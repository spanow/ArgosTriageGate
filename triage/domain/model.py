"""Domaine du Triage Gate : candidats, décision et port `DecisionPort`."""

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Candidate:
    """Une catégorie possible. Le modèle lit la `definition` ; la `route` dit quoi faire si elle est choisie."""

    id: str
    definition: str
    route: str
    label_fr: str = ""


@dataclass(frozen=True)
class Decision:
    """Ce que renvoie un modèle : une distribution sur les candidats (somme = 1) et la porte NONE, séparée."""

    probabilities: dict[str, float]
    none_probability: float | None
    is_none: bool
    latency_ms: float
    model: str
    input_tokens: int | None = None

    @property
    def choice(self) -> str:
        return max(self.probabilities, key=self.probabilities.get)

    @property
    def confidence(self) -> float:
        return self.probabilities[self.choice]

    def top(self, k: int) -> list[tuple[str, float]]:
        return sorted(self.probabilities.items(), key=lambda item: item[1], reverse=True)[:k]


class DecisionPort(Protocol):
    """Le port : « choisis parmi ces candidats pour ce contexte ». Wazn et la baseline à règles l'implémentent."""

    name: str

    def decide(self, context: str, candidates: Sequence[Candidate], instruction: str) -> Decision:
        ...
