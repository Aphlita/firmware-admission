"""src.unpack 的判定顺序、结构化结果与 CLI 输出测试。

全部路径注入 fake runner，不调用真实 binwalk。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import src.unpack as unpack_module
from src.unpack import (
    Runner,
    UnpackResult,
    collect_filesystems,
    parse_signatures,
    unpack_firmware,
)

SAMPLE_STDOUT = (
    "DECIMAL       HEXADECIMAL     DESCRIPTION\n"
    "------------------------------------------------------------\n"
    "0             0x0             TRX firmware header, little endian, image size: 1048576 bytes\n"
    "28            0x1C            LZMA compressed data, properties: 0x5D, dictionary size: 8388608 bytes\n"
    "1310720       0x140000        SquashFS filesystem, little endian, version 4.0, size: 5001216 bytes\n"
    "1310720       0x140000        SquashFS filesystem, little endian, version 4.0, size: 5001216 bytes\n"
)

GARBAGE_STDOUT = (
    "DECIMAL       HEXADECIMAL     DESCRIPTION\n"
    "------------------------------------------------------------\n"
)


def _extract_dir_of(argv: list[str]) -> Path:
    return Path(argv[argv.index("--directory") + 1])


def _fake_runner(
    extract_files: dict[str, int] | None = None,
    *,
    stdout: str = SAMPLE_STDOUT,
    exit_code: int = 0,
) -> Runner:
    def runner(argv: list[str], timeout: int) -> tuple[int, str, str]:
        if extract_files is not None:
            root = _extract_dir_of(argv)
            for relative, size in extract_files.items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"x" * size)
        return exit_code, stdout, ""

    return runner


def test_unpack_success_returns_filesystems_and_components(tmp_path: Path) -> None:
    image = tmp_path / "fw.bin"
    image.write_bytes(b"firmware")
    extract_dir = tmp_path / "work" / "_fw.extracted"
    stale = extract_dir / "stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")

    result = unpack_firmware(
        image,
        workdir=tmp_path / "work",
        runner=_fake_runner(
            {
                "squashfs-root/bin/busybox": 10,
                "squashfs-root/etc/passwd": 5,
            }
        ),
    )

    assert result.ok is True
    assert result.error is None
    assert result.error_kind is None
    assert Path(str(result.extract_dir)) == extract_dir.resolve()
    assert [Path(path) for path in result.filesystem_paths] == [
        extract_dir.resolve() / "squashfs-root"
    ]
    assert result.file_count == 2
    assert result.components == ["TRX", "LZMA", "squashfs"]
    assert not stale.exists()


def test_unpack_reports_invalid_image_for_unrecognized_data(tmp_path: Path) -> None:
    image = tmp_path / "fw.bin"
    image.write_bytes(b"garbage")

    result = unpack_firmware(image, workdir=tmp_path, runner=_fake_runner(stdout=GARBAGE_STDOUT))

    assert result.ok is False
    assert result.error_kind == "invalid_image"
    assert result.components == []
    assert result.filesystem_paths == []
    assert result.file_count == 0


def test_unpack_missing_image_skips_runner(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str], timeout: int) -> tuple[int, str, str]:
        calls.append(argv)
        return 0, SAMPLE_STDOUT, ""

    result = unpack_firmware(tmp_path / "absent.bin", workdir=tmp_path, runner=runner)

    assert result.ok is False
    assert result.error_kind == "not_found"
    assert result.extract_dir is None
    assert calls == []


@pytest.mark.parametrize("exception", [FileNotFoundError("binwalk"), PermissionError("binwalk")])
def test_unpack_reports_binwalk_missing(tmp_path: Path, exception: Exception) -> None:
    image = tmp_path / "fw.bin"
    image.write_bytes(b"firmware")

    def runner(argv: list[str], timeout: int) -> tuple[int, str, str]:
        raise exception

    result = unpack_firmware(image, workdir=tmp_path, runner=runner)

    assert result.ok is False
    assert result.error_kind == "binwalk_missing"


@pytest.mark.parametrize("mode", ["raise", "exit_code"])
def test_unpack_reports_timeout(tmp_path: Path, mode: str) -> None:
    image = tmp_path / "fw.bin"
    image.write_bytes(b"firmware")

    def runner(argv: list[str], timeout: int) -> tuple[int, str, str]:
        if mode == "raise":
            raise subprocess.TimeoutExpired(cmd=argv[0], timeout=timeout)
        return 124, "", ""

    result = unpack_firmware(image, workdir=tmp_path, runner=runner)

    assert result.ok is False
    assert result.error_kind == "timeout"


def test_unpack_reports_extract_failed_but_keeps_components(tmp_path: Path) -> None:
    image = tmp_path / "fw.bin"
    image.write_bytes(b"firmware")

    result = unpack_firmware(image, workdir=tmp_path, runner=_fake_runner())

    assert result.ok is False
    assert result.error_kind == "extract_failed"
    assert result.components == ["TRX", "LZMA", "squashfs"]
    assert result.filesystem_paths == []


def test_parse_signatures_deduplicates_in_order() -> None:
    assert parse_signatures(SAMPLE_STDOUT) == ["TRX", "LZMA", "squashfs"]
    assert parse_signatures(GARBAGE_STDOUT) == []
    assert parse_signatures("") == []


def test_collect_filesystems_sorted_roots(tmp_path: Path) -> None:
    for relative in (
        "rootfs/etc/passwd",
        "jffs2-root/bin/sh",
        "squashfs-root-0/lib/libc.so",
        "other/x",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")

    found = collect_filesystems(tmp_path)

    assert [Path(path).name for path in found] == ["jffs2-root", "rootfs", "squashfs-root-0"]
    assert all(Path(path).is_absolute() for path in found)
    assert collect_filesystems(tmp_path / "absent") == []


def test_main_prints_json_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    result = UnpackResult(
        ok=True,
        image_path=str(tmp_path / "fw.bin"),
        extract_dir=str(tmp_path / "_fw.extracted"),
        filesystem_paths=[str(tmp_path / "_fw.extracted" / "squashfs-root")],
        file_count=3,
        components=["TRX", "squashfs"],
    )
    monkeypatch.setattr(unpack_module, "unpack_firmware", lambda *args, **kwargs: result)

    assert unpack_module.main([str(tmp_path / "fw.bin")]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["components"] == ["TRX", "squashfs"]
    assert payload["file_count"] == 3


def test_main_returns_failure_and_usage_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    failed = UnpackResult(
        ok=False,
        image_path=str(tmp_path / "fw.bin"),
        error="未识别出固件签名",
        error_kind="invalid_image",
    )
    monkeypatch.setattr(unpack_module, "unpack_firmware", lambda *args, **kwargs: failed)

    assert unpack_module.main([str(tmp_path / "fw.bin")]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_kind"] == "invalid_image"

    assert unpack_module.main([]) == 2
    assert "用法" in capsys.readouterr().err