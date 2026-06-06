import ast
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR     = _get_base_dir()
TEST_TIMEOUT = 30


@dataclass
class TestResult:
    passed:  bool
    message: str


def _syntax_check(file_path: Path) -> TestResult:
    try:
        ast.parse(file_path.read_text(encoding="utf-8"))
        return TestResult(True, f"Syntax OK: {file_path.name}")
    except SyntaxError as e:
        return TestResult(False, f"SyntaxError in {file_path.name} line {e.lineno}: {e.msg}")
    except Exception as e:
        return TestResult(False, f"Parse error in {file_path.name}: {e}")


def _import_check(module_dot: str) -> TestResult:
    cmd = [sys.executable, "-c", f"import {module_dot}; print('OK')"]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=TEST_TIMEOUT, cwd=str(BASE_DIR),
        )
        if r.returncode == 0 and "OK" in r.stdout:
            return TestResult(True, f"Import OK: {module_dot}")
        err = (r.stderr or r.stdout)[:300]
        return TestResult(False, f"Import failed {module_dot}: {err}")
    except subprocess.TimeoutExpired:
        return TestResult(False, f"Import timeout: {module_dot}")


def _core_load_check() -> TestResult:
    cmd = [sys.executable, "-c", "from viko.ui import VikoUI; print('OK')"]
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=TEST_TIMEOUT, cwd=str(BASE_DIR), env=env,
        )
        if r.returncode == 0:
            return TestResult(True, "Core load OK")
        return TestResult(False, f"Core load failed: {(r.stderr or r.stdout)[:300]}")
    except subprocess.TimeoutExpired:
        return TestResult(False, "Core load timeout")


def _path_to_module(rel_path: str) -> str:
    return rel_path.replace("\\", "/").replace("/", ".").removesuffix(".py")


def run(plan: dict, changes: list[dict]) -> TestResult:
    all_results: list[TestResult] = []

    for change in changes:
        rel   = change.get("file", "").replace("\\", "/")
        fpath = BASE_DIR / rel
        if not fpath.exists() or not rel.endswith(".py"):
            continue

        r = _syntax_check(fpath)
        all_results.append(r)
        if not r.passed:
            return r

        if rel.startswith("viko/") and "self_engineer" not in rel:
            module = _path_to_module(rel)
            r = _import_check(module)
            all_results.append(r)
            if not r.passed:
                return r

    modified_core = any(
        change.get("file", "") in ("viko.py", "viko/ui.py", "viko/ui_widgets.py")
        for change in changes
    )
    if modified_core:
        r = _core_load_check()
        all_results.append(r)
        if not r.passed:
            return r

    n = sum(1 for r in all_results if r.passed)
    return TestResult(True, f"Semua test lolos ({n} check{'s' if n != 1 else ''})")
