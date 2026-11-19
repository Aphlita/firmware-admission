"""src.schema 数据契约的合法构造与非法取值测试。"""

import json
from dataclasses import asdict

import pytest

from src.schema import (
    Decision,
    Evidence,
    EvidenceLevel,
    Firmware,
    Granularity,
    Policy,
    RuleFormat,
    Verdict,
)


def _firmware() -> Firmware:
    return Firmware(
        id="fw-0001",
        vendor="sample-vendor",
        model="sample-model",
        version="1.0.0",
        sha256="0" * 64,
        source_url="file:///data/sample/firmware.bin",
    )


def test_valid_models_build_and_serialize_to_json() -> None:
    firmware = _firmware()
    evidence = Evidence(
        id="ev-0001",
        firmware_id=firmware.id,
        check_code="PORT_TELNET_23",
        level="E1",
        confidence=0.9,
        raw_ref="materials/raw/ev-0001.txt",
    )
    decision = Decision(
        firmware_id=firmware.id,
        verdict=Verdict.REJECT,
        confidence=1,
        reasons=["23/tcp 开放"],
        evidence_ids=[evidence.id],
    )
    policy = Policy(
        firmware_id=firmware.id,
        granularity="fqdn",
        rule_format=RuleFormat.ACL,
        rules=["deny tcp any"],
    )

    assert evidence.level is EvidenceLevel.E1
    assert policy.granularity is Granularity.FQDN
    assert policy.asn_fallback is False
    assert decision.exposure is None
    assert firmware.family is None
    assert json.loads(json.dumps(asdict(evidence)))["level"] == "E1"
    assert json.loads(json.dumps(asdict(decision)))["verdict"] == "reject"


@pytest.mark.parametrize("level", ["E4", "e1", None])
def test_evidence_rejects_invalid_level(level: object) -> None:
    with pytest.raises(ValueError):
        Evidence(
            id="ev-0001",
            firmware_id="fw-0001",
            check_code="X",
            level=level,  # type: ignore[arg-type]
            confidence=0.5,
            raw_ref="r",
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.01, "0.5", True])
def test_evidence_rejects_invalid_confidence(confidence: object) -> None:
    with pytest.raises(ValueError):
        Evidence(
            id="ev-0001",
            firmware_id="fw-0001",
            check_code="X",
            level=EvidenceLevel.E2,
            confidence=confidence,  # type: ignore[arg-type]
            raw_ref="r",
        )


@pytest.mark.parametrize("verdict", ["maybe", ""])
def test_decision_rejects_invalid_verdict(verdict: object) -> None:
    with pytest.raises(ValueError):
        Decision(
            firmware_id="fw-0001",
            verdict=verdict,  # type: ignore[arg-type]
            confidence=0.5,
            reasons=[],
            evidence_ids=[],
        )


@pytest.mark.parametrize("exposure", [-0.01, 1.5])
def test_decision_rejects_out_of_range_exposure(exposure: float) -> None:
    with pytest.raises(ValueError):
        Decision(
            firmware_id="fw-0001",
            verdict=Verdict.PASS,
            confidence=0.5,
            reasons=[],
            evidence_ids=[],
            exposure=exposure,
        )


def test_policy_rejects_invalid_enums() -> None:
    with pytest.raises(ValueError):
        Policy(
            firmware_id="fw-0001",
            granularity="ip",  # type: ignore[arg-type]
            rule_format=RuleFormat.MUD,
            rules=[],
        )
    with pytest.raises(ValueError):
        Policy(
            firmware_id="fw-0001",
            granularity=Granularity.ASN,
            rule_format="bgp",  # type: ignore[arg-type]
            rules=[],
        )