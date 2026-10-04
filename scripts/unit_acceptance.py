"""Run the test suite and preserve its actual log and machine-readable result."""
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]


if __name__ == "__main__":
    output = ROOT / "tmp/acceptance"
    output.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
    (output / "unit-tests.log").write_text(buffer.getvalue(), encoding="utf-8")
    (output / "unit-results.json").write_text(json.dumps({"success": result.wasSuccessful(),
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped)}, indent=2), encoding="utf-8")
    print(buffer.getvalue())
    raise SystemExit(0 if result.wasSuccessful() else 1)
