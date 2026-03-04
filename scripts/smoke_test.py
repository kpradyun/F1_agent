"""Project smoke tests for fast local validation.

Run:
    python scripts/smoke_test.py
"""
from __future__ import annotations

import compileall
import importlib
import os
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MODULES = [
    "config.settings",
    "core.agent",
    "core.fastf1_adapter",
    "tools.analysis_tools",
    "tools.advanced_tools",
    "tools.reference_tools",
    "tools.live_tools",
    "rag_engine",
    "replay_ui",
]


def run_compileall() -> bool:
    print("[1/3] Compile check...")
    ok = compileall.compile_dir(".", quiet=1, maxlevels=10)
    print("  ->", "PASS" if ok else "FAIL")
    return ok


def run_import_checks() -> bool:
    print("[2/3] Import smoke checks...")
    failed: List[str] = []
    for mod in MODULES:
        try:
            importlib.import_module(mod)
            print(f"  [PASS] {mod}")
        except Exception as exc:
            failed.append(f"{mod}: {exc}")
            print(f"  [FAIL] {mod}: {exc}")
    if failed:
        print("\nImport failures:")
        for item in failed:
            print(" -", item)
    return len(failed) == 0


def run_config_checks() -> bool:
    print("[3/3] Config checks...")
    tavily = os.environ.get("TAVILY_API_KEY")
    if tavily:
        print("  [PASS] TAVILY_API_KEY is set")
    else:
        print("  [WARN] TAVILY_API_KEY not set (Tavily tool will return config warning)")
    return True


def main() -> int:
    compile_ok = run_compileall()
    import_ok = run_import_checks()
    config_ok = run_config_checks()

    if compile_ok and import_ok and config_ok:
        print("\nSmoke tests passed.")
        return 0

    print("\nSmoke tests failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
