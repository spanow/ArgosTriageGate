"""Adapter Wazn : requête Wazn construite depuis le domaine, réponse convertie en `Decision`.

Le modèle tourne dans un serveur (Modal ou Docker) ; on l'interroge avec le client HTTP de la bibliothèque,
qui n'a pas besoin de PyTorch.
"""

import time
from typing import Sequence

from wazn_experimental import Client, Instruction, Label, Request

from triage.domain.model import Candidate, Decision

INSTRUCTION_NAME = "category"


class WaznAdapter:
    name = "wazn"

    def __init__(self, client=None, url: str = "http://127.0.0.1:8000"):
        self.client = client or Client(url)

    def decide(self, context: str, candidates: Sequence[Candidate], instruction: str) -> Decision:
        request = Request(
            context=context,
            instructions=Instruction(instruction, labels=[Label(c.id, c.definition) for c in candidates],
                                     name=INSTRUCTION_NAME),
        )
        start = time.perf_counter()
        response = self.client.predict(request)
        # Temps d'inférence mesuré par le serveur : hors réseau et hors file d'attente.
        if response.prediction_seconds is not None:
            latency_ms = response.prediction_seconds * 1000
        else:
            latency_ms = (time.perf_counter() - start) * 1000
        answer = response[INSTRUCTION_NAME]
        return Decision(probabilities=dict(answer.probabilities), none_probability=answer.none_probability,
                        is_none=bool(answer.is_none), latency_ms=latency_ms, model=response.model,
                        input_tokens=response.usage.input_tokens)
