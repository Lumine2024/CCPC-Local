"""Measure complete submissions and process phases on real exported cases."""
import argparse
import cProfile
from dataclasses import asdict
import json
from pathlib import Path
import platform
import pstats
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import judge as judge_module
from backend.problems import load_problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem-list", type=Path, default=ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest")
    parser.add_argument("--problems", nargs="+", default=["A", "L"])
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/judge-benchmark")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    problems, fingerprint = load_problems(args.problem_list)
    judge = judge_module.Judge({pid: problems[pid] for pid in args.problems}, args.output / "judge")
    original_run = judge_module.run
    phases = {}

    def timed_run(command, cwd, output, error, **kwargs):
        phase = "compile" if output.name == "compile.out" else "checker" if output.name == "checker.out" else "program"
        started = time.perf_counter()
        try:
            return original_run(command, cwd, output, error, **kwargs)
        finally:
            phases[phase] = phases.get(phase, 0) + time.perf_counter() - started

    judge_module.run = timed_run
    report = {"platform": platform.platform(), "python": sys.version, "input_fingerprint": fingerprint, "results": []}
    profiler = cProfile.Profile()
    try:
        if args.profile:
            profiler.enable()
        original_checker = judge.checker

        def timed_checker(p):
            started = time.perf_counter()
            try:
                return original_checker(p)
            finally:
                report.setdefault("checker_setup_seconds", {})[p.id] = round(time.perf_counter() - started, 3)

        judge.checker = timed_checker
        try:
            judge.prepare_checkers()
        finally:
            judge.checker = original_checker
        for pid in args.problems:
            p = problems[pid]
            entries = [s for s in p.config["solutions"] if s["role"] == "main" or s["language"] == "python"]
            for entry in entries:
                for attempt in range(args.rounds):
                    phases.clear()
                    started = time.perf_counter()
                    result = judge.evaluate(pid, (p.root / entry["path"]).read_text(encoding="utf-8-sig"), entry["language"])
                    row = {"problem": pid, "language": entry["language"], "round": attempt + 1,
                           "elapsed_seconds": round(time.perf_counter() - started, 3),
                           "phases_seconds": {k: round(v, 3) for k, v in phases.items()}, **asdict(result)}
                    report["results"].append(row)
                    print(json.dumps(row), flush=True)
    finally:
        judge_module.run = original_run
        profiler.disable()
        judge.close()
    report["success"] = all(r["verdict"] == "AC" and r["checked"] == len(problems[r["problem"]].cases) for r in report["results"])
    (args.output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.profile:
        with (args.output / "profile.txt").open("w", encoding="utf-8") as stream:
            pstats.Stats(profiler, stream=stream).sort_stats("cumulative").print_stats(40)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
