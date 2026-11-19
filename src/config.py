"""configs/ 下基线、锚点、判定口径的加载与结构校验。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "ANCHORS_PATH",
    "BASELINE_PATH",
    "JUDGEMENT_PATH",
    "load_yaml",
    "validate_anchors",
    "validate_baseline",
    "validate_judgement",
]

BASELINE_PATH: Path = Path("configs/baseline.yaml")
ANCHORS_PATH: Path = Path("configs/anchors.yaml")
JUDGEMENT_PATH: Path = Path("configs/judgement.yaml")

_EVIDENCE_KEYS = {"E1", "E2", "E3"}
_CHECK_FIELDS = ("code", "category", "name", "severity", "weight", "source")


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} 必须是 mapping，收到 {type(value).__name__}")
    return value


def _require_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} 必须是数值，收到 {value!r}")
    return float(value)


def load_yaml(path: str | Path) -> dict[str, Any]:
    """读取 YAML 配置，路径缺失抛 FileNotFoundError，内容非法抛 ValueError。"""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"{file_path.name}: YAML 解析失败: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{file_path.name}: 根节点必须是 mapping，收到 {type(data).__name__}")
    return data


def validate_baseline(data: dict[str, Any]) -> None:
    """校验检查项基线的字段完整性、权重一致性与阈值/置信度取值。"""
    root = _require_mapping(data, "baseline")
    weight_mapping = _require_mapping(root.get("weight_mapping"), "weight_mapping")
    if not weight_mapping:
        raise ValueError("weight_mapping 不能为空")

    checks = root.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("checks 必须是非空 list")

    seen_codes: set[str] = set()
    for index, check in enumerate(checks):
        item = _require_mapping(check, f"checks[{index}]")
        missing = [field for field in _CHECK_FIELDS if item.get(field) in (None, "")]
        if missing:
            raise ValueError(f"checks[{index}] 缺少字段: {', '.join(missing)}")

        code = item["code"]
        if code in seen_codes:
            raise ValueError(f"checks 中 code 重复: {code!r}")
        seen_codes.add(code)

        severity = item["severity"]
        if severity not in weight_mapping:
            raise ValueError(f"checks[{index}].severity 不在 weight_mapping: {severity!r}")

        weight = _require_number(item["weight"], f"checks[{index}].weight")
        if not 0.0 < weight <= 1.0:
            raise ValueError(f"checks[{index}].weight 必须在 (0.0, 1.0]，收到 {weight}")
        expected = _require_number(weight_mapping[severity], f"weight_mapping[{severity!r}]")
        if weight != expected:
            raise ValueError(
                f"checks[{index}].weight 与 weight_mapping[{severity!r}] 不一致: "
                f"{weight} != {expected}"
            )

    thresholds = _require_mapping(root.get("verdict_thresholds"), "verdict_thresholds")
    pass_max = _require_number(thresholds.get("pass_max"), "verdict_thresholds.pass_max")
    conditional_max = _require_number(
        thresholds.get("conditional_max"), "verdict_thresholds.conditional_max"
    )
    if not 0.0 < pass_max < conditional_max <= 1.0:
        raise ValueError(
            "verdict_thresholds 必须满足 0.0 < pass_max < conditional_max <= 1.0，"
            f"收到 pass_max={pass_max}, conditional_max={conditional_max}"
        )

    confidence = _require_mapping(root.get("default_confidence"), "default_confidence")
    if set(confidence) != _EVIDENCE_KEYS:
        raise ValueError(
            f"default_confidence 的键必须恰为 {sorted(_EVIDENCE_KEYS)}，"
            f"收到 {sorted(confidence)}"
        )
    for level, value in confidence.items():
        ratio = _require_number(value, f"default_confidence.{level}")
        if not 0.0 <= ratio <= 1.0:
            raise ValueError(f"default_confidence.{level} 必须在 [0.0, 1.0]，收到 {ratio}")


def validate_anchors(data: dict[str, Any]) -> None:
    """校验锚点库数量、id 唯一性，以及已验证锚点必须可下载且版本明确。"""
    root = _require_mapping(data, "anchors.yaml")
    anchors = root.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != 3:
        raise ValueError(
            f"anchors 必须是长度恰为 3 的 list，收到 {len(anchors) if isinstance(anchors, list) else type(anchors).__name__}"
        )

    seen_ids: set[str] = set()
    for index, anchor in enumerate(anchors):
        item = _require_mapping(anchor, f"anchors[{index}]")
        anchor_id = item.get("id")
        if anchor_id in (None, ""):
            raise ValueError(f"anchors[{index}] 缺少字段 id")
        if anchor_id in seen_ids:
            raise ValueError(f"anchors 中 id 重复: {anchor_id!r}")
        seen_ids.add(anchor_id)

        if item.get("verified") is True:
            download = item.get("download")
            if not isinstance(download, str) or not download.startswith("http"):
                raise ValueError(
                    f"anchors[{index}] 已验证但 download 不是 http(s) 链接: {download!r}"
                )
            firmware = item.get("firmware")
            if firmware in (None, "", "TBD"):
                raise ValueError(
                    f"anchors[{index}] 已验证但 firmware 未填写具体版本: {firmware!r}"
                )


def validate_judgement(data: dict[str, Any]) -> None:
    """校验判定口径：证据等级齐全，且明确不依赖真机（纯仿真口径）。"""
    root = _require_mapping(data, "judgement")
    levels = _require_mapping(root.get("evidence_levels"), "evidence_levels")
    if set(levels) != _EVIDENCE_KEYS:
        raise ValueError(
            f"evidence_levels 的键必须恰为 {sorted(_EVIDENCE_KEYS)}，收到 {sorted(levels)}"
        )
    meta = _require_mapping(root.get("meta"), "meta")
    if meta.get("real_device_required") is not False:
        raise ValueError("meta.real_device_required 必须为 false（纯仿真口径）")