"""T3-1 指标计算：kappa、覆盖率、误杀率、漏放率、ASN 回退与策略条数。

输入约定见 ``materials/标注模板.json``；所有分母为 0 的指标返回 ``None``，
由报告层写 ``N/A`` / ``TODO(measure)``，不用 0 冒充“没有发生”。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.schema import Policy

__all__ = [
    "MetricsResult",
    "agreement_rate",
    "asn_fallback_rate",
    "cohen_kappa",
    "compute_metrics",
    "coverage_rate",
    "false_block_rate",
    "load_annotation",
    "main",
    "miss_rate",
]

_VALID_STATUSES = frozenset({"clear", "found", "not_tested"})
_VALID_DECISIONS = frozenset({"pass", "conditional", "reject"})


@dataclass(frozen=True)
class MetricsResult:
    """一次指标计算的完整结果；未定义项为 None。"""

    coverage: float
    agreement: float | None
    kappa: float | None
    decision_accuracy: float | None
    false_block_rate: float | None
    miss_rate: float | None
    asn_fallback_rate: float | None
    policy_rule_count: int


def _check_labels(labels_a: Sequence[str], labels_b: Sequence[str]) -> None:
    if len(labels_a) != len(labels_b):
        raise ValueError("两组标注长度不一致")


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float | None:
    """Cohen's kappa；无样本或只有单一类别（pe=1）时未定义。"""
    _check_labels(labels_a, labels_b)
    total = len(labels_a)
    if total == 0:
        return None
    categories = sorted(set(labels_a) | set(labels_b))
    if len(categories) <= 1:
        return None
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / total
    expected = sum(
        (labels_a.count(category) / total) * (labels_b.count(category) / total)
        for category in categories
    )
    if expected >= 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def agreement_rate(labels_a: Sequence[str], labels_b: Sequence[str]) -> float | None:
    _check_labels(labels_a, labels_b)
    if not labels_a:
        return None
    return sum(a == b for a, b in zip(labels_a, labels_b)) / len(labels_a)


def coverage_rate(statuses: Mapping[Any, str]) -> float:
    if not statuses:
        return 0.0
    unknown = set(statuses.values()) - _VALID_STATUSES
    if unknown:
        raise ValueError(f"未知标注取值: {sorted(unknown)}")
    covered = sum(1 for status in statuses.values() if status in {"found", "clear"})
    return covered / len(statuses)


def _rate(numerator: int, denominator: int, field: str) -> float | None:
    if numerator < 0 or denominator < 0:
        raise ValueError(f"{field} 不能为负数")
    if denominator == 0:
        return None
    if numerator > denominator:
        raise ValueError(f"{field} 的分子不能大于分母")
    return numerator / denominator


def false_block_rate(false_blocks: int, legit_total: int) -> float | None:
    return _rate(false_blocks, legit_total, "false_block_rate")


def miss_rate(missed: int, malicious_total: int) -> float | None:
    return _rate(missed, malicious_total, "miss_rate")


def _flatten(labels: Mapping[str, Mapping[str, str]]) -> dict[tuple[str, str], str]:
    if not isinstance(labels, Mapping):
        raise ValueError("标注必须是 firmware -> check -> status 的 mapping")
    flat: dict[tuple[str, str], str] = {}
    for firmware_id, checks in labels.items():
        if not isinstance(checks, Mapping):
            raise ValueError(f"{firmware_id} 的标注必须是 mapping")
        for check_code, status in checks.items():
            if status not in _VALID_STATUSES:
                raise ValueError(f"{firmware_id}/{check_code} 的未知状态: {status!r}")
            key = (str(firmware_id), str(check_code))
            if key in flat:
                raise ValueError(f"重复标注: {key}")
            flat[key] = status
    return flat


def _decision_accuracy(decisions: Sequence[Mapping[str, Any]]) -> float | None:
    if not decisions:
        return None
    correct = 0
    for index, item in enumerate(decisions):
        expected = item.get("expected")
        actual = item.get("actual")
        if expected not in _VALID_DECISIONS or actual not in _VALID_DECISIONS:
            raise ValueError(f"decisions[{index}] 的 expected/actual 非法")
        correct += expected == actual
    return correct / len(decisions)


