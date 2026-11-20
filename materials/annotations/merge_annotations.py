#!/usr/bin/env python3
"""把 A/B 两份独立标注合并成 src.metrics 可读的文件。

用法（在项目根目录）：
    python materials/annotations/merge_annotations.py ^
      materials/annotations/annotator_A.json ^
      materials/annotations/annotator_B.json ^
      materials/annotations/annotation_combined.json

只合并 annotators；decisions/policy_replay/policies 置空，避免把未验证数据带进指标。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: 根节点必须是对象")
    return data


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "用法: python materials/annotations/merge_annotations.py "
            "annotator_A.json annotator_B.json annotation_combined.json",
            file=sys.stderr,
        )
        return 2
    a, b, out = argv[1], argv[2], argv[3]
    merged: dict[str, dict] = {}
    for path in (a, b):
        data = load(path)
        annotators = data.get("annotators", {})
        if not isinstance(annotators, dict) or not annotators:
            raise ValueError(f"{path}: 缺少非空 annotators")
        for name, labels in annotators.items():
            if name in merged:
                raise ValueError(f"重复标注者: {name}")
            merged[name] = labels
    if set(merged) != {"A", "B"}:
        raise ValueError(f"合并后应只有 A/B，实际: {sorted(merged)}")
    payload = {
        "annotators": {"A": merged["A"], "B": merged["B"]},
        "decisions": [],
        "policy_replay": [],
        "policies": [],
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已合并 -> {out}")
    print("下一步: python -m src.metrics " + out + " --output materials/metrics_12.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
