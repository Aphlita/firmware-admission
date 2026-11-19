"""src.config 的配置加载与三项配置结构校验测试。"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from src.config import (
    load_yaml,
    validate_anchors,
    validate_baseline,
    validate_judgement,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs"


def _baseline() -> dict[str, Any]:
    return {
        "weight_mapping": {
            "Critical": 1.0,
            "High": 0.8,
            "Medium": 0.6,
            "Low": 0.3,
        },
        "checks": [
            {
                "code": "CRED_DEFAULT_ADMIN_WEB",
                "category": "CRED",
                "name": "默认口令",
                "severity": "Critical",
                "weight": 1.0,
                "source": "src-a",
            },
            {
                "code": "EGRESS_UNREGISTERED_THIRD_PARTY",
                "category": "EGRESS",
                "name": "第三方外联",
                "severity": "Low",
                "weight": 0.3,
                "source": "src-b",
            },
        ],
        "verdict_thresholds": {"pass_max": 0.2, "conditional_max": 0.6},
        "default_confidence": {"E1": 0.9, "E2": 0.7, "E3": 0.5},
    }


def _anchors() -> dict[str, Any]:
    return {
        "anchors": [
            {
                "id": "A1",
                "firmware": "V1.0.0.19",
                "download": "https://example.invalid/fw.bin",
                "verified": True,
            },
            {"id": "A2", "firmware": "TBD", "download": "TBD", "verified": False},
            {"id": "A3", "firmware": "TBD", "download": "TBD", "verified": False},
        ]
    }


def _judgement() -> dict[str, Any]:
    return {
        "meta": {"real_device_required": False},
        "evidence_levels": {"E1": {}, "E2": {}, "E3": {}},
    }


def test_shipped_configs_validate() -> None:
    baseline = load_yaml(CONFIG_DIR / "baseline.yaml")
    anchors = load_yaml(CONFIG_DIR / "anchors.yaml")
    judgement = load_yaml(CONFIG_DIR / "judgement.yaml")

    validate_baseline(baseline)
    validate_anchors(anchors)
    validate_judgement(judgement)

    codes = {check["code"] for check in baseline["checks"]}
    assert len(codes) == 9
    assert {check["category"] for check in baseline["checks"]} == {"CRED", "UNAUTH", "EGRESS"}
    assert baseline["meta"]["provisional"] is True


def test_load_yaml_rejects_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_yaml(CONFIG_DIR / "no_such_config.yaml")


def test_load_yaml_rejects_malformed_yaml(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("checks: [1,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="broken.yaml"):
        load_yaml(path)


def test_load_yaml_rejects_non_mapping_root(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_yaml(path)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda d: d["checks"][0].update(weight=1.5), "weight"),
        (lambda d: d["checks"][0].update(weight=0.8), "不一致"),
        (lambda d: d["checks"][0].update(severity="Severe"), "weight_mapping"),
        (lambda d: d["checks"][1].update(code="CRED_DEFAULT_ADMIN_WEB"), "重复"),
        (lambda d: d["checks"][0].pop("source"), "缺少字段"),
        (lambda d: d.update(checks=[]), "非空 list"),
        (lambda d: d["verdict_thresholds"].update(pass_max=0.7), "pass_max"),
        (lambda d: d["verdict_thresholds"].update(conditional_max=0.2), "pass_max"),
        (lambda d: d["default_confidence"].pop("E3"), "default_confidence"),
        (lambda d: d["default_confidence"].update(E2=1.2), "default_confidence"),
    ],
)
def test_baseline_rejects_invalid_data(mutate: Any, match: str) -> None:
    data = copy.deepcopy(_baseline())
    mutate(data)
    with pytest.raises(ValueError, match=match):
        validate_baseline(data)


def test_baseline_rejects_non_mapping_root() -> None:
    with pytest.raises(ValueError):
        validate_baseline([])


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda d: d["anchors"].pop(), "长度恰为 3"),
        (lambda d: d["anchors"][1].update(id="A1"), "重复"),
        (lambda d: d["anchors"][0].update(download="TBD"), "download"),
        (lambda d: d["anchors"][0].update(firmware="TBD"), "firmware"),
        (lambda d: d["anchors"][0].update(download="ftp://example.invalid"), "download"),
    ],
)
def test_anchors_rejects_invalid_data(mutate: Any, match: str) -> None:
    data = copy.deepcopy(_anchors())
    mutate(data)
    with pytest.raises(ValueError, match=match):
        validate_anchors(data)


def test_anchors_allows_tbd_for_unverified() -> None:
    validate_anchors(_anchors())


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda d: d["evidence_levels"].pop("E3"), "evidence_levels"),
        (lambda d: d["meta"].update(real_device_required=True), "real_device_required"),
        (lambda d: d.pop("meta"), "meta"),
    ],
)
def test_judgement_rejects_invalid_data(mutate: Any, match: str) -> None:
    data = copy.deepcopy(_judgement())
    mutate(data)
    with pytest.raises(ValueError, match=match):
        validate_judgement(data)