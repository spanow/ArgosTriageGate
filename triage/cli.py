"""CLI du Triage Gate :  uv run triage <fichier_log> [--adapter wazn|strands|rules] [--threshold 0.6]

Affiche le texte extrait, la distribution, la porte NONE, la décision de routage et la latence.
"""

import argparse
import sys
from pathlib import Path

from triage.adapters import ADAPTERS, create_adapter
from triage.domain.taxonomy import load_taxonomy
from triage.policy.routing import route
from triage.preprocessing.extract import extract

REASONS = {
    "confident": "décision automatique",
    "none": "ESCALADE : aucune catégorie ne convient (porte NONE)",
    "low_confidence": "ESCALADE : le modèle hésite (confiance sous le seuil)",
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="triage", description="Triage Gate d'Argos")
    parser.add_argument("log_file", type=Path)
    parser.add_argument("--adapter", choices=ADAPTERS, default="wazn")
    parser.add_argument("--threshold", type=float, help="seuil de confiance (défaut : celui de la taxonomie)")
    args = parser.parse_args(argv)

    taxonomy = load_taxonomy()
    text = extract(args.log_file.read_text(encoding="utf-8")).to_text()
    adapter = create_adapter(args.adapter)
    decision = adapter.decide(text, taxonomy.candidates, taxonomy.instruction)
    result = route(decision, taxonomy, args.threshold)

    print("--- Incident extrait ---")
    print(text)
    print(f"\n--- Distribution ({decision.model}) ---")
    for category, probability in decision.top(len(taxonomy.candidates)):
        print(f"  {category:<22} {probability:6.1%}  {'#' * round(probability * 40)}")
    if decision.none_probability is not None:
        print(f"  {'P(NONE)':<22} {decision.none_probability:6.1%}  -> is_none = {decision.is_none}")
    print("\n--- Décision ---")
    print(f"  {REASONS[result.reason]}")
    print(f"  route : {result.route}" + (f"  (catégorie : {result.category})" if result.category else ""))
    if result.suggestions:
        print("  pistes : " + ", ".join(f"{c} {p:.0%}" for c, p in result.suggestions))
    tokens = f", {decision.input_tokens} tokens lus" if decision.input_tokens else ""
    print(f"  latence : {decision.latency_ms / 1000:.2f} s{tokens}")


if __name__ == "__main__":
    sys.exit(main())
