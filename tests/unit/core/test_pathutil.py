"""core.pathutil 测试：三平台表驱动归一、边界拒绝、无文件系统 IO。"""

from __future__ import annotations

from pathlib import Path

import pytest

from aftermatter.core.errors import ContractViolation, PathOutsideWorkspace
from aftermatter.core.pathutil import norm_path

# (root, p, 期望的仓库相对 posix 路径)
NORMAL_CASES: list[tuple[str, str, str]] = [
    ("/repo", "/repo/src/a.py", "src/a.py"),
    ("/repo/", "/repo/src/a.py", "src/a.py"),
    ("/repo", "/repo", "."),
    ("/repo", "/repo/.", "."),
    ("/repo", "src/a.py", "src/a.py"),
    ("/repo", "src/old/../b.py", "src/b.py"),
    ("/repo", "src/../b.py", "b.py"),
    ("/repo", "/repo/sub/../b.py", "b.py"),
    ("/repo", "/repo/a/../b.py", "b.py"),
    ("/repo", "/repo/definitely/not/on/disk/x.py", "definitely/not/on/disk/x.py"),
    ("/", "/a/b.py", "a/b.py"),
    ("/repo", "/repo\\src\\a.py", "src/a.py"),
    ("C:/repo", "C:\\repo\\src\\a.py", "src/a.py"),
    ("C:/repo", "C:/repo/src/a.py", "src/a.py"),
    ("C:/Repo", "c:/repo", "."),
    ("C:/repo", "src\\sub\\a.py", "src/sub/a.py"),
    ("C:/repo", "C:\\repo\\A.B\\c.py", "A.B/c.py"),
    ("\\\\server\\share\\repo", "\\\\SERVER\\Share\\repo\\src\\a.py", "src/a.py"),
]


@pytest.mark.parametrize(("root", "p", "expected"), NORMAL_CASES)
def test_norm_path_tables(root: str, p: str, expected: str) -> None:
    assert norm_path(p, root) == expected


def test_output_is_always_posix_relative() -> None:
    result = norm_path("C:\\repo\\src\\a.py", "C:/repo")
    assert "\\" not in result and ":" not in result and not result.startswith("/")


def test_posix_segments_stay_case_sensitive() -> None:
    with pytest.raises(PathOutsideWorkspace):
        norm_path("/Repo/src/a.py", "/repo")


def test_windows_segments_are_case_insensitive_but_preserved() -> None:
    assert norm_path("C:/REPO/Src/A.py", "C:/repo") == "Src/A.py"


@pytest.mark.parametrize("p", ["/etc/passwd", "/repo-evil/a.py", "../outside/x", "C:/other/x"])
def test_rejects_similar_looking_prefixes(p: str) -> None:
    with pytest.raises(PathOutsideWorkspace) as caught:
        norm_path(p, "/repo")
    assert caught.value.code == "path_outside_root"
    assert "repo" not in str(caught.value), "异常文本不得携带真实路径"


def test_rejects_different_drive_and_style_mismatch() -> None:
    with pytest.raises(PathOutsideWorkspace):
        norm_path("D:/repo/x", "C:/repo")
    with pytest.raises(PathOutsideWorkspace):
        norm_path("/Users/dev/x", "C:/Users/dev")


def test_escapes_above_root_are_rejected() -> None:
    with pytest.raises(PathOutsideWorkspace):
        norm_path("/repo/../../repo/x", "/repo")


@pytest.mark.parametrize("root", ["", "repo/src", "src/a.py"])
def test_root_must_be_absolute(root: str) -> None:
    with pytest.raises(ContractViolation) as caught:
        norm_path("/repo/x", root)
    assert caught.value.code == "path_root_not_absolute"


def test_malformed_unc_root_is_rejected() -> None:
    with pytest.raises(ContractViolation) as caught:
        norm_path("/repo/x", "\\\\server")
    assert caught.value.code == "path_malformed_unc"


def test_empty_path_is_rejected() -> None:
    with pytest.raises(ContractViolation) as caught:
        norm_path("", "/repo")
    assert caught.value.code == "path_empty"


def test_accepts_path_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/home/dev")
    assert norm_path(Path("/repo/src/a.py"), Path("/repo")) == "src/a.py"


def test_expand_user_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/home/dev")
    assert norm_path("~/code/a.py", "/home/dev") == "code/a.py"
    assert norm_path("~", "/home/dev") == "."


def test_expand_user_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USERPROFILE", "C:\\Users\\dev")
    assert norm_path("~\\code\\a.py", "C:/Users/dev") == "code/a.py"


def test_missing_home_env_is_contract_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOME", raising=False)
    with pytest.raises(ContractViolation) as caught:
        norm_path("~/code/a.py", "/home/dev")
    assert caught.value.code == "path_home_unknown"


def test_home_outside_repo_is_outside_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/home/dev")
    with pytest.raises(PathOutsideWorkspace):
        norm_path("~/other/a.py", "/repo")
