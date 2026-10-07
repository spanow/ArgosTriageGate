"""Adapter Strands Decider 2B (v21), second modèle derrière le même port.

API du paquet `strands-decider` 0.1.0 : POST /v1/systemone avec un `state` et des `questions` typées.
Strands n'a pas de porte NONE et la v21 n'a pas été entraînée avec une option « none of these » : la porte est
une question oui/non (`noul`), posée dans la même requête. P(NONE) = 1 − P(oui).
"""

from typing import Sequence

import httpx

from triage.domain.model import Candidate, Decision

GATE_QUESTION = (
    "Does this text describe a technical failure that one of these teams must act on: application developers, "
    "configuration owners, operations (capacity), owners of a downstream service, security/PKI, or data integration?"
)
NONE_THRESHOLD = 0.5  # comme la porte de Wazn (none_threshold = 0,5)


class StrandsAdapter:
    name = "strands"

    def __init__(self, url: str = "http://127.0.0.1:8001", http: httpx.Client | None = None):
        self.http = http or httpx.Client(base_url=url, timeout=900)

    def decide(self, context: str, candidates: Sequence[Candidate], instruction: str) -> Decision:
        payload = {
            "state": context,
            "questions": {
                "category": {"type": "choice", "instructions": instruction,
                             "criteria": {c.id: c.definition for c in candidates}},
                "relevant": {"type": "noul", "instructions": GATE_QUESTION},
            },
        }
        response = self.http.post("/v1/systemone", json=payload)
        response.raise_for_status()
        body = response.json()
        none_probability = 1 - body["answers"]["relevant"]["noul"]
        return Decision(probabilities=dict(body["answers"]["category"]["probabilities"]),
                        none_probability=none_probability, is_none=none_probability > NONE_THRESHOLD,
                        latency_ms=body["latency_ms"], model=body["model"],
                        input_tokens=body.get("usage", {}).get("input_tokens"))
