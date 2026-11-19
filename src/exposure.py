"""敞口与三态判定（T2-1）。

口径说明见 ``materials/判定口径-T2-1.md``。核心修正：
1. ``Evidence`` 是“阳性发现”，E1 不能像旧公式那样贡献 0；E1 按满权重计风险。
2. E2/E3 按 ``w * confidence`` 计风险，未测试项按 ``w`` 计最坏风险。
3. 另算加权证据覆盖率 ``assurance``，覆盖率不足时只能给“有条件”，不能直接放行。
4. Critical 项的 E1 是硬红线；Critical 的 E2/E3、High 的 E1 至少“有条件”。

阈值是 provisional，需用锚点集校准；本模块只做计算，不把 provisional 值写成实测指标。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.config import BASELINE_PATH, load_yaml, validate_baseline
from src.schema import Evidence, EvidenceLevel, Verdict

__all__ = ["CheckSpec", "ExposureResult", "assess_exposure", "load_checks", "main"]

_STATUSES = frozenset({"clear", "found", "not_tested"})
_LEVEL_RANK = {
    EvidenceLevel.E1: 3,
    EvidenceLevel.E2: 2,
    EvidenceLevel.E3: 1,
}


@dataclass(frozen=True)
class CheckSpec:
    """判定所需的最小检查项定义，来自 configs/baseline.yaml。"""

    code: str
    category: str
    name: str
    severity: str
    weight: float


@dataclass(frozen=True)
class ExposureResult:
    """一次固件判定的结构化结果。"""

    exposure: float
    assurance: float
    verdict: Verdict
    confidence: float
    reasons: list[str]
    per_check: dict[str, dict[str, Any]] = field(default_factory=dict)


def load_checks(path: str | Path = BASELINE_PATH) -> list[CheckSpec]:
    """从 baseline.yaml 读取 9 个检查项，并复用 config 的字段校验。"""
    data = load_yaml(path)
    validate_baseline(data)
    return [
        CheckSpec(
            code=item["code"],
            category=item["category"],
            name=item["name"],
            severity=item["severity"],
            weight=float(item["weight"]),
        )
        for item in data["checks"]
    ]


def _validate_checks(checks: Sequence[CheckSpec]) -> float:
    if not checks:
        raise ValueError("checks 不能为空")
    codes = [check.code for check in checks]
    if len(codes) != len(set(codes)):
        raise ValueError("checks 中 code 重复")
    total = 0.0
    for check in checks:
        if check.weight <= 0 or check.weight > 1:
            raise ValueError(f"{check.code}.weight 必须在 (0.0, 1.0]，收到 {check.weight}")
        total += check.weight
    return total


def _validate_thresholds(pass_max: float, conditional_max: float, assurance_min: float) -> None:
    if not 0.0 <= pass_max < conditional_max <= 1.0:
        raise ValueError(
            "必须满足 0.0 <= pass_max < conditional_max <= 1.0，"
            f"收到 pass_max={pass_max}, conditional_max={conditional_max}"
        )
    if not 0.0 <= assurance_min <= 1.0:
        raise ValueError(f"assurance_min 必须在 [0.0, 1.0]，收到 {assurance_min}")


def _group_evidence(evidence: Sequence[Evidence], known: set[str]) -> dict[str, list[Evidence]]:
    grouped: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        if item.check_code not in known:
            raise ValueError(f"evidence 的 check_code 不在 baseline 中: {item.check_code!r}")
        grouped[item.check_code].append(item)
    return grouped


def _resolve_statuses(
    checks: Sequence[CheckSpec],
    grouped: Mapping[str, list[Evidence]],
    outcomes: Mapping[str, str] | None,
) -> dict[str, str]:
    codes = {check.code for check in checks}
    if outcomes is None:
        return {
            check.code: "found" if grouped.get(check.code) else "not_tested"
            for check in checks
        }

    unknown = set(outcomes) - codes
    if unknown:
        raise ValueError(f"outcomes 含未知 check_code: {sorted(unknown)}")

    statuses: dict[str, str] = {}
    for check in checks:
        status = outcomes.get(check.code, "not_tested")
        if status not in _STATUSES:
            raise ValueError(
                f"{check.code}.status 只接受 {sorted(_STATUSES)}，收到 {status!r}"
            )
        has_evidence = bool(grouped.get(check.code))
        if status == "found" and not has_evidence:
            raise ValueError(f"{check.code} 标为 found 但没有 Evidence")
        if status in {"clear", "not_tested"} and has_evidence:
            raise ValueError(f"{check.code} 有 Evidence 但 status={status}")
        statuses[check.code] = status
    return statuses


def _strongest(items: Sequence[Evidence]) -> Evidence:
    return max(items, key=lambda item: (_LEVEL_RANK[item.level], item.confidence))


def _check_risk(check: CheckSpec, status: str, chosen: Evidence | None) -> tuple[float, float]:
    """返回 (风险贡献, 证据保障度)；未知项按最坏风险、零保障处理。"""
    if status == "clear":
        return 0.0, 1.0
    if status == "not_tested" or chosen is None:
        return check.weight, 0.0
    if chosen.level is EvidenceLevel.E1:
        return check.weight, 1.0
    return check.weight * chosen.confidence, chosen.confidence


def _gate_reasons(
    check: CheckSpec,
    chosen: Evidence | None,
) -> tuple[bool, bool]:
    """返回 (是否硬拒绝, 是否至少有条件)。"""
    if chosen is None:
        return False, False
    if check.severity == "Critical":
        if chosen.level is EvidenceLevel.E1:
            return True, False
        return False, True
    if check.severity == "High" and chosen.level is EvidenceLevel.E1:
        return False, True
    return False, False


def _score_checks(
    checks: Sequence[CheckSpec],
    statuses: Mapping[str, str],
    grouped: Mapping[str, list[Evidence]],
) -> tuple[
    float,
    float,
    dict[str, dict[str, Any]],
    list[tuple[CheckSpec, Evidence]],
    list[tuple[CheckSpec, Evidence]],
    list[tuple[CheckSpec, Evidence]],
]:
    exposure_num = 0.0
    assurance_num = 0.0
    per_check: dict[str, dict[str, Any]] = {}
    hard_reject: list[tuple[CheckSpec, Evidence]] = []
    hard_conditional: list[tuple[CheckSpec, Evidence]] = []
    findings: list[tuple[CheckSpec, Evidence]] = []

    for check in checks:
        status = statuses[check.code]
        chosen = _strongest(grouped[check.code]) if status == "found" else None
        risk, check_assurance = _check_risk(check, status, chosen)
        exposure_num += risk
        assurance_num += check.weight * check_assurance
        per_check[check.code] = {
            "status": status,
            "severity": check.severity,
            "weight": check.weight,
            "risk": risk,
            "assurance": check_assurance,
            "level": chosen.level.value if chosen else None,
            "confidence": chosen.confidence if chosen else None,
        }
        if chosen is None:
            continue
        findings.append((check, chosen))
        reject, conditional = _gate_reasons(check, chosen)
        if reject:
            hard_reject.append((check, chosen))
        elif conditional:
            hard_conditional.append((check, chosen))
    return (
        exposure_num,
        assurance_num,
        per_check,
        hard_reject,
        hard_conditional,
        findings,
    )


def _decide_verdict(
    hard_reject: Sequence[tuple[CheckSpec, Evidence]],
    hard_conditional: Sequence[tuple[CheckSpec, Evidence]],
    exposure: float,
    assurance: float,
    *,
    pass_max: float,
    conditional_max: float,
    assurance_min: float,
) -> Verdict:
    if hard_reject:
        return Verdict.REJECT
    if assurance >= assurance_min and exposure > conditional_max:
        return Verdict.REJECT
    if hard_conditional or assurance < assurance_min or exposure > pass_max:
        return Verdict.CONDITIONAL
    return Verdict.PASS


def _decision_confidence(
    verdict: Verdict,
    assurance: float,
    hard_reject: Sequence[tuple[CheckSpec, Evidence]],
    hard_conditional: Sequence[tuple[CheckSpec, Evidence]],
) -> float:
    if verdict is Verdict.PASS:
        return assurance
    driving = max(
        (item.confidence for _, item in [*hard_reject, *hard_conditional]),
        default=0.0,
    )
    return max(assurance, driving)


def assess_exposure(
    evidence: Sequence[Evidence],
    checks: Sequence[CheckSpec],
    outcomes: Mapping[str, str] | None = None,
    *,
    pass_max: float = 0.2,
    conditional_max: float = 0.6,
    assurance_min: float = 0.6,
) -> ExposureResult:
    """计算加权敞口、证据保障度与三态判定。

    ``outcomes`` 缺省时：有 Evidence 的检查项记 found，其余记 not_tested。
    要得到 clear，必须由调用方显式传入（T1-2 只产出阳性发现，不能把“没扫到”当 clear）。
    """
    _validate_thresholds(pass_max, conditional_max, assurance_min)
    checks = list(checks)
    total_weight = _validate_checks(checks)
    grouped = _group_evidence(evidence, {check.code for check in checks})
    statuses = _resolve_statuses(checks, grouped, outcomes)

    (
        exposure_num,
        assurance_num,
        per_check,
        hard_reject,
        hard_conditional,
        findings,
    ) = _score_checks(checks, statuses, grouped)
    exposure = exposure_num / total_weight
    assurance = assurance_num / total_weight
    verdict = _decide_verdict(
        hard_reject,
        hard_conditional,
        exposure,
        assurance,
        pass_max=pass_max,
        conditional_max=conditional_max,
        assurance_min=assurance_min,
    )
    confidence = _decision_confidence(verdict, assurance, hard_reject, hard_conditional)
    reasons = _build_reasons(
        verdict,
        exposure,
        assurance,
        pass_max,
        conditional_max,
        assurance_min,
        hard_reject,
        hard_conditional,
        findings,
    )
    return ExposureResult(
        exposure=exposure,
        assurance=assurance,
        verdict=verdict,
        confidence=confidence,
        reasons=reasons,
        per_check=per_check,
    )


def _build_reasons(
    verdict: Verdict,
    exposure: float,
    assurance: float,
    pass_max: float,
    conditional_max: float,
    assurance_min: float,
    hard_reject: Sequence[tuple[CheckSpec, Evidence]],
    hard_conditional: Sequence[tuple[CheckSpec, Evidence]],
    findings: Sequence[tuple[CheckSpec, Evidence]],
) -> list[str]:
    reasons: list[str] = []
    for check, item in hard_reject:
        reasons.append(
            f"红线：{check.code}（{check.severity}）为 {item.level.value} 确认风险，直接拒绝"
        )
    if verdict is not Verdict.REJECT:
        for check, item in hard_conditional:
            reasons.append(
                f"下限：{check.code}（{check.severity}）为 {item.level.value} 风险，至少条件放行"
            )
    if assurance < assurance_min:
        reasons.append(
            f"证据不足：加权保障度 assurance={assurance:.3f} < {assurance_min:.2f}，"
            "未测项或弱证据占比较高，不能直接放行"
        )
    if verdict is Verdict.REJECT and assurance >= assurance_min and exposure > conditional_max:
        reasons.append(f"敞口过高：U={exposure:.3f} > conditional_max={conditional_max:.2f}")
    elif verdict is Verdict.CONDITIONAL and assurance >= assurance_min and exposure > pass_max:
        reasons.append(f"敞口偏高：U={exposure:.3f} > pass_max={pass_max:.2f}")
    elif verdict is Verdict.PASS:
        reasons.append(
            f"放行：U={exposure:.3f} <= pass_max={pass_max:.2f}，"
            f"assurance={assurance:.3f} >= {assurance_min:.2f}"
        )
    if findings:
        summary = "；".join(
            f"{check.code}({item.level.value},c={item.confidence:.2f})"
            for check, item in findings[:5]
        )
        reasons.append(f"风险项 {len(findings)} 个：{summary}")
    return reasons


def _load_evidence_file(path: str | Path) -> tuple[list[Evidence], str | None]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("evidence", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("evidence JSON 必须是 list 或含 evidence 字段的对象")
    evidence = [
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
    firmware_id = data.get("firmware_id") if isinstance(data, dict) else None
    return evidence, firmware_id


def main(argv: list[str] | None = None) -> int:
    """CLI：读取 evidence JSON，输出敞口 + 三态判定。"""
    parser = argparse.ArgumentParser(description="敞口与三态判定（T2-1）")
    parser.add_argument("evidence", help="src.evidence 产出的 JSON")
    parser.add_argument("--firmware-id", default=None)
    parser.add_argument("--checks", default=str(BASELINE_PATH))
    parser.add_argument("--output", default=None)
    parser.add_argument("--pass-max", type=float, default=0.2)
    parser.add_argument("--conditional-max", type=float, default=0.6)
    parser.add_argument("--assurance-min", type=float, default=0.6)
    args = parser.parse_args(argv)

    try:
        evidence, source_id = _load_evidence_file(args.evidence)
        firmware_id = args.firmware_id or source_id or Path(args.evidence).stem
        result = assess_exposure(
            evidence,
            load_checks(args.checks),
            pass_max=args.pass_max,
            conditional_max=args.conditional_max,
            assurance_min=args.assurance_min,
        )
    except (OSError, KeyError, ValueError) as exc:
        print(f"判定失败: {exc}", file=sys.stderr)
        return 2

    payload = {
        "firmware_id": firmware_id,
        "verdict": result.verdict.value,
        "confidence": result.confidence,
        "exposure": result.exposure,
        "assurance": result.assurance,
        "reasons": result.reasons,
        "per_check": result.per_check,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
