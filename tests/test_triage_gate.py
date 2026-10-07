"""Tests du Triage Gate : taxonomie, routage, baseline à règles, adapters (serveurs simulés)."""

import json

import httpx
import pytest
from wazn_experimental import Answer, Response, Usage

from triage.adapters.rules import RuleBasedAdapter
from triage.adapters.strands import StrandsAdapter
from triage.adapters.wazn import WaznAdapter
from triage.domain.model import Candidate, Decision
from triage.domain.taxonomy import load_taxonomy
from triage.policy.routing import route

TAXONOMY = load_taxonomy()


def decision(probabilities: dict[str, float], is_none: bool = False, none_probability: float = 0.01) -> Decision:
    return Decision(probabilities=probabilities, none_probability=none_probability, is_none=is_none,
                    latency_ms=1.0, model="test")


# --- 3.1 Domaine + taxonomie ------------------------------------------------------------------------------------

def test_taxonomy_is_loaded_with_its_routes_and_policy():
    assert [c.id for c in TAXONOMY.candidates] == [
        "code_defect", "configuration", "capacity", "dependency", "security_certificate", "data_quality"]
    assert TAXONOMY.route_of("dependency") == "dependency_owner_ticket"
    assert TAXONOMY.threshold == 0.6
    assert TAXONOMY.top_k == 2


def test_decision_exposes_choice_confidence_and_top_k():
    d = decision({"capacity": 0.2, "dependency": 0.7, "code_defect": 0.1})
    assert d.choice == "dependency"
    assert d.confidence == 0.7
    assert d.top(2) == [("dependency", 0.7), ("capacity", 0.2)]


# --- 3.4 Politique de routage -------------------------------------------------------------------------------------

def test_confident_decision_is_routed_to_the_category_action():
    result = route(decision({"dependency": 0.9, "capacity": 0.1}), TAXONOMY)
    assert (result.category, result.route, result.escalated, result.reason) == (
        "dependency", "dependency_owner_ticket", False, "confident")


def test_none_gate_wins_over_a_confident_choice():
    """choice à 0,85 mais is_none=True → escalade, sans suggestion."""
    result = route(decision({"capacity": 0.85, "dependency": 0.15}, is_none=True, none_probability=0.91), TAXONOMY)
    assert result.escalated and result.reason == "none"
    assert result.category is None and result.route == "escalate"
    assert result.suggestions == []


def test_low_confidence_escalates_with_top_k_suggestions():
    """0,48 / 0,41 sous le seuil 0,6 → escalade avec les 2 meilleures pistes."""
    result = route(decision({"capacity": 0.48, "dependency": 0.41, "code_defect": 0.11}), TAXONOMY)
    assert result.escalated and result.reason == "low_confidence"
    assert result.suggestions == [("capacity", 0.48), ("dependency", 0.41)]


def test_threshold_can_be_overridden_for_the_threshold_curve():
    d = decision({"capacity": 0.55, "dependency": 0.45})
    assert route(d, TAXONOMY).escalated
    assert not route(d, TAXONOMY, threshold=0.5).escalated


# --- 3.2 Baseline à règles ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Exception: java.lang.NullPointerException: Cannot invoke \"x\"", "code_defect"),
    ("Caused by: java.net.SocketTimeoutException: Read timed out", "dependency"),
    ("java.sql.SQLTransientConnectionException: HikariPool-1 - Connection is not available", "capacity"),
    ("java.lang.IllegalStateException: Required key 'shipping.partner.api-key' not found", "configuration"),
    ("Caused by: java.security.cert.CertificateExpiredException: NotAfter", "security_certificate"),
    ("tools.jackson.core.exc.UnexpectedEndOfInputException: Unexpected end-of-input", "data_quality"),
])
def test_rules_recognise_typical_signatures(text, expected):
    d = RuleBasedAdapter().decide(text, TAXONOMY.candidates, TAXONOMY.instruction)
    assert d.choice == expected and not d.is_none
    assert abs(sum(d.probabilities.values()) - 1) < 1e-9


