"""Politique de routage. Indépendante du modèle : elle ne lit qu'une `Decision`.

Ordre des contrôles (à ne jamais inverser) :
  1. porte NONE ouverte          → escalade, sans suggestion (log inconnu)
  2. confiance < seuil           → escalade, avec le top-k en suggestions (le modèle hésite)
  3. sinon                       → action associée à la catégorie
"""

from dataclasses import dataclass, field

from triage.domain.model import Decision
from triage.domain.taxonomy import Taxonomy


@dataclass(frozen=True)
class Routing:
    category: str | None
    route: str
    escalated: bool
    reason: str  # "none" | "low_confidence" | "confident"
    suggestions: list[tuple[str, float]] = field(default_factory=list)


def route(decision: Decision, taxonomy: Taxonomy, threshold: float | None = None) -> Routing:
    threshold = taxonomy.threshold if threshold is None else threshold
    if decision.is_none:
        return Routing(None, taxonomy.none_route, True, "none")
    if decision.confidence < threshold:
        return Routing(None, taxonomy.none_route, True, "low_confidence", decision.top(taxonomy.top_k))
    return Routing(decision.choice, taxonomy.route_of(decision.choice), False, "confident")
