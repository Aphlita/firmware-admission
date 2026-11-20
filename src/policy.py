"""端点粒度选择与 ACL/MUD 策略合成（T2-2）。

输入是已识别的端点（来自 `src.evidence` 的出向外联证据），输出 `Policy`：
- 粒度：FQDN / vendor-group / ASN；
- 载体：ACL 行 或 MUD JSON 行；
- 回滚引用：必填，由调用方生成；
- ASN 回退：只要最终粒度是 ASN，`Policy.asn_fallback` 必为 True，规则文本也带
  ``asn-fallback`` 标注，禁止静默回退。
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from src.schema import Evidence, Granularity, Policy, RuleFormat

__all__ = [
    "Endpoint",
    "build_policy",
    "choose_granularity",
    "endpoints_from_evidence",
    "main",
]

_HOST_RE = re.compile(r"host=([A-Za-z0-9_.:-]+)")
_SCHEME_RE = re.compile(r"\b(https?)://")
_SCHEME_TEXT_RE = re.compile(r"\b(https?)\s+外联地址")
_DOMAIN_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


@dataclass(frozen=True)
class Endpoint:
    """一个待放行的出向端点。"""

    host: str
    port: int = 443
    scheme: str = "https"
    evidence_id: str = ""
    vendor: str | None = None
    asn: str | None = None

    def __post_init__(self) -> None:
        if not self.host or not self.host.strip():
            raise ValueError("Endpoint.host 不能为空")
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Endpoint.port 必须在 1..65535，收到 {self.port}")
        scheme = self.scheme.lower()
        if scheme not in {"http", "https"}:
            raise ValueError(f"Endpoint.scheme 只接受 http/https，收到 {self.scheme!r}")
        object.__setattr__(self, "host", self.host.strip().lower().rstrip("."))
        object.__setattr__(self, "scheme", scheme)


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _is_domain(host: str) -> bool:
    if _is_ip(host) or "." not in host:
        return False
    return all(_DOMAIN_LABEL_RE.match(label) for label in host.split("."))


def _vendor_for(endpoint: Endpoint, vendor_map: Mapping[str, str] | None) -> str | None:
    if endpoint.vendor:
        return endpoint.vendor
    for suffix, vendor in (vendor_map or {}).items():
        if endpoint.host == suffix or endpoint.host.endswith("." + suffix):
            return vendor
    return None


def _asn_for(endpoint: Endpoint, asn_map: Mapping[str, str] | None) -> str | None:
    return endpoint.asn or (asn_map or {}).get(endpoint.host)


def _normalize_endpoints(
    endpoints: Iterable[Endpoint],
    vendor_map: Mapping[str, str] | None,
    asn_map: Mapping[str, str] | None,
) -> list[Endpoint]:
    unique: dict[tuple[str, int, str], Endpoint] = {}
    for endpoint in endpoints:
        vendor = _vendor_for(endpoint, vendor_map)
        asn = _asn_for(endpoint, asn_map)
        normalized = Endpoint(
            host=endpoint.host,
            port=endpoint.port,
            scheme=endpoint.scheme,
            evidence_id=endpoint.evidence_id,
            vendor=vendor,
            asn=asn,
        )
        unique[(normalized.host, normalized.port, normalized.scheme)] = normalized
    return sorted(unique.values(), key=lambda item: (item.host, item.port, item.scheme))


def choose_granularity(
    endpoints: Sequence[Endpoint],
    *,
    vendor_map: Mapping[str, str] | None = None,
) -> Granularity:
    """按“域名可定位 → 厂商可归组 → ASN 回退”的顺序选粒度。"""
    if not endpoints:
        return Granularity.FQDN
    if any(not _is_domain(endpoint.host) for endpoint in endpoints):
        return Granularity.ASN
    vendors = {_vendor_for(endpoint, vendor_map) for endpoint in endpoints}
    if None not in vendors and len(vendors) < len(endpoints):
        return Granularity.VENDOR_GROUP
    return Granularity.FQDN


def _as_granularity(value: Granularity | str) -> Granularity:
    return value if isinstance(value, Granularity) else Granularity(value)


def _as_rule_format(value: RuleFormat | str) -> RuleFormat:
    return value if isinstance(value, RuleFormat) else RuleFormat(value)


def _acl_rules(endpoints: Sequence[Endpoint], granularity: Granularity) -> list[str]:
    rules: set[str] = set()
    if granularity is Granularity.FQDN:
        for endpoint in endpoints:
            rules.add(f"permit tcp any host {endpoint.host} eq {endpoint.port}")
    elif granularity is Granularity.VENDOR_GROUP:
        for endpoint in endpoints:
            if not endpoint.vendor:
                raise ValueError(f"vendor-group 缺少 vendor: {endpoint.host}")
            rules.add(f"permit tcp any vendor-group {endpoint.vendor} eq {endpoint.port}")
    else:
        for endpoint in endpoints:
            if endpoint.asn:
                rules.add(f"permit tcp any asn {endpoint.asn} eq {endpoint.port}")
            else:
                rules.add(
                    f"permit tcp any host {endpoint.host} eq {endpoint.port}  "
                    "# asn-fallback: no ASN mapping"
                )
    return sorted(rules)


def _mud_rules(endpoints: Sequence[Endpoint], granularity: Granularity) -> list[str]:
    rules: list[str] = []
    for endpoint in endpoints:
        entry: dict[str, object] = {
            "granularity": granularity.value,
            "port": endpoint.port,
            "scheme": endpoint.scheme,
        }
        if granularity is Granularity.FQDN:
            entry["host"] = endpoint.host
        elif granularity is Granularity.VENDOR_GROUP:
            if not endpoint.vendor:
                raise ValueError(f"vendor-group 缺少 vendor: {endpoint.host}")
            entry["vendor"] = endpoint.vendor
        elif endpoint.asn:
            entry["asn"] = endpoint.asn
        else:
            entry["host"] = endpoint.host
            entry["asn_fallback"] = True
        rules.append(json.dumps({"allow": entry}, ensure_ascii=False, sort_keys=True))
    return sorted(rules)


def build_policy(
    firmware_id: str,
    endpoints: Iterable[Endpoint],
    *,
    rollback_ref: str,
    granularity: Granularity | str | None = None,
    rule_format: RuleFormat | str = RuleFormat.ACL,
    vendor_map: Mapping[str, str] | None = None,
    asn_map: Mapping[str, str] | None = None,
) -> Policy:
    """由端点合成最小权限策略；ASN 粒度必须显式标注 ``asn_fallback``。"""
    if not firmware_id or not firmware_id.strip():
        raise ValueError("firmware_id 不能为空")
    if not rollback_ref or not rollback_ref.strip():
        raise ValueError("rollback_ref 必填（configs/baseline.yaml policy.require_rollback_ref）")

    normalized = _normalize_endpoints(endpoints, vendor_map, asn_map)
    selected = _as_granularity(granularity) if granularity is not None else choose_granularity(
        normalized, vendor_map=vendor_map
    )
    selected_format = _as_rule_format(rule_format)
    if selected_format is RuleFormat.ACL:
        rules = _acl_rules(normalized, selected)
    else:
        rules = _mud_rules(normalized, selected)
    return Policy(
        firmware_id=firmware_id,
        granularity=selected,
        rule_format=selected_format,
        rules=rules,
        asn_fallback=selected is Granularity.ASN,
        rollback_ref=rollback_ref,
    )


def endpoints_from_evidence(evidence: Sequence[Evidence]) -> list[Endpoint]:
    """从出向外联证据的 detail 中提取 host，供策略合成使用。"""
    found: dict[tuple[str, int, str], Endpoint] = {}
    for item in evidence:
        if not item.check_code.startswith("EGRESS_"):
            continue
        host_match = _HOST_RE.search(item.detail)
        if host_match is None:
            continue
        scheme_match = _SCHEME_RE.search(item.detail) or _SCHEME_TEXT_RE.search(item.detail)
        scheme = scheme_match.group(1).lower() if scheme_match else "https"
        port = 443 if scheme == "https" else 80
        endpoint = Endpoint(
            host=host_match.group(1).rstrip(".,;"),
            port=port,
            scheme=scheme,
            evidence_id=item.id,
        )
        found.setdefault((endpoint.host, endpoint.port, endpoint.scheme), endpoint)
    return sorted(found.values(), key=lambda item: (item.host, item.port, item.scheme))


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
    """CLI：evidence JSON → 端点 → ACL/MUD 策略。"""
    parser = argparse.ArgumentParser(description="端点粒度与 ACL/MUD 策略（T2-2）")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--firmware-id", required=True)
    parser.add_argument("--rollback-ref", default=None)
    parser.add_argument("--granularity", choices=("fqdn", "vendor-group", "asn"), default=None)
    parser.add_argument("--rule-format", choices=("acl", "mud"), default="acl")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)

    try:
        evidence = _load_evidence(args.evidence)
        endpoints = endpoints_from_evidence(evidence)
        policy = build_policy(
            args.firmware_id,
            endpoints,
            rollback_ref=args.rollback_ref or f"rb-{args.firmware_id}",
            granularity=args.granularity,
            rule_format=args.rule_format,
        )
    except (OSError, KeyError, ValueError) as exc:
        print(f"策略生成失败: {exc}", file=sys.stderr)
        return 2

    payload = {
        "firmware_id": policy.firmware_id,
        "granularity": policy.granularity.value,
        "rule_format": policy.rule_format.value,
        "rule_count": len(policy.rules),
        "asn_fallback": policy.asn_fallback,
        "rollback_ref": policy.rollback_ref,
        "rules": list(policy.rules),
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
