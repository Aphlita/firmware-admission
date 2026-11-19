"""端到端冒烟：配置校验 → 证据 → 判定 → 策略 → JSON 落盘读回。

只使用锚点元数据与占位字符串，不写入任何真实漏洞结论。
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from src.config import (
    ANCHORS_PATH,
    BASELINE_PATH,
    JUDGEMENT_PATH,
    load_yaml,
    validate_anchors,
    validate_baseline,
    validate_judgement,
)
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


def _anchor_a1() -> dict[str, Any]:
    anchors = load_yaml(ANCHORS_PATH)["anchors"]
    return next(anchor for anchor in anchors if anchor["id"] == "A1")


def _build_chain(anchor: dict[str, Any]) -> tuple[Firmware, Evidence, Decision, Policy]:
    firmware = Firmware(
        id="A1",
        vendor="Tenda",
        model="O4 V3.0",
        version="V1.0.0.19(6074)",
        sha256="0" * 64,
        source_url=anchor["download"],
        family=None,
    )
    evidence = Evidence(
        id="E-A1-1",
        firmware_id=firmware.id,
        check_code="CRED_DEFAULT_SERVICE_LOGIN",
        level=EvidenceLevel.E1,
        confidence=0.9,
        raw_ref="materials/schema_sample.json:1",
        detail="占位",
    )
    decision = Decision(
        firmware_id=firmware.id,
        verdict=Verdict.CONDITIONAL,
        confidence=0.9,
        reasons=["占位"],
        evidence_ids=[evidence.id],
        exposure=0.4,
    )
    policy = Policy(
        firmware_id=firmware.id,
        granularity=Granularity.VENDOR_GROUP,
        rule_format=RuleFormat.MUD,
        rules=["占位"],
        asn_fallback=True,
        rollback_ref="rb-A1",
    )
    return firmware, evidence, decision, policy


def test_config_evidence_decision_policy_roundtrip(tmp_path: Path) -> None:
    baseline = load_yaml(BASELINE_PATH)
    anchors = load_yaml(ANCHORS_PATH)
    judgement = load_yaml(JUDGEMENT_PATH)
    validate_baseline(baseline)
    validate_anchors(anchors)
    validate_judgement(judgement)

    anchor = _anchor_a1()
    firmware, evidence, decision, policy = _build_chain(anchor)
    assert (firmware.vendor, firmware.model, firmware.version) == (
        anchor["vendor"],
        anchor["model"],
        anchor["firmware"],
    )

    payload = {
        "firmware": asdict(firmware),
        "evidence": asdict(evidence),
        "decision": asdict(decision),
        "policy": asdict(policy),
    }
    smoke_path = tmp_path / "smoke.json"
    smoke_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    loaded = json.loads(smoke_path.read_text(encoding="utf-8"))
    assert set(loaded) == {"firmware", "evidence", "decision", "policy"}

    assert loaded["firmware"] == payload["firmware"]
    assert loaded["firmware"]["source_url"] == anchor["download"]
    assert loaded["firmware"]["family"] is None

    assert loaded["evidence"]["level"] == "E1"
    assert loaded["evidence"]["confidence"] == 0.9
    assert loaded["evidence"]["raw_ref"] == "materials/schema_sample.json:1"

    assert loaded["decision"]["verdict"] == "conditional"
    assert loaded["decision"]["exposure"] == 0.4
    assert loaded["decision"]["evidence_ids"] == ["E-A1-1"]

    assert loaded["policy"]["granularity"] == "vendor-group"
    assert loaded["policy"]["rule_format"] == "mud"
    assert loaded["policy"]["asn_fallback"] is True
    assert loaded["policy"]["rollback_ref"] == "rb-A1"


def test_evidence_rejects_unknown_level() -> None:
    with pytest.raises(ValueError):
        Evidence(
            id="E-A1-1",
            firmware_id="A1",
            check_code="CRED_DEFAULT_SERVICE_LOGIN",
            level="E9",  # type: ignore[arg-type]
            confidence=0.9,
            raw_ref="materials/schema_sample.json:1",
            detail="占位",
        )


def test_decision_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValueError):
        Decision(
            firmware_id="A1",
            verdict=Verdict.CONDITIONAL,
            confidence=1.5,
            reasons=["占位"],
            evidence_ids=["E-A1-1"],
            exposure=0.4,
        )