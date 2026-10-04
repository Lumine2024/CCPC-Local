"""Real corpus judging acceptance; writes inspectable per-case logs and JSON."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.problems import load_problems
from backend.contest_parser import parse_contest
from backend.judge import Judge


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem-list", type=Path, default=ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest")
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/acceptance")
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    problems, fingerprint = load_problems(args.problem_list)
    judge = Judge(problems, args.output / "judge")
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
              "python": sys.version, "input_fingerprint": fingerprint, "results": [], "success": False}
    failed = False
    for pid, p in problems.items():
        main_solution = next(s for s in p.config["solutions"] if s["role"] == "main")
        for label, entry in [("main", main_solution), ("wrong", p.config["wrongSolutions"][0])]:
            started = time.monotonic()
            result = judge.evaluate(pid, (p.root / entry["path"]).read_text(encoding="utf-8-sig"), entry["language"], f"{pid}-{label}")
            good = result.verdict == "AC" and result.checked == len(p.cases) if label == "main" else result.verdict in {"WA", "TLE", "MLE", "RE", "OLE"}
            failed |= not good
            report["results"].append({"problem": pid, "role": label, "solution": entry["path"],
                "case_count": len(p.cases), "elapsed_seconds": round(time.monotonic()-started, 2), "passed": good, **asdict(result)})
            print(f"{pid} {label}: {result.verdict}, {result.checked}/{len(p.cases)} cases, {'PASS' if good else 'FAIL'}", flush=True)
            (args.output / "judge-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # Deliberately controlled submissions validate distinct verdict paths.
    pid = "L" if "L" in problems else next(iter(problems))
    probes = {"CE": "this is not C++;", "TLE": "int main(){for(;;){}}",
              "RE": "#include <cstdlib>\nint main(){std::abort();}",
              "MLE": "#include <cstdlib>\n#include <cstring>\n#include <vector>\nint main(){std::vector<void*> p; for(;;){void* q=std::malloc(16*1024*1024);if(!q)continue;std::memset(q,1,16*1024*1024);p.push_back(q);}}",
              "OLE": '#include <cstdio>\nint main(){for(;;)std::puts("01234567890123456789012345678901234567890123456789");}'}
    for expected, source in probes.items():
        result = judge.evaluate(pid, source, "cpp", f"probe-{expected}")
        good = result.verdict == expected; failed |= not good
        report["results"].append({"probe": expected, "passed": good, **asdict(result)})
        print(f"probe {expected}: {result.verdict} {'PASS' if good else 'FAIL'}", flush=True)
    # A compiler-valid checker that reports _fail verifies system error mapping.
    from dataclasses import replace
    bad = args.output / "bad-checker.cpp"; bad.write_text("int main(){return 3;}")
    alternate = dict(problems); alternate[pid] = replace(problems[pid], checker=bad.resolve())
    bad_judge = Judge(alternate, args.output / "system-error")
    result = bad_judge.evaluate(pid, "int main(){return 0;}", "cpp", "probe-system-error")
    good = result.verdict == "Judge Error"; failed |= not good
    report["results"].append({"probe": "Judge Error", "passed": good, **asdict(result)})
    print(f"probe Judge Error: {result.verdict} {'PASS' if good else 'FAIL'}", flush=True)
    _, after = load_problems(args.problem_list)
    report["inputs_unchanged"] = after == fingerprint
    failed |= not report["inputs_unchanged"]
    report["success"] = not failed
    (args.output / "judge-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
