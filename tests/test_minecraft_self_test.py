"""
Unit Test Suite for REN-AI Minecraft In-Game Self-Test Diagnostic Engine
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ren.minecraft.self_test import MinecraftSelfTestRunner


def test_self_test_runner():
    print("\n" + "=" * 64)
    print(" [*] RUNNING MINECRAFT SELF-TEST RUNNER VERIFICATION")
    print("=" * 64)

    runner = MinecraftSelfTestRunner()
    all_passed, results, report = runner.run_all_self_tests()

    print(f"\n{report}\n")
    assert all_passed is True, f"Expected all self tests to pass, got failures in: {[r.test_name for r in results if not r.passed]}"
    assert len(results) == 10, f"Expected 10 test results, got {len(results)}"
    print("  [PASS] All 10 self-diagnostic subsystems verified.")

    print("\n" + "=" * 64)
    print(" [PASS] ALL SELF-TEST RUNNER TESTS PASSED (100%)")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    test_self_test_runner()
