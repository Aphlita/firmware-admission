"""src.policy 的端点粒度、ACL/MUD 与 ASN 回退测试。"""

from __future__ import annotations

import json

import pytest

from src.policy import Endpoint, build_policy, choose_granularity, endpoints_from_evidence
from src.schema import Evidence, EvidenceLevel, Granularity, RuleFormat


def _egress(detail: str, suffix: str = "1") -> Evidence:
    return Evidence(
        id=f"E-EGRESS-{suffix}",
        firmware_id="FW-TEST",
        check_code="EGRESS_FIXED_CLOUD_ENDPOINT",
        level=EvidenceLevel.E3,
        confidence=0.4,
        raw_ref=f"etc/config:{suffix}",
        detail=detail,
    )


def test_endpoints_from_evidence_dedupes_hosts() -> None:
    evidence = [
        _egress("静态发现 https 外联地址 host=api.vendor.com；", "1"),
        _egress("静态发现 https 外联地址 host=api.vendor.com；", "2"),
        _egress("静态发现 http 外联地址 host=www.example.org；", "3"),
        Evidence(
            id="E-CRED-1",
            firmware_id="FW-TEST",
            check_code="CRED_DEFAULT_ADMIN_WEB",
            level=EvidenceLevel.E3,
            confidence=0.5,
            raw_ref="etc/passwd:1",
            detail="host=not-an-egress.example",
        ),
    ]

    endpoints = endpoints_from_evidence(evidence)

    assert [(item.host, item.port) for item in endpoints] == [
        ("api.vendor.com", 443),
        ("www.example.org", 80),
    ]
    assert endpoints[0].evidence_id == "E-EGRESS-1"


def test_choose_granularity_fqdn_vendor_asn() -> None:
    fqdn = [Endpoint("api.vendor.com"), Endpoint("www.other.com")]
    assert choose_granularity(fqdn) is Granularity.FQDN

    vendor_group = [Endpoint("a.tenda.com.cn"), Endpoint("b.tenda.com.cn")]
    assert (
        choose_granularity(vendor_group, vendor_map={"tenda.com.cn": "Tenda"})
        is Granularity.VENDOR_GROUP
    )

    assert choose_granularity([Endpoint("203.0.113.10")]) is Granularity.ASN
    assert choose_granularity([]) is Granularity.FQDN


def test_build_acl_fqdn_policy() -> None:
    policy = build_policy(
        "FW-TEST",
        [Endpoint("api.vendor.com"), Endpoint("www.other.com", scheme="http", port=80)],
        rollback_ref="rb-FW-TEST-1",
    )

    assert policy.granularity is Granularity.FQDN
    assert policy.rule_format is RuleFormat.ACL
    assert policy.asn_fallback is False
    assert policy.rollback_ref == "rb-FW-TEST-1"
    assert policy.rules == [
        "permit tcp any host api.vendor.com eq 443",
        "permit tcp any host www.other.com eq 80",
    ]


def test_build_vendor_group_policy() -> None:
    policy = build_policy(
        "FW-TEST",
        [Endpoint("a.tenda.com.cn", vendor="Tenda"), Endpoint("b.tenda.com.cn", vendor="Tenda")],
        granularity=Granularity.VENDOR_GROUP,
        rollback_ref="rb-FW-TEST-2",
    )

    assert policy.granularity is Granularity.VENDOR_GROUP
    assert policy.rules == ["permit tcp any vendor-group Tenda eq 443"]


def test_asn_fallback_is_explicit() -> None:
    policy = build_policy(
        "FW-TEST",
        [Endpoint("203.0.113.10")],
        rollback_ref="rb-FW-TEST-3",
    )

    assert policy.granularity is Granularity.ASN
    assert policy.asn_fallback is True
    assert "asn-fallback" in policy.rules[0]

    mapped = build_policy(
        "FW-TEST",
        [Endpoint("203.0.113.10")],
        rollback_ref="rb-FW-TEST-4",
        asn_map={"203.0.113.10": "64500"},
    )

    assert mapped.granularity is Granularity.ASN
    assert mapped.asn_fallback is True
    assert mapped.rules == ["permit tcp any asn 64500 eq 443"]


def test_mud_rules_are_json() -> None:
    policy = build_policy(
        "FW-TEST",
        [Endpoint("api.vendor.com")],
        rollback_ref="rb-FW-TEST-5",
        rule_format=RuleFormat.MUD,
    )

    assert policy.rule_format is RuleFormat.MUD
    payload = json.loads(policy.rules[0])
    assert payload["allow"]["host"] == "api.vendor.com"
    assert payload["allow"]["granularity"] == "fqdn"
    assert payload["allow"]["port"] == 443


def test_build_policy_requires_rollback_and_vendor() -> None:
    with pytest.raises(ValueError):
        build_policy("FW-TEST", [Endpoint("api.vendor.com")], rollback_ref="")
    with pytest.raises(ValueError):
        build_policy(
            "FW-TEST",
            [Endpoint("a.tenda.com.cn")],
            granularity=Granularity.VENDOR_GROUP,
            rollback_ref="rb-FW-TEST-6",
        )


def test_build_policy_empty_endpoints() -> None:
    policy = build_policy("FW-TEST", [], rollback_ref="rb-FW-TEST-7")

    assert policy.granularity is Granularity.FQDN
    assert policy.rules == []
    assert policy.asn_fallback is False
