"""src.report 的判定报告、Markdown/JSON 与 CLI 测试。"""

from __future__ import annotations

import json
from pathlib import Path

from src.exposure import ExposureResult
from src.report import (
    build_report,
    decision_from_exposure,
    main,
    render_json,
    render_markdown,
)
from src.schema import (
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
        id="A3",
        vendor="Tenda",
        model="AC15",
        version="V15.03.05.18",
        sha256="TODO(measure)",
        source_url="https://example.invalid/ac15.zip",
    )


def _evidence(check_code: str, level: EvidenceLevel = EvidenceLevel.E3) -> Evidence:
    return Evidence(
        id=f"E-A3-{check_code}",
        firmware_id="A3",
        check_code=check_code,
        level=level,
        confidence=0.5,
        raw_ref="webroot_ro/config.cfg:1",
        detail="静态发现，待实测",
    )


def _result() -> ExposureResult:
    return ExposureResult(
        exposure=0.642,
        assurance=0.262,
        verdict=Verdict.CONDITIONAL,
        confidence=0.5,
        reasons=["证据不足：assurance=0.262 < 0.60"],
        per_check={"CRED_DEFAULT_ADMIN_WEB": {"status": "found"}},
    )


def test_decision_from_exposure_carries_fields() -> None:
    evidence = [_evidence("CRED_DEFAULT_ADMIN_WEB")]
    decision = decision_from_exposure("A3", evidence, _result())

    assert decision.firmware_id == "A3"
    assert decision.verdict is Verdict.CONDITIONAL
    assert decision.confidence == 0.5
    assert decision.exposure == 0.642
    assert decision.evidence_ids == ["E-A3-CRED_DEFAULT_ADMIN_WEB"]


def test_build_report_static_only_and_counts() -> None:
    evidence = [
        _evidence("CRED_DEFAULT_ADMIN_WEB"),
        _evidence("UNAUTH_MGMT_ENDPOINT"),
        _evidence("EGRESS_FIXED_CLOUD_ENDPOINT"),
    ]
    decision = decision_from_exposure("A3", evidence, _result())
    report = build_report(
        _firmware(), decision, evidence, exposure_result=_result()
    )

    assert report["firmware"]["model"] == "AC15"
    assert report["decision"]["verdict"] == "conditional"
    assert report["evidence"]["total"] == 3
    assert report["evidence"]["by_level"]["E3"] == 3
    assert report["evidence"]["by_category"]["CRED"] == 1
    assert report["evidence"]["by_category"]["UNAUTH"] == 1
    assert report["evidence"]["by_category"]["EGRESS"] == 1
    assert report["static_only"] is True
    assert "E3" in report["disclaimer"]
    assert report["assurance"] == 0.262


def test_build_report_with_policy() -> None:
    policy = Policy(
        firmware_id="A3",
        granularity=Granularity.FQDN,
        rule_format=RuleFormat.ACL,
        rules=["permit tcp any host www.tenda.com.cn eq 443"],
        asn_fallback=False,
        rollback_ref="rb-A3",
    )
    evidence = [_evidence("EGRESS_FIXED_CLOUD_ENDPOINT")]
    report = build_report(_firmware(), decision_from_exposure("A3", evidence, _result()), evidence, policy)

    assert report["policy"]["granularity"] == "fqdn"
    assert report["policy"]["rule_count"] == 1
    assert report["policy"]["rollback_ref"] == "rb-A3"


def test_render_markdown_contains_sections() -> None:
    evidence = [_evidence("CRED_DEFAULT_ADMIN_WEB")]
    report = build_report(_firmware(), decision_from_exposure("A3", evidence, _result()), evidence)
    markdown = render_markdown(report)

    assert "# 入网体检报告：A3" in markdown
    assert "## 1. 结论" in markdown
    assert "## 2. 证据清单" in markdown
    assert "webroot_ro/config.cfg:1" in markdown
    assert "E3" in markdown
    assert "TODO(measure)" in markdown
    assert "本样例未生成策略" in markdown


def test_render_json_roundtrip() -> None:
    evidence = [_evidence("CRED_DEFAULT_ADMIN_WEB")]
    report = build_report(_firmware(), decision_from_exposure("A3", evidence, _result()), evidence)

    assert json.loads(render_json(report)) == report


def test_main_writes_markdown_with_policy(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output = tmp_path / "report.md"
    payload = {
        "firmware_id": "A3",
        "evidence": [
            {
                "id": "E-A3-1",
                "firmware_id": "A3",
                "check_code": "EGRESS_FIXED_CLOUD_ENDPOINT",
                "level": "E3",
                "confidence": 0.4,
                "raw_ref": "webroot_ro/default.cfg:86",
                "detail": "静态发现硬编码 https 外联地址 host=www.tenda.com.cn；待实测",
            }
        ],
    }
    evidence_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    assert (
        main(
            [
                "--evidence",
                str(evidence_path),
                "--firmware-id",
                "A3",
                "--vendor",
                "Tenda",
                "--model",
                "AC15",
                "--version",
                "V15.03.05.18",
                "--output",
                str(output),
                "--with-policy",
            ]
        )
        == 0
    )
    text = output.read_text(encoding="utf-8")
    assert "# 入网体检报告：A3" in text
    assert "conditional" in text
    assert "permit tcp any host www.tenda.com.cn eq 443" in text
