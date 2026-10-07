"""Évalue un adapter sur un jeu d'incidents et enregistre les sorties du modèle.

    uv run python -m triage.eval.run --adapter rules
    uv run python -m triage.eval.run --adapter wazn --url http://127.0.0.1:8000
    uv run python -m triage.eval.run --adapter strands --dataset robustness

Chaque incident est écrit au fil de l'eau dans results/<prefix>_<adapter>.partial.jsonl : relancer la commande
reprend là où elle s'était arrêtée. Résultat final : results/<prefix>_<adapter>_<horodatage>.json.
"""

import argparse
import json
import platform
from datetime import datetime
from pathlib import Path

from triage.adapters import ADAPTERS, create_adapter
from triage.domain.taxonomy import load_taxonomy
from triage.policy.routing import route
from triage.preprocessing.extract import extract

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
# jeu → (fichier d'incidents, préfixe des fichiers de résultats)
DATASETS = {"main": ("incidents.jsonl", "run"), "robustness": ("robustness.jsonl", "robust")}

# Matériel par défaut ; pour un modèle, --hardware le précise (sur Modal : le GPU lu par nvidia-smi).
HARDWARE = {
    "rules": f"AMD Ryzen 5 5600H, Python {platform.python_version()} (regex, no model)",
}
MODELS = {"wazn": "wazn-2b-v0.1", "strands": "strands-decider-2B-hobson-v21", "rules": "rules-baseline"}


def load_incidents(dataset: str) -> list[dict]:
    path = ROOT / "data" / DATASETS[dataset][0]
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def evaluate_one(adapter, taxonomy, incident: dict) -> dict:
    text = extract(incident["log"]).to_text()
    decision = adapter.decide(text, taxonomy.candidates, taxonomy.instruction)
    routing = route(decision, taxonomy)
    candidates = [{"id": c.id, "description": c.label_fr, "probability": round(decision.probabilities[c.id], 6)}
                  for c in taxonomy.candidates]
    candidates.append({"id": "NONE", "description": "Aucune catégorie ne correspond",
                       "probability": None if decision.none_probability is None
                       else round(decision.none_probability, 6)})
    return {
        "id": incident["id"], "source": incident["source"], "scenario": incident["scenario"],
        "ambiguous": incident["ambiguous"], "log_excerpt": text, "expected": incident["expected"],
        "candidates": candidates,
        # La réponse brute du modèle (indépendante du seuil) : NONE si la porte est ouverte, sinon l'argmax.
        "predicted": "NONE" if decision.is_none else decision.choice,
        "confidence": round(decision.confidence, 6),
        "route": routing.route, "escalated": routing.escalated, "reason": routing.reason,
        "suggestions": [[c, round(p, 6)] for c, p in routing.suggestions],
        "latency_ms": round(decision.latency_ms, 1), "input_tokens": decision.input_tokens,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", choices=ADAPTERS, required=True)
    parser.add_argument("--dataset", choices=list(DATASETS), default="main")
    parser.add_argument("--limit", type=int, help="traite au plus N incidents puis s'arrête (reprise ensuite)")
    parser.add_argument("--url", help="adresse du serveur du modèle (défaut : celle de l'adapter)")
    parser.add_argument("--hardware", help="description du matériel, enregistrée dans le run")
    args = parser.parse_args(argv)
    prefix = DATASETS[args.dataset][1]

    taxonomy = load_taxonomy()
    adapter = create_adapter(args.adapter, args.url)
    RESULTS.mkdir(exist_ok=True)
    partial = RESULTS / f"{prefix}_{args.adapter}.partial.jsonl"
    done = {json.loads(line)["id"] for line in partial.read_text(encoding="utf-8").splitlines()} \
        if partial.exists() else set()

    if args.adapter != "rules" and not done:
        # Échauffement : la 1ʳᵉ requête est plus lente (initialisations) ; on ne la compte pas.
        adapter.decide("warm-up", taxonomy.candidates, taxonomy.instruction)

    incidents = load_incidents(args.dataset)
    processed = 0
    for incident in incidents:
        if incident["id"] in done:
            continue
        if args.limit is not None and processed >= args.limit:
            print(f"Arrêt après {processed} incidents (--limit) ; relancer pour continuer.")
            return
        processed += 1
        result = evaluate_one(adapter, taxonomy, incident)
        with partial.open("a", encoding="utf-8") as out:
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
        print(f"{incident['id']}  attendu {incident['expected']:<22} prédit {result['predicted']:<22} "
              f"{result['confidence']:.2f}  {result['latency_ms'] / 1000:6.1f} s", flush=True)

    results = {json.loads(line)["id"]: json.loads(line) for line in partial.read_text(encoding="utf-8").splitlines()}
    run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    run = {
        "run_id": run_id,
        "model": MODELS[args.adapter],
        "hardware": args.hardware or HARDWARE.get(args.adapter, "not specified"),
        "dataset": args.dataset,
        "threshold": taxonomy.threshold,
        "instruction": taxonomy.instruction,
        "incidents": [results[i["id"]] for i in incidents],
    }
    output = RESULTS / f"{prefix}_{args.adapter}_{run_id}.json"
    output.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    partial.unlink()
    print(f"→ {output}")


if __name__ == "__main__":
    main()
