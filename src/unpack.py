"""固件解包封装：调用 binwalk 把固件映像解包为文件系统，并返回结构化结果。

判定顺序固定为 not_found → binwalk_missing → timeout → invalid_image → extract_failed → ok，
`unpack_firmware` 对任何输入都不向调用方抛异常。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

Runner = Callable[[list[str], int], tuple[int, str, str]]

_BINWALK_TIMEOUT_EXIT_CODE = 124
_FILESYSTEM_ROOTS = ("squashfs-root", "jffs2-root", "cramfs-root", "rootfs")

_ROW_RE = re.compile(r"^\s*\d+\s+0x[0-9A-Fa-f]+\s+(?P<description>\S.*)$")


def _build_signatures() -> tuple[tuple[re.Pattern[str], str], ...]:
    """把关键词编译成带词边界的正则：避免 "elf" 命中 "self" 这类普通英文词。"""
    keywords = (
        ("trx", "TRX"),
        ("uimage", "uImage"),
        ("lzma", "LZMA"),
        ("squashfs", "squashfs"),
        ("cramfs", "cramfs"),
        ("jffs2", "jffs2"),
        ("gzip", "gzip"),
        ("bzip2", "bzip2"),
        ("cpio", "cpio"),
        ("tar archive", "tar"),
        ("zip archive", "zip"),
        ("ubi", "UBI"),
        ("android bootimg", "bootimg"),
        ("flattened device tree", "dtb"),
        ("yaffs", "yaffs2"),
        ("elf", "ELF"),
    )
    return tuple(
        (re.compile(rf"(?<![0-9a-z]){keyword}(?![0-9a-z])"), name)
        for keyword, name in keywords
    )


_SIGNATURES = _build_signatures()


@dataclass
class UnpackResult:
    ok: bool
    image_path: str
    extract_dir: str | None = None
    filesystem_paths: list[str] = field(default_factory=list)
    file_count: int = 0
    components: list[str] = field(default_factory=list)
    error: str | None = None
    error_kind: str | None = None


def parse_signatures(binwalk_stdout: str) -> list[str]:
    """从 binwalk 签名行提取组件名，去重并保留首次出现顺序。"""
    components: list[str] = []
    for line in binwalk_stdout.splitlines():
        row = _ROW_RE.match(line)
        if row is None:
            continue
        description = row.group("description").lower()
        for pattern, name in _SIGNATURES:
            if name not in components and pattern.search(description):
                components.append(name)
                break
    return components


def _is_filesystem_root(name: str) -> bool:
    return any(name == root or name.startswith(f"{root}-") for root in _FILESYSTEM_ROOTS)


def collect_filesystems(extract_dir: Path) -> list[str]:
    """返回解包目录下所有文件系统根目录的绝对路径字符串，按字典序排序。"""
    root = Path(extract_dir)
    if not root.is_dir():
        return []
    root = root.resolve()
    roots = {
        str(path)
        for path in root.rglob("*")
        if path.is_dir() and _is_filesystem_root(path.name)
    }
    return sorted(roots)


def _count_files(filesystem_paths: list[str]) -> int:
    files = {
        child
        for path in filesystem_paths
        for child in Path(path).rglob("*")
        if child.is_file()
    }
    return len(files)


def _default_runner(argv: list[str], timeout: int) -> tuple[int, str, str]:
    completed = subprocess.run(
        argv,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _failure(image: Path, extract_dir: Path, error: str, error_kind: str) -> UnpackResult:
    return UnpackResult(
        ok=False,
        image_path=str(image),
        extract_dir=str(extract_dir),
        error=error,
        error_kind=error_kind,
    )


def unpack_firmware(
    image_path: str | Path,
    workdir: str | Path | None = None,
    timeout: int = 300,
    runner: Runner | None = None,
) -> UnpackResult:
    image = Path(image_path)
    if not image.exists():
        return UnpackResult(
            ok=False,
            image_path=str(image),
            error=f"固件映像不存在: {image}",
            error_kind="not_found",
        )

    base = Path(workdir) if workdir is not None else image.parent
    extract_dir = (base / f"_{image.stem}.extracted").resolve()
    # 幂等：同一 workdir 重复执行时先清掉上次的解包目录。
    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)

    run = runner if runner is not None else _default_runner
    argv = ["binwalk", "--extract"]
    # binwalk 以 root 运行时，extractor 模块要求显式指定提取用户，否则拒绝加载。
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        argv.append("--run-as=root")
    argv += ["--directory", str(extract_dir), str(image)]
    try:
        exit_code, stdout, stderr = run(argv, timeout)
    except subprocess.TimeoutExpired:
        return _failure(image, extract_dir, f"binwalk 超时（{timeout}s）", "timeout")
    except (FileNotFoundError, PermissionError) as exc:
        return _failure(image, extract_dir, f"binwalk 不可用: {exc}", "binwalk_missing")
    except Exception as exc:  # 契约要求永不抛异常，未知 runner 故障归为解包失败
        return _failure(image, extract_dir, f"binwalk 调用失败: {exc}", "extract_failed")

    if exit_code == _BINWALK_TIMEOUT_EXIT_CODE:
        return _failure(image, extract_dir, f"binwalk 超时（{timeout}s）", "timeout")

    # binwalk 自身失败（参数/权限/extractor 加载）属工具故障，不能报成“固件损坏”。
    if exit_code != 0:
        detail = (stderr.strip() or f"binwalk 退出码 {exit_code}")[:400]
        return _failure(image, extract_dir, f"binwalk 执行失败: {detail}", "extract_failed")

    components = parse_signatures(stdout)
    if not components:
        detail = stderr.strip() or "binwalk 未输出签名行"
        return _failure(image, extract_dir, f"未识别出固件签名: {detail}", "invalid_image")

    try:
        filesystem_paths = collect_filesystems(extract_dir)
    except OSError as exc:
        return _failure(image, extract_dir, f"扫描解包目录失败: {exc}", "extract_failed")

    if not filesystem_paths:
        return UnpackResult(
            ok=False,
            image_path=str(image),
            extract_dir=str(extract_dir),
            components=components,
            error="解包未产出文件系统",
            error_kind="extract_failed",
        )

    return UnpackResult(
        ok=True,
        image_path=str(image),
        extract_dir=str(extract_dir),
        filesystem_paths=filesystem_paths,
        file_count=_count_files(filesystem_paths),
        components=components,
    )


def main(argv: list[str] | None = None) -> int:
    """把 UnpackResult 以 JSON 打到 stdout；0 表示解包成功，1 表示失败，2 表示用法错误。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("用法: python -m src.unpack <image>", file=sys.stderr)
        return 2
    result = unpack_firmware(args[0])
    print(json.dumps(asdict(result), ensure_ascii=False))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())