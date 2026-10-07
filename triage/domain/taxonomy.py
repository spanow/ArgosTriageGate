"""Chargement de data/taxonomy.yaml en objets du domaine."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from triage.domain.model import Candidate

DEFAULT_TAXONOMY = Path(__file__).resolve().parents[2] / "data" / "taxonomy.yaml"


@dataclass(frozen=True)
class Taxonomy:
    instruction: str
    candidates: list[Candidate]
    none_route: str
    threshold: float
    top_k: int

    def route_of(self, candidate_id: str) -> str:
        return next(c.route for c in self.candidates if c.id == candidate_id)

    def candidate(self, candidate_id: str) -> Candidate:
        return next(c for c in self.candidates if c.id == candidate_id)


def load_taxonomy(path: Path = DEFAULT_TAXONOMY) -> Taxonomy:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    candidates = [Candidate(c["id"], c["definition"], c["route"], c.get("label_fr", "")) for c in raw["categories"]]
    return Taxonomy(instruction=raw["instruction"], candidates=candidates, none_route=raw["none"]["route"],
                    threshold=raw["policy"]["confidence_threshold"], top_k=raw["policy"]["suggestions_top_k"])
