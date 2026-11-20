"""src.exposure 的敞口、保障度与三态判定测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.exposure import CheckSpec, assess_exposure, load_checks, main
from src.schema import Evidence, EvidenceLevel, Verdict

CHECKS = [
    CheckSpec("CRIT", "CRED", "Critical check", "Critical", 1.0),
    CheckSpec("HIGH", "UNAUTH", "High check", "High", 0.8),
    CheckSpec("MED", "EGRESS", "Medium check", "Medium", 0.6),
]


def _evidence(
    check_code: str, level: EvidenceLevel, confidence: float, suffix: str = "1"
) -> Evidence:
    return Evidence(
        id=f"E-{check_code}-{suffix}",
        firmware_id="FW-TEST",
        check_code=check_code,
        level=level,
        confidence=confidence,
        raw_ref=f"{check_code}:1",
        detail="测试",
    )


def _outcomes(**statuses: str) -> dict[str, str]:
    return statuses


def test_all_clear_passes() -> None:
    result = assess_exposure(
        [], CHECKS, _outcomes(CRIT="clear", HIGH="clear", MED="clear")
    )

    assert result.exposure == pytest.approx(0.0)
    assert result.assurance == pytest.approx(1.0)
    assert result.verdict is Verdict.PASS
    assert result.confidence == pytest.approx(1.0)
    assert any("放行" in reason for reason in result.reasons)


def test_all_not_tested_is_conditional_and_zero_confidence() -> None:
    result = assess_exposure(
        [], CHECKS, _outcomes(CRIT="not_tested", HIGH="not_tested", MED="not_tested")
    )

    assert result.exposure == pytest.approx(1.0)
    assert result.assurance == pytest.approx(0.0)
    assert result.verdict is Verdict.CONDITIONAL
    assert result.confidence == pytest.approx(0.0)
    assert any("证据不足" in reason for reason in result.reasons)


def test_all_e3_findings_are_conditional_not_pass() -> None:
    evidence = [_evidence(check.code, EvidenceLevel.E3, 0.5) for check in CHECKS]
    result = assess_exposure(
        evidence, CHECKS, {check.code: "found" for check in CHECKS}
    )

    assert result.exposure == pytest.approx(0.5)
    assert result.assurance == pytest.approx(0.5)
    assert result.verdict is Verdict.CONDITIONAL
    assert any("下限" in reason for reason in result.reasons)
    assert any("证据不足" in reason for reason in result.reasons)


def test_all_e1_findings_are_rejected() -> None:
    evidence = [_evidence(check.code, EvidenceLevel.E1, 0.9) for check in CHECKS]
    result = assess_exposure(
        evidence, CHECKS, {check.code: "found" for check in CHECKS}
    )

    assert result.exposure == pytest.approx(1.0)
    assert result.assurance == pytest.approx(1.0)
    assert result.verdict is Verdict.REJECT
    assert any("红线" in reason for reason in result.reasons)


def test_e1_critical_is_hard_reject_even_if_other_checks_clear() -> None:
    result = assess_exposure(
        [_evidence("CRIT", EvidenceLevel.E1, 0.9)],
        CHECKS,
        _outcomes(CRIT="found", HIGH="clear", MED="clear"),
    )

    assert result.exposure == pytest.approx(1.0 / 2.4)
    assert result.verdict is Verdict.REJECT
    assert result.confidence == pytest.approx(1.0)
    assert result.per_check["CRIT"]["level"] == "E1"


def test_high_e1_is_at_least_conditional() -> None:
    result = assess_exposure(
        [_evidence("HIGH", EvidenceLevel.E1, 0.9)],
        CHECKS,
        _outcomes(CRIT="clear", HIGH="found", MED="clear"),
    )

    assert result.exposure == pytest.approx(0.8 / 2.4)
    assert result.verdict is Verdict.CONDITIONAL
    assert any("下限" in reason for reason in result.reasons)


def test_low_assurance_blocks_pass_even_if_exposure_is_low() -> None:
    result = assess_exposure(
        [],
        CHECKS,
        _outcomes(CRIT="clear", HIGH="not_tested", MED="not_tested"),
    )

    assert result.exposure == pytest.approx(1.4 / 2.4)
    assert result.assurance == pytest.approx(1.0 / 2.4)
    assert result.verdict is Verdict.CONDITIONAL
    assert any("证据不足" in reason for reason in result.reasons)


def test_multiple_evidence_uses_strongest_level() -> None:
    evidence = [
        _evidence("CRIT", EvidenceLevel.E3, 0.4, suffix="weak"),
        _evidence("CRIT", EvidenceLevel.E1, 0.9, suffix="strong"),
    ]
    result = assess_exposure(
        evidence,
        CHECKS,
        _outcomes(CRIT="found", HIGH="clear", MED="clear"),
    )

    assert result.per_check["CRIT"]["level"] == "E1"
    assert result.verdict is Verdict.REJECT
    assert any("CRIT(E1" in reason for reason in result.reasons)


def test_unknown_check_or_inconsistent_status_raises() -> None:
    with pytest.raises(ValueError):
        assess_exposure(
            [_evidence("NOPE", EvidenceLevel.E3, 0.5)], CHECKS
        )
    with pytest.raises(ValueError):
        assess_exposure([], CHECKS, {"NOPE": "not_tested"})
    with pytest.raises(ValueError):
        assess_exposure([], CHECKS, {"CRIT": "found"})
    with pytest.raises(ValueError):
        assess_exposure(
            [_evidence("CRIT", EvidenceLevel.E3, 0.5)], CHECKS, {"CRIT": "clear"}
        )


def test_load_checks_reads_all_nine_baseline_checks() -> None:
    checks = load_checks()

    assert len(checks) == 9
    assert sum(check.weight for check in checks) == pytest.approx(7.1)
    assert {check.code for check in checks} >= {
        "CRED_DEFAULT_ADMIN_WEB",
        "UNAUTH_MGMT_ENDPOINT",
        "EGRESS_FIXED_CLOUD_ENDPOINT",
    }


def test_main_accepts_explicit_outcomes_for_pass_sample(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    outcomes_path = tmp_path / "outcomes.json"
    output = tmp_path / "decision.json"
    evidence_path.write_text(
        json.dumps({"firmware_id": "CLEAN", "evidence": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    outcomes = {check.code: "clear" for check in load_checks()}
    outcomes_path.write_text(json.dumps(outcomes, ensure_ascii=False), encoding="utf-8")

    assert (
        main(
            [
                str(evidence_path),
                "--firmware-id",
                "CLEAN",
                "--outcomes",
                str(outcomes_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["verdict"] == "pass"
    assert payload["exposure"] == pytest.approx(0.0)
    assert payload["assurance"] == pytest.approx(1.0)
