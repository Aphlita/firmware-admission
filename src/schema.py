"""入网体检的唯一数据契约：固件、证据、判定、策略。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

__all__ = [
    "Decision",
    "Evidence",
    "EvidenceLevel",
    "Firmware",
    "Granularity",
    "Policy",
    "RuleFormat",
    "Verdict",
]


class EvidenceLevel(str, Enum):
    """证据分层：E1 实测 / E2 单点 / E3 静态。"""

    E1 = "E1"
    E2 = "E2"
    E3 = "E3"


class Verdict(str, Enum):
    """三态判定。"""

    PASS = "pass"
    CONDITIONAL = "conditional"
    REJECT = "reject"


class Granularity(str, Enum):
    """策略下发粒度。"""

    FQDN = "fqdn"
    VENDOR_GROUP = "vendor-group"
    ASN = "asn"


class RuleFormat(str, Enum):
    """策略载体格式。"""

    ACL = "acl"
    MUD = "mud"


_EnumT = TypeVar("_EnumT", bound=Enum)


def _to_enum(value: Any, enum_cls: type[_EnumT], field: str) -> _EnumT:
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, TypeError):
        allowed = ", ".join(member.value for member in enum_cls)
        raise ValueError(f"{field} 只接受 {allowed}，收到 {value!r}") from None


def _check_ratio(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} 必须是 [0.0, 1.0] 内的数值，收到 {value!r}")
    ratio = float(value)
    if not 0.0 <= ratio <= 1.0:
        raise ValueError(f"{field} 必须是 [0.0, 1.0] 内的数值，收到 {value!r}")
    return ratio


@dataclass
class Firmware:
    """待体检固件的身份信息。"""

    id: str
    vendor: str
    model: str
    version: str
    sha256: str
    source_url: str
    family: str | None = None


@dataclass
class Evidence:
    """一条可追溯到原文的取证结果。"""

    id: str
    firmware_id: str
    check_code: str
    level: EvidenceLevel
    confidence: float
    raw_ref: str
    detail: str = ""

    def __post_init__(self) -> None:
        self.level = _to_enum(self.level, EvidenceLevel, "Evidence.level")
        self.confidence = _check_ratio(self.confidence, "Evidence.confidence")


@dataclass
class Decision:
    """对单个固件的放行判定。"""

    firmware_id: str
    verdict: Verdict
    confidence: float
    reasons: list[str]
    evidence_ids: list[str]
    exposure: float | None = None

    def __post_init__(self) -> None:
        self.verdict = _to_enum(self.verdict, Verdict, "Decision.verdict")
        self.confidence = _check_ratio(self.confidence, "Decision.confidence")
        if self.exposure is not None:
            self.exposure = _check_ratio(self.exposure, "Decision.exposure")


@dataclass
class Policy:
    """随判定下发的放行策略。"""

    firmware_id: str
    granularity: Granularity
    rule_format: RuleFormat
    rules: list[str]
    asn_fallback: bool = False
    rollback_ref: str | None = None

    def __post_init__(self) -> None:
        self.granularity = _to_enum(self.granularity, Granularity, "Policy.granularity")
        self.rule_format = _to_enum(self.rule_format, RuleFormat, "Policy.rule_format")