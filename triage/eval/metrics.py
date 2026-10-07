"""Métriques d'évaluation. Chaque ligne est un incident évalué (voir triage/eval/run.py) :
`expected`, `predicted` (réponse brute du modèle : catégorie ou NONE), `confidence`, `ambiguous`, `latency_ms`.
"""

import math
from collections import defaultdict


def accuracy(rows: list[dict], include_ambiguous: bool = True) -> float:
    kept = [r for r in rows if include_ambiguous or not r["ambiguous"]]
    return sum(r["predicted"] == r["expected"] for r in kept) / len(kept)


def confusion(rows: list[dict]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        matrix[r["expected"]][r["predicted"]] += 1
    return matrix


def none_precision_recall(rows: list[dict]) -> tuple[float | None, float | None]:
    """Précision : quand NONE est prédit, est-ce juste ? Rappel : parmi les NONE attendus, combien trouvés ?"""
    predicted = [r for r in rows if r["predicted"] == "NONE"]
    expected = [r for r in rows if r["expected"] == "NONE"]
    hits = sum(r["expected"] == "NONE" for r in predicted)
    return (hits / len(predicted) if predicted else None, hits / len(expected) if expected else None)


def routing_at(rows: list[dict], threshold: float) -> dict:
    """Ce que fait le Triage Gate à ce seuil : action automatique si pas NONE et confiance ≥ seuil, sinon escalade."""
    automatic = [r for r in rows if r["predicted"] != "NONE" and r["confidence"] >= threshold]
    correct = sum(r["predicted"] == r["expected"] for r in automatic)
    return {
        "threshold": threshold,
        "automatic": len(automatic),
        "automatic_correct": correct,
        "automatic_wrong": len(automatic) - correct,
        "coverage": len(automatic) / len(rows),
        "automatic_precision": correct / len(automatic) if automatic else None,
        "escalated": len(rows) - len(automatic),
    }


def expected_calibration_error(rows: list[dict], bins: int = 5) -> float:
    """ECE sur les réponses qui désignent une catégorie : moyenne pondérée, par tranche de confiance,
    de |taux de réussite − confiance moyenne|. 0 = confiance parfaitement tenue."""
    scored = [r for r in rows if r["predicted"] != "NONE"]
    by_bin: dict[int, list[dict]] = defaultdict(list)
    for r in scored:
        by_bin[min(int(r["confidence"] * bins), bins - 1)].append(r)
    error = 0.0
    for members in by_bin.values():
        success = sum(r["predicted"] == r["expected"] for r in members) / len(members)
        mean_confidence = sum(r["confidence"] for r in members) / len(members)
        error += len(members) / len(scored) * abs(success - mean_confidence)
    return error


def percentile(values: list[float], p: float) -> float:
    """Percentile « rang le plus proche » : une valeur réellement observée, sans interpolation."""
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]
