"""Verify the optional Python lane using real exported data and syntax errors."""
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.problems import load_problems
from backend.judge import Judge

if __name__ == "__main__":
    output = ROOT / "tmp/acceptance"
    problems, _ = load_problems(ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest")
    judge = Judge(problems, output / "python-judge")
    result = judge.evaluate("L", (problems["L"].root / "src/solution.py").read_text(encoding="utf-8-sig"), "python", "L-python")
    syntax = judge.evaluate("L", "def broken(:\n", "python", "python-syntax")
    success = result.verdict == "AC" and result.checked == 38 and syntax.verdict == "CE"
    report = {"success": success, "main": asdict(result), "syntax": asdict(syntax)}
    (output / "python-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if success else 1)
