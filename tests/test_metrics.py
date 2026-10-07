"""Tests des métriques d'évaluation, sur de petits cas calculables à la main."""

from triage.eval.metrics import (accuracy, confusion, expected_calibration_error, none_precision_recall,
                                 percentile, routing_at)


def row(expected, predicted, confidence, ambiguous=False, latency_ms=100.0):
    return {"expected": expected, "predicted": predicted, "confidence": confidence, "ambiguous": ambiguous,
            "latency_ms": latency_ms}


ROWS = [
    row("code_defect", "code_defect", 0.9),
    row("capacity", "code_defect", 0.7, ambiguous=True),
    row("dependency", "dependency", 0.5),
    row("NONE", "NONE", 0.4),
    row("NONE", "dependency", 0.8),
]


def test_accuracy_on_all_and_without_ambiguous_cases():
    assert accuracy(ROWS) == 3 / 5
    assert accuracy(ROWS, include_ambiguous=False) == 3 / 4


def test_confusion_counts_expected_by_predicted():
    matrix = confusion(ROWS)
    assert matrix["capacity"]["code_defect"] == 1
    assert matrix["NONE"]["dependency"] == 1
    assert matrix["code_defect"]["code_defect"] == 1


def test_none_precision_and_recall():
    # 1 seul NONE prédit, et il est juste ; 2 NONE attendus, 1 trouvé.
    assert none_precision_recall(ROWS) == (1.0, 0.5)


def test_routing_at_threshold_counts_automatic_actions_and_their_errors():
    r = routing_at(ROWS, 0.6)
    # Automatiques : conf ≥ 0,6 et pas NONE → lignes 1, 2, 5 ; justes : ligne 1 seulement.
    assert (r["automatic"], r["automatic_correct"], r["automatic_wrong"]) == (3, 1, 2)
    assert r["coverage"] == 3 / 5
    assert r["automatic_precision"] == 1 / 3


def test_expected_calibration_error_is_zero_for_perfect_calibration():
    perfect = [row("a", "a", 1.0), row("a", "a", 1.0)]
    assert expected_calibration_error(perfect) == 0.0
    # Toujours 0,8 annoncé, 50 % de réussite → écart 0,3.
    half = [row("a", "a", 0.8), row("a", "b", 0.8)]
    assert abs(expected_calibration_error(half) - 0.3) < 1e-9


def test_percentile_uses_nearest_rank():
    assert percentile([1, 2, 3, 4, 100], 50) == 3
    assert percentile([1, 2, 3, 4, 100], 95) == 100
