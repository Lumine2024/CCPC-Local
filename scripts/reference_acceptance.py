"""Cross-check independent references only on their configured case scopes."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.problems import load_problems
from backend.judge import Judge


def main():
    output = ROOT / "tmp/acceptance"
    problems, _ = load_problems(ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest")
    report = {"success": False, "results": []}
    failed = False
    for pid, p in problems.items():
        reference = next(s for s in p.config["solutions"] if s["role"] == "reference" and s["language"] == "cpp")
        generation = {c["name"]: c for c in p.config["generator"]["cases"]}
        cases = [c for c in p.cases
                 if (not reference.get("cases") or c.name in reference["cases"])
                 and (not reference.get("groups") or c.group in reference["groups"])
                 and (not generation.get(c.name, {}).get("checkWith")
                      or reference["name"] in generation[c.name]["checkWith"])]
        if not cases:
            raise RuntimeError(f"{pid}: reference case scope is empty")
        scoped = {pid: replace(p, cases=cases)}
        judge = Judge(scoped, output / "reference-judge")
        result = judge.evaluate(pid, (p.root / reference["path"]).read_text(encoding="utf-8-sig"), reference["language"], f"{pid}-reference")
        good = result.verdict == "AC" and result.checked == len(cases)
        failed |= not good
        report["results"].append({"problem": pid, "solution": reference["path"], "case_scope": [c.name for c in cases],
                                  "passed": good, **asdict(result)})
        print(f"{pid} independent reference: {result.verdict} {result.checked}/{len(cases)} {'PASS' if good else 'FAIL'}", flush=True)
        (output / "reference-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["success"] = not failed
    (output / "reference-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
