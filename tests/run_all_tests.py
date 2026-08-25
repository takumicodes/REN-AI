"""
Master Test Runner for REN-AI
Discovers and executes all unit and integration test suites.
"""

import sys
import time
import subprocess
import unittest
from pathlib import Path

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def main():
    print("\n" + "=" * 68)
    print(" [*] REN-AI COMPREHENSIVE MASTER TEST SUITE RUNNER")
    print("=" * 68)

    tests_dir = Path(__file__).parent
    mc_tests = sorted(list(tests_dir.glob("test_minecraft_*.py")))

    total_passed = 0
    total_failed = 0
    results = []

    # 1. Run all Minecraft Embodied test suites
    for test_file in mc_tests:
        t0 = time.time()
        res = subprocess.run([sys.executable, str(test_file)], cwd=str(root_dir), capture_output=True, text=True, errors="replace")
        dur = (time.time() - t0) * 1000
        passed = res.returncode == 0
        if passed:
            total_passed += 1
            results.append((test_file.name, True, f"{dur:.1f}ms"))
        else:
            total_failed += 1
            err_snip = res.stderr.strip() or res.stdout.strip()
            results.append((test_file.name, False, err_snip[:120]))

    # 2. Run standard unittest discovery
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(tests_dir), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=1)
    unit_res = runner.run(suite)

    print("\n" + "=" * 68)
    print(" [*] EMBODIED MINECRAFT TEST RESULTS SUMMARY")
    print("=" * 68)
    for name, ok, note in results:
        status = "[PASS]" if ok else "[FAIL]"
        print(f" {status:<6} | {name:<36} | {note}")
    print("=" * 68)
    print(f" OVERALL: {'100% PASSED' if total_failed == 0 and unit_res.wasSuccessful() else 'FAILURES DETECTED'}")
    print(f" Embodied Tests: {total_passed} Passed / {len(mc_tests)} Total | Unittest Errors: {len(unit_res.errors)}, Failures: {len(unit_res.failures)}")
    print("=" * 68 + "\n")

    sys.exit(0 if total_failed == 0 and unit_res.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