def _replay_rates(rows: Sequence[Mapping[str, Any]]) -> tuple[float | None, float | None]:
    if not rows:
        return None, None
    false_blocks = legit_total = missed = malicious_total = 0
    for index, row in enumerate(rows):
        try:
            false_blocks += int(row["false_blocks"])
            legit_total += int(row["legit_total"])
            missed += int(row["missed"])
            malicious_total += int(row["malicious_total"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"policy_replay[{index}] 字段非法") from None
    return (
        false_block_rate(false_blocks, legit_total),
        miss_rate(missed, malicious_total),
    )


def _policy_values(policies: Sequence[Policy | Mapping[str, Any]]) -> tuple[float | None, int]:
    if not policies:
        return None, 0
    fallback = 0
    rule_count = 0
    for index, policy in enumerate(policies):
        if isinstance(policy, Policy):
            fallback += bool(policy.asn_fallback)
            rule_count += len(policy.rules)
        elif isinstance(policy, Mapping):
            if "asn_fallback" not in policy or "rule_count" not in policy:
                raise ValueError(f"policies[{index}] 缺少 asn_fallback/rule_count")
            if not isinstance(policy["asn_fallback"], bool):
                raise ValueError(f"policies[{index}].asn_fallback 必须是 bool")
            fallback += policy["asn_fallback"]
            rule_count += int(policy["rule_count"])
        else:
            raise ValueError(f"policies[{index}] 类型非法")
    return fallback / len(policies), rule_count


def asn_fallback_rate(policies: Sequence[Policy | Mapping[str, Any]]) -> float | None:
    rate, _ = _policy_values(policies)
    return rate


def compute_metrics(annotation: Mapping[str, Any]) -> MetricsResult:
    """从标注 JSON 计算全部指标；A 为主标注，B 只用于一致性/kappa。"""
    if not isinstance(annotation, Mapping):
        raise ValueError("annotation 必须是 mapping")
    annotators = annotation.get("annotators", {})
    if not isinstance(annotators, Mapping):
        raise ValueError("annotators 必须是 mapping")

    coverage = 0.0
    agreement: float | None = None
    kappa: float | None = None
    if annotators:
        names = list(annotators)
        primary = _flatten(annotators[names[0]])
        coverage = coverage_rate(primary)
        if len(names) >= 2:
            secondary = _flatten(annotators[names[1]])
            if set(primary) != set(secondary):
                raise ValueError("两位标注者的 firmware/check 键集合不一致")
            keys = sorted(primary)
            agreement = agreement_rate(
                [primary[key] for key in keys], [secondary[key] for key in keys]
            )
            kappa = cohen_kappa(
                [primary[key] for key in keys], [secondary[key] for key in keys]
            )

    decisions = annotation.get("decisions", [])
    if not isinstance(decisions, list):
        raise ValueError("decisions 必须是 list")
    accuracy = _decision_accuracy(decisions)

    replay = annotation.get("policy_replay", [])
    if not isinstance(replay, list):
        raise ValueError("policy_replay 必须是 list")
    false_rate, miss = _replay_rates(replay)

    policies = annotation.get("policies", [])
    if not isinstance(policies, list):
        raise ValueError("policies 必须是 list")
    asn_rate, policy_count = _policy_values(policies)

    return MetricsResult(
        coverage=coverage,
        agreement=agreement,
        kappa=kappa,
        decision_accuracy=accuracy,
        false_block_rate=false_rate,
        miss_rate=miss,
        asn_fallback_rate=asn_rate,
        policy_rule_count=policy_count,
    )


def load_annotation(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("标注 JSON 根节点必须是对象")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T3-1 指标计算")
    parser.add_argument("annotation", help="标注 JSON")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    try:
        result = compute_metrics(load_annotation(args.annotation))
    except (OSError, KeyError, ValueError) as exc:
        print(f"指标计算失败: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(asdict(result), ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
