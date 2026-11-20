"""判定报告生成（T2-3）。

输入：Firmware + Decision + Evidence（可选 Policy / ExposureResult）。
输出：结构化 dict、Markdown 文本、JSON 文本。

报告必须把“证据等级”和“未实测”写在明面上：只有 E3 时，结论是静态初判，
不得写成实测结论；缺口统一标 ``TODO(measure)``。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from src.exposure import ExposureResult, assess_exposure, load_checks
from src.policy import build_policy, endpoints_from_evidence
from src.schema import Decision, Evidence, Firmware, Policy

__all__ = [
    "build_report",
    "decision_from_exposure",
    "main",
    "render_json",
    "render_markdown",
]

_DISCLAIMER_STATIC = (
    "本报告全部证据为 E3（静态推断），未在影子设备中实测；"
    "结论只作准入初判，具体可利用性写 TODO(measure)。"
)
_DISCLAIMER_MIXED = "本报告含 E1/E2 证据；实测结论必须带报文/响应原文 raw_ref。"


def decision_from_exposure(
    firmware_id: str,
    evidence: Sequence[Evidence],
    result: ExposureResult,
) -> Decision:
    """把 T2-1 的 ExposureResult 收敛为数据契约 Decision。"""
    return Decision(
        firmware_id=firmware_id,
        verdict=result.verdict,
        confidence=result.confidence,
        reasons=list(result.reasons),
        evidence_ids=[item.id for item in evidence],
        exposure=result.exposure,
    )


def _evidence_payload(item: Evidence) -> dict[str, Any]:
    return {
        "id": item.id,
        "check_code": item.check_code,
        "level": item.level.value,
        "confidence": item.confidence,
        "raw_ref": item.raw_ref,
        "detail": item.detail,
    }


def _counts(evidence: Sequence[Evidence]) -> dict[str, dict[str, int]]:
    by_level = Counter(item.level.value for item in evidence)
    by_category = Counter(item.check_code.split("_", 1)[0] for item in evidence)
    return {
        "by_level": {key: by_level.get(key, 0) for key in ("E1", "E2", "E3")},
        "by_category": {
            key: by_category.get(key, 0) for key in ("CRED", "UNAUTH", "EGRESS")
        },
    }


def build_report(
    firmware: Firmware,
    decision: Decision,
    evidence: Sequence[Evidence],
    policy: Policy | None = None,
    exposure_result: ExposureResult | None = None,
) -> dict[str, Any]:
    """组装可序列化的判定报告；不写文件。"""
    evidence_list = list(evidence)
    static_only = bool(evidence_list) and all(item.level.value == "E3" for item in evidence_list)
    report: dict[str, Any] = {
        "firmware": {
            "id": firmware.id,
            "vendor": firmware.vendor,
            "model": firmware.model,
            "version": firmware.version,
            "sha256": firmware.sha256,
            "source_url": firmware.source_url,
            "family": firmware.family,
        },
        "decision": {
            "verdict": decision.verdict.value,
            "confidence": decision.confidence,
            "exposure": decision.exposure,
            "reasons": list(decision.reasons),
            "evidence_ids": list(decision.evidence_ids),
        },
        "evidence": {
            "total": len(evidence_list),
            **_counts(evidence_list),
            "items": [_evidence_payload(item) for item in evidence_list],
        },
        "policy": None,
        "static_only": static_only,
        "disclaimer": _DISCLAIMER_STATIC if static_only else _DISCLAIMER_MIXED,
    }
    if policy is not None:
        report["policy"] = {
            "granularity": policy.granularity.value,
            "rule_format": policy.rule_format.value,
            "rule_count": len(policy.rules),
            "asn_fallback": policy.asn_fallback,
            "rollback_ref": policy.rollback_ref,
            "rules": list(policy.rules),
        }
    if exposure_result is not None:
        report["assurance"] = exposure_result.assurance
        report["per_check"] = exposure_result.per_check
    return report


def _safe_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _render_summary(report: dict[str, Any]) -> list[str]:
    firmware = report["firmware"]
    decision = report["decision"]
    lines = [
        f"# 入网体检报告：{firmware['id']}",
        "",
        "## 1. 结论",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 厂商 / 型号 | {_safe_cell(firmware['vendor'])} / {_safe_cell(firmware['model'])} |",
        f"| 固件版本 | {_safe_cell(firmware['version'])} |",
        f"| 判定 | **{_safe_cell(decision['verdict'])}** |",
        f"| 置信度 | {decision['confidence']:.3f} |",
        (
            f"| 风险敞口 | {decision['exposure']:.3f} |"
            if decision["exposure"] is not None
            else "| 风险敞口 | TODO(measure) |"
        ),
    ]
    if "assurance" in report:
        lines.append(f"| 加权保障度 | {report['assurance']:.3f} |")
    lines += ["", "**判定理由**", ""]
    lines += [f"- {_safe_cell(reason)}" for reason in decision["reasons"]] or ["- TODO(measure)"]
    return lines


def _render_evidence_section(evidence: dict[str, Any]) -> list[str]:
    level_text = " / ".join(f"{key}={value}" for key, value in evidence["by_level"].items())
    category_text = " / ".join(
        f"{key}={value}" for key, value in evidence["by_category"].items()
    )
    lines = [
        "",
        "## 2. 证据清单",
        "",
        f"共 **{evidence['total']}** 条；按等级：{level_text}；按类别：{category_text}。",
        "",
        "| 编号 | 检查项 | 等级 | 置信度 | raw_ref | 说明 |",
        "|---|---|---|---|---|---|",
    ]
    for item in evidence["items"]:
        lines.append(
            f"| {_safe_cell(item['id'])} | {_safe_cell(item['check_code'])} | "
            f"{_safe_cell(item['level'])} | {item['confidence']:.3f} | "
            f"{_safe_cell(item['raw_ref'])} | {_safe_cell(item['detail'])} |"
        )
    return lines


def _render_policy_section(policy: dict[str, Any] | None) -> list[str]:
    lines = ["", "## 3. 策略", ""]
    if policy is None:
        lines.append("本样例未生成策略。")
        return lines
    lines += [
        "| 项 | 值 |",
        "|---|---|",
        f"| 粒度 | {_safe_cell(policy['granularity'])} |",
        f"| 载体 | {_safe_cell(policy['rule_format'])} |",
        f"| 规则条数 | {policy['rule_count']} |",
        f"| ASN 回退 | {policy['asn_fallback']} |",
        f"| 回滚引用 | {_safe_cell(policy['rollback_ref'])} |",
        "",
        "```text",
        *policy["rules"],
        "```",
    ]
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    """把报告 dict 渲染为中文 Markdown。"""
    lines = _render_summary(report)
    lines += _render_evidence_section(report["evidence"])
    lines += _render_policy_section(report.get("policy"))
    lines += ["", "## 4. 口径与限制", "", f"- {report['disclaimer']}"]
    lines.append("- 阈值/置信度为 provisional，锚点集校准前不得写入材料指标。")
    return "\n".join(lines) + "\n"


def render_json(report: dict[str, Any]) -> str:
    """返回 UTF-8 JSON 文本。"""
    return json.dumps(report, ensure_ascii=False, indent=2)


def _load_evidence(path: str | Path) -> list[Evidence]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("evidence", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("evidence JSON 必须是 list 或含 evidence 字段的对象")
    return [
        Evidence(
            id=item["id"],
            firmware_id=item["firmware_id"],
            check_code=item["check_code"],
            level=item["level"],
            confidence=item["confidence"],
            raw_ref=item["raw_ref"],
            detail=item.get("detail", ""),
        )
        for item in items
    ]


def main(argv: list[str] | None = None) -> int:
    """CLI：evidence JSON → 敞口判定 → Markdown/JSON 报告。"""
    parser = argparse.ArgumentParser(description="判定报告生成（T2-3）")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--firmware-id", required=True)
    parser.add_argument("--vendor", default="unknown")
    parser.add_argument("--model", default="unknown")
    parser.add_argument("--version", default="unknown")
    parser.add_argument("--sha256", default="TODO(measure)")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--output", default=None)
    parser.add_argument("--format", choices=("md", "json"), default="md")
    parser.add_argument("--with-policy", action="store_true")
    args = parser.parse_args(argv)

    try:
        evidence = _load_evidence(args.evidence)
        result = assess_exposure(evidence, load_checks())
        decision = decision_from_exposure(args.firmware_id, evidence, result)
        policy = None
        if args.with_policy:
            policy = build_policy(
                args.firmware_id,
                endpoints_from_evidence(evidence),
                rollback_ref=f"rb-{args.firmware_id}",
            )
        firmware = Firmware(
            id=args.firmware_id,
            vendor=args.vendor,
            model=args.model,
            version=args.version,
            sha256=args.sha256,
            source_url=args.source_url,
            family=None,
        )
        report = build_report(firmware, decision, evidence, policy, result)
    except (OSError, KeyError, ValueError) as exc:
        print(f"报告生成失败: {exc}", file=sys.stderr)
        return 2

    text = render_json(report) if args.format == "json" else render_markdown(report)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
