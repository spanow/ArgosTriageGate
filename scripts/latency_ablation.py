"""Effet du préprocessing : le même incident envoyé à Wazn brut, puis extrait.

    uv run python scripts/latency_ablation.py
Sortie : results/ablation_wazn_<horodatage>.json + tableau à l'écran. Latence = temps d'inférence côté serveur.
"""

import json
from datetime import datetime
from pathlib import Path

from triage.adapters.wazn import WaznAdapter
from triage.domain.taxonomy import load_taxonomy
from triage.preprocessing.extract import extract

ROOT = Path(__file__).resolve().parent.parent
# Trois tailles de log brut : court (ligne unique), moyen, long (stack trace Tomcat complète).
SCENARIOS = ["json_parse_error", "payment_timeout", "npe_guest_order"]


def main() -> None:
    taxonomy = load_taxonomy()
    adapter = WaznAdapter()
    incidents = [json.loads(line) for line in (ROOT / "data" / "incidents.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = []
    for scenario in SCENARIOS:
        incident = next(i for i in incidents if i["scenario"] == scenario)
        for variant, text in (("brut", incident["log"]), ("extrait", extract(incident["log"]).to_text())):
            d = adapter.decide(text, taxonomy.candidates, taxonomy.instruction)
            rows.append({"id": incident["id"], "scenario": scenario, "variant": variant, "expected": incident["expected"],
                         "predicted": "NONE" if d.is_none else d.choice, "confidence": round(d.confidence, 4),
                         "input_tokens": d.input_tokens, "latency_ms": round(d.latency_ms, 1)})
            r = rows[-1]
            print(f"{scenario:<18} {variant:<8} {r['input_tokens']:>5} tokens  {r['latency_ms'] / 1000:6.1f} s  "
                  f"→ {r['predicted']} ({r['confidence']:.2f}), attendu {r['expected']}", flush=True)
    run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output = ROOT / "results" / f"ablation_wazn_{run_id}.json"
    output.write_text(json.dumps({"run_id": run_id, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {output}")


if __name__ == "__main__":
    main()
