#!/usr/bin/env python3
"""检查 A/B 标注是否可合并；不计算指标。

用法（在项目根目录）：
    python materials/annotations/check_annotations.py ^
      materials/annotations/annotator_A.json ^
      materials/annotations/annotator_B.json

退出码：0 = 可合并；1 = 有 TODO/缺项/非法状态；2 = 用法错误。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VALID = {"found", "clear", "not_tested"}


def load_labels(path: str) -> dict[str, dict[str, str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    annotators = data.get("annotators")
    if not isinstance(annotators, dict) or len(annotators) != 1:
        raise ValueError(f"{path}: 需要恰好一个 annotators 子项")
    return next(iter(annotators.values()))


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("用法: python .../check_annotations.py annotator_A.json annotator_B.json", file=sys.stderr)
        return 2
    try:
        a = load_labels(argv[1])
        b = load_labels(argv[2])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"读取失败: {exc}", file=sys.stderr)
        return 1

    problems = 0
    keys_a = {(f, c) for f, checks in a.items() for c in checks}
    keys_b = {(f, c) for f, checks in b.items() for c in checks}
    if keys_a != keys_b:
        print(f"键集合不一致: A 独有 {sorted(keys_a - keys_b)}; B 独有 {sorted(keys_b - keys_a)}")
        problems += 1

    todo = 0
    for name, labels in (("A", a), ("B", b)):
        for fid, checks in labels.items():
            for code, status in checks.items():
                if status == "TODO":
                    todo += 1
                elif status not in VALID:
                    print(f"{name}/{fid}/{code}: 非法状态 {status!r}")
                    problems += 1
    if todo:
        print(f"仍有 TODO: {todo} 个（必须全部替换）")
        problems += 1

    disagreements = []
    for key in sorted(keys_a & keys_b):
        if a[key[0]][key[1]] != b[key[0]][key[1]]:
            disagreements.append((key[0], key[1], a[key[0]][key[1]], b[key[0]][key[1]]))

    print(f"固件数: {len({f for f, _ in keys_a})}；检查项/固件: {len(keys_a) // max(len({f for f, _ in keys_a}), 1)}")
    print(f"A/B 不一致: {len(disagreements)} 个")
    for fid, code, av, bv in disagreements:
        print(f"  {fid} {code}: A={av} B={bv}")
    if problems == 0:
        print("CHECK_OK：可以合并并计算指标")
        return 0
    print("CHECK_FAILED：先修上面的问题")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