def test_rules_say_none_when_nothing_matches():
    d = RuleBasedAdapter().decide("Bonjour, mon panier ne se valide plus.", TAXONOMY.candidates, TAXONOMY.instruction)
    assert d.is_none


# --- 3.3 Adapter Wazn (serveur simulé) ----------------------------------------------------------------------------

class FakeClient:
    """Imite wazn_experimental.Client : renvoie une vraie Response, et garde la requête reçue."""

    def __init__(self, answer: Answer):
        self.answer = answer
        self.request = None

    def predict(self, request):
        self.request = request
        return Response(model="wazn-2b-v0.1", answers={"category": self.answer}, usage=Usage(input_tokens=120),
                        prediction_seconds=4.2)


def test_wazn_adapter_sends_definitions_and_maps_the_answer():
    answer = Answer(choice="dependency", confidence=0.8, probabilities={"dependency": 0.8, "capacity": 0.2},
                    none_probability=0.05, is_none=False)
    client = FakeClient(answer)
    candidates = [Candidate("dependency", "A downstream service failed.", "t1"),
                  Candidate("capacity", "A pool is exhausted.", "t2")]

    d = WaznAdapter(client=client).decide("ERROR timeout", candidates, "Which team must act?")

    sent = client.request
    assert sent.context == "ERROR timeout"
    assert "A downstream service failed." in str(sent.to_dict())
    assert (d.choice, d.confidence, d.none_probability, d.is_none, d.model) == (
        "dependency", 0.8, 0.05, False, "wazn-2b-v0.1")
    assert d.input_tokens == 120
    # Latence = temps d'inférence mesuré par le serveur (4,2 s), sans file d'attente ni HTTP.
    assert d.latency_ms == 4200


# --- Adapter Strands Decider (serveur simulé par httpx.MockTransport) --------------------------------------------

def test_strands_adapter_asks_choice_and_gate_in_one_request_and_maps_the_gate_to_none():
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json={
            "model": "strands-decider-2B-hobson-v21",
            "answers": {
                "category": {"type": "choice", "choice": "dependency", "confidence": 0.7,
                             "probabilities": {"dependency": 0.8, "capacity": 0.2}},
                "relevant": {"type": "noul", "noul": 0.1},
            },
            "usage": {"input_tokens": 300, "output_tokens": 1},
            "latency_ms": 5123.4,
        })

    http = httpx.Client(base_url="http://strands", transport=httpx.MockTransport(handler))
    candidates = [Candidate("dependency", "A downstream service failed.", "t1"),
                  Candidate("capacity", "A pool is exhausted.", "t2")]

    d = StrandsAdapter(http=http).decide("ERROR timeout", candidates, "Which team must act?")

    assert sent["state"] == "ERROR timeout"
    assert sent["questions"]["category"]["criteria"] == {"dependency": "A downstream service failed.",
                                                         "capacity": "A pool is exhausted."}
    assert sent["questions"]["relevant"]["type"] == "noul"
    assert d.choice == "dependency" and d.confidence == 0.8
    assert abs(d.none_probability - 0.9) < 1e-9 and d.is_none   # P(oui) = 0,1 → porte NONE ouverte
    assert (d.latency_ms, d.input_tokens, d.model) == (5123.4, 300, "strands-decider-2B-hobson-v21")


# --- Fabrique d'adapters : chaque conteneur n'embarque que la bibliothèque de son modèle -----------------------

@pytest.mark.parametrize("name, forbidden", [("rules", "wazn_experimental"), ("strands", "wazn_experimental")])
def test_choosing_an_adapter_does_not_import_the_other_models_library(name, forbidden):
    import subprocess
    import sys

    code = ("import sys; from triage.adapters import create_adapter; create_adapter(%r); "
            "sys.exit(1 if %r in sys.modules else 0)" % (name, forbidden))
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
