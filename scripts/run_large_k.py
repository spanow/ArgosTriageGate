"""Large-K : Wazn choisit l'équipe propriétaire parmi 36 (data/services.yaml).

    uv run python scripts/run_large_k.py
Sortie : results/largek_wazn_<horodatage>.json, mêmes champs que les runs d'évaluation.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml

from triage.adapters.wazn import WaznAdapter
from triage.domain.model import Candidate
from triage.preprocessing.extract import extract

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="traite au plus N cas puis s'arrête (reprise ensuite)")
    args = parser.parse_args()
    partial = ROOT / "results" / "largek_wazn.partial.jsonl"
    done = {}
    if partial.exists():
        for line in partial.read_text(encoding="utf-8").splitlines():
            done[json.loads(line)["scenario"]] = json.loads(line)
    catalog = yaml.safe_load((ROOT / "data" / "services.yaml").read_text(encoding="utf-8"))
    candidates = [Candidate(team, definition, route=f"ticket:{team}") for team, definition in catalog["teams"].items()]
    incidents = [json.loads(line) for line in (ROOT / "data" / "incidents.jsonl").read_text(encoding="utf-8").splitlines()]
    adapter = WaznAdapter()
    if not done:
        # Échauffement à 36 labels : la 1ʳᵉ requête est plus lente ; on ne la compte pas.
        adapter.decide("warm-up", candidates, catalog["instruction"])

    processed = 0
    for case in catalog["cases"]:
        if case["scenario"] in done:
            continue
        if args.limit is not None and processed >= args.limit:
            print("Arrêt (--limit) ; relancer pour continuer.")
            return
        processed += 1
        incident = next(i for i in incidents if i["scenario"] == case["scenario"])
        text = extract(incident["log"]).to_text()
        decision = adapter.decide(text, candidates, catalog["instruction"])
        predicted = "NONE" if decision.is_none else decision.choice
        row = {
            "id": incident["id"], "scenario": case["scenario"], "log_excerpt": text, "expected": case["expected"],
            "candidates": [{"id": team, "description": catalog["teams"][team], "probability": round(p, 6)}
                           for team, p in decision.top(len(candidates))]
                          + [{"id": "NONE", "description": "Aucune équipe ne correspond",
                              "probability": round(decision.none_probability, 6)}],
            "predicted": predicted, "confidence": round(decision.confidence, 6),
            "latency_ms": round(decision.latency_ms, 1), "input_tokens": decision.input_tokens,
        }
        with partial.open("a", encoding="utf-8") as out:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[case["scenario"]] = row
        print(f"{case['scenario']:<18} attendu {case['expected']:<18} prédit {predicted:<18} "
              f"{decision.confidence:.2f}  {decision.latency_ms / 1000:.0f} s", flush=True)

    results = [done[c["scenario"]] for c in catalog["cases"]]
    run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output = ROOT / "results" / f"largek_wazn_{run_id}.json"
    output.write_text(json.dumps({"run_id": run_id, "model": "wazn-2b-v0.1", "k": len(candidates),
                                  "instruction": catalog["instruction"], "incidents": results},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    partial.unlink()
    print(f"→ {output}")


if __name__ == "__main__":
    main()
