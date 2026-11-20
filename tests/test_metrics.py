"""src.metrics 的 kappa、覆盖率、误杀/漏放与标注聚合测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.metrics import (
    agreement_rate,
    asn_fallback_rate,
    cohen_kappa,
    compute_metrics,
    coverage_rate,
    false_block_rate,
    main,
    miss_rate,
)


def test_cohen_kappa_known_hand_calculation() -> None:
    # 6 对：4 对一致，po=4/6；A/B 边际均为 2/2/2 与 2/3/1；
    # pe=12/36，kappa=(4/6-1/3)/(1-1/3)=0.5（手算）。
    labels_a = ["yes", "yes", "no", "no", "maybe", "maybe"]
    labels_b = ["yes", "no", "no", "no", "maybe", "yes"]

    assert cohen_kappa(labels_a, labels_b) == pytest.approx(0.5)
    assert agreement_rate(labels_a, labels_b) == pytest.approx(4 / 6)


def test_kappa_boundaries_and_errors() -> None:
    assert cohen_kappa(["found", "clear"], ["found", "clear"]) == pytest.approx(1.0)
    assert cohen_kappa(["found", "found"], ["found", "found"]) is None
    assert cohen_kappa([], []) is None
    with pytest.raises(ValueError):
        cohen_kappa(["found"], ["found", "clear"])


def test_coverage_rate() -> None:
    statuses = {"a": "found", "b": "clear", "c": "not_tested", "d": "not_tested"}

    assert coverage_rate(statuses) == pytest.approx(0.5)
    assert coverage_rate({}) == 0.0
    with pytest.raises(ValueError):
        coverage_rate({"a": "unknown"})


def test_false_block_and_miss_rates_with_zero_denominator() -> None:
    assert false_block_rate(2, 10) == pytest.approx(0.2)
    assert miss_rate(1, 5) == pytest.approx(0.2)
    assert false_block_rate(0, 0) is None
    assert miss_rate(0, 0) is None
    with pytest.raises(ValueError):
        false_block_rate(3, 2)


def test_asn_fallback_rate() -> None:
    assert asn_fallback_rate(
        [
            {"asn_fallback": False, "rule_count": 4},
            {"asn_fallback": True, "rule_count": 1},
        ]
    ) == pytest.approx(0.5)
    assert asn_fallback_rate([]) is None


def test_compute_metrics_from_annotation() -> None:
    annotation = {
        "annotators": {
            "A": {
                "A1": {"C1": "found", "C2": "clear", "C3": "not_tested"},
                "A2": {"C1": "clear", "C2": "clear", "C3": "clear"},
            },
            "B": {
                "A1": {"C1": "found", "C2": "not_tested", "C3": "not_tested"},
                "A2": {"C1": "clear", "C2": "clear", "C3": "clear"},
            },
        },
        "decisions": [
            {"firmware_id": "A1", "expected": "reject", "actual": "conditional"},
            {"firmware_id": "A2", "expected": "pass", "actual": "pass"},
        ],
        "policy_replay": [
            {"false_blocks": 2, "legit_total": 10, "missed": 1, "malicious_total": 5},
            {"false_blocks": 0, "legit_total": 5, "missed": 0, "malicious_total": 5},
        ],
        "policies": [
            {"asn_fallback": False, "rule_count": 4},
            {"asn_fallback": True, "rule_count": 1},
        ],
    }

    result = compute_metrics(annotation)

    assert result.coverage == pytest.approx(5 / 6)
    assert result.agreement == pytest.approx(5 / 6)
    assert result.kappa == pytest.approx(5 / 7)
    assert result.decision_accuracy == pytest.approx(0.5)
    assert result.false_block_rate == pytest.approx(2 / 15)
    assert result.miss_rate == pytest.approx(0.1)
    assert result.asn_fallback_rate == pytest.approx(0.5)
    assert result.policy_rule_count == 5


def test_compute_metrics_rejects_bad_schema() -> None:
    with pytest.raises(ValueError):
        compute_metrics({"annotators": {"A": {"A1": {"C1": "unknown"}}}})
    with pytest.raises(ValueError):
        compute_metrics(
            {
                "annotators": {
                    "A": {"A1": {"C1": "found"}},
                    "B": {"A1": {"C2": "found"}},
                }
            }
        )
    with pytest.raises(ValueError):
        compute_metrics({"policies": [{"asn_fallback": "false", "rule_count": 1}]})


def test_main_writes_json(tmp_path: Path) -> None:
    annotation_path = tmp_path / "annotation.json"
    output = tmp_path / "metrics.json"
    annotation_path.write_text(
        json.dumps(
            {
                "annotators": {"A": {"A1": {"C1": "found", "C2": "clear"}}},
                "policies": [{"asn_fallback": False, "rule_count": 2}],
            }
        ),
        encoding="utf-8",
    )

    assert main([str(annotation_path), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["coverage"] == 1.0
    assert payload["kappa"] is None
    assert payload["policy_rule_count"] == 2
