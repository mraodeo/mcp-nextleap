"""
Stand-alone test runner using Python standard library (no external dependencies required).
Runs all tests in test_sanitizer.py and test_data_loader.py.
"""
import sys
import traceback
from pathlib import Path

# Add workspace root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import tests.test_sanitizer as t_san
import tests.test_data_loader as t_data
import tests.test_specialists as t_spec
import tests.test_reviewer as t_rev
import tests.test_graph as t_graph
import tests.test_mcp_tools as t_mcp
import tests.test_acceptance_suite as t_acc
import tests.test_web_server as t_web

def run_all():
    test_modules = [
        ("test_sanitizer", t_san),
        ("test_data_loader", t_data),
        ("test_specialists", t_spec),
        ("test_reviewer", t_rev),
        ("test_graph", t_graph),
        ("test_mcp_tools", t_mcp),
        ("test_acceptance_suite", t_acc),
        ("test_web_server", t_web)
    ]

    total = 0
    passed = 0
    failed = 0

    print("=" * 70)
    print("RUNNING MULTI-AGENT UNIT TESTS (Built-in Runner)")
    print("=" * 70)

    for mod_name, mod in test_modules:
        print(f"\n--- Module: {mod_name} ---")
        for attr in dir(mod):
            if attr.startswith("test_") and callable(getattr(mod, attr)):
                total += 1
                func = getattr(mod, attr)
                try:
                    func()
                    print(f"  [PASS] {attr}")
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {attr}")
                    traceback.print_exc()
                    failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: Total: {total} | Passed: {passed} | Failed: {failed}")
    print("=" * 70)
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_all()
