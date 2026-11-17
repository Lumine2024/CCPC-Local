from pathlib import Path
from dataclasses import replace
import json
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import psutil

from backend.judge import Judge
from backend.problems import Case, load_problems
from backend.runner import RunResult
from test_core import fixture


class CompilationTests(unittest.TestCase):
    def test_invalid_source_does_not_build_checker(self):
        with tempfile.TemporaryDirectory(prefix="judge compilation ") as temp:
            root = Path(temp)
            problem_root, _ = fixture(root)
            problems, _ = load_problems(problem_root)
            judge = Judge(problems, root / "judge")
            with patch.object(judge, "checker") as checker, patch.object(
                judge, "compile", return_value=(RunResult("RE", 1, 0, 0), "invalid C++")
            ):
                for language, source in [("cpp", "invalid C++"), ("python", "def broken(:")]:
                    with self.subTest(language=language):
                        result = judge.evaluate("A", source, language)
                        self.assertEqual(result.verdict, "CE")
                        self.assertTrue(result.message)
                        checker.assert_not_called()
            judge.close()


class JudgeFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="judge pipeline ")
        self.root = Path(self.temp.name)
        problem_root, _ = fixture(self.root)
        self.problems, _ = load_problems(problem_root)
        p = self.problems["A"]
        cases = []
        for n in range(3):
            input_file, answer = self.root / f"{n}.in", self.root / f"{n}.ans"
            input_file.write_text(str(n)); answer.write_text(str(n))
            cases.append(Case(str(n), "sample", input_file, answer))
        p.cases = cases
        self.judge = Judge(self.problems, self.root / "judge")
        self.judge.checkers["A"] = p.checker

    def tearDown(self):
        self.judge.close()
        self.temp.cleanup()

    def evaluate(self, fake_run):
        with patch("backend.judge.run", side_effect=fake_run), patch.object(
            self.judge, "checker", side_effect=AssertionError("checker built during submission")
        ):
            return self.judge.evaluate("A", "print(1)", "python", "pipeline")


class PipelineTests(JudgeFixture, unittest.TestCase):

    def test_checker_overlaps_next_program_and_outputs_are_isolated(self):
        checker_started, second_program = threading.Event(), threading.Event()
        active = set()
        lock = threading.Lock()

        def fake_run(command, cwd, output, error, **kwargs):
            if output.name == "program.out":
                n = int(kwargs["input_file"].stem)
                with lock:
                    self.assertFalse(active, "two contestant programs ran together")
                    active.add(n)
                try:
                    if n == 1:
                        self.assertTrue(checker_started.wait(2))
                        second_program.set()
                    output.write_text(str(n))
                    return RunResult("OK", 0, n + 10, n + 100)
                finally:
                    with lock:
                        active.remove(n)
            n = int(Path(command[1]).stem)
            if n == 0:
                checker_started.set()
                self.assertTrue(second_program.wait(2), "checker and next program did not overlap")
            self.assertEqual(Path(command[2]).read_text(), str(n))
            self.assertEqual(Path(command[3]).read_text(), str(n))
            return RunResult("OK", 0, 1, 1)

        result = self.evaluate(fake_run)
        self.assertEqual(result.verdict, "AC")
        self.assertEqual(result.checked, 3)
        self.assertEqual((result.time_ms, result.memory_kb), (12, 102))

    def test_fail_fast_cancels_next_run_and_preserves_earliest_verdict(self):
        for next_verdict in ("Cancelled", "RE"):
            with self.subTest(next_verdict=next_verdict):
                second_program = threading.Event()
                programs, checks = [], []

                def fake_run(command, cwd, output, error, **kwargs):
                    if output.name == "program.out":
                        n = int(kwargs["input_file"].stem)
                        programs.append(n)
                        output.write_text(str(n))
                        if n == 1:
                            second_program.set()
                            # The earlier WA must signal cancellation before
                            # run() returns, even while that run is still active.
                            self.assertTrue(kwargs["stop"].events[-1].wait(2))
                            return RunResult(next_verdict, 1, 9999, 9999)
                        return RunResult("OK", 0, 10, 100)
                    checks.append(int(Path(command[1]).stem))
                    self.assertTrue(second_program.wait(2))
                    return RunResult("RE", 1, 1, 1)

                result = self.evaluate(fake_run)
                self.assertEqual(result.verdict, "WA")
                self.assertEqual(result.checked, 0)
                self.assertEqual((result.time_ms, result.memory_kb), (10, 100))
                self.assertEqual(programs, [0, 1])
                self.assertEqual(checks, [0])
                self.assertFalse(self.judge.stop.is_set(), "local failure stopped the whole service")

    def test_runtime_failure_after_successful_previous_checker(self):
        second_program = threading.Event()
        programs, checks = [], []

        def fake_run(command, cwd, output, error, **kwargs):
            if output.name == "program.out":
                n = int(kwargs["input_file"].stem)
                programs.append(n); output.write_text(str(n))
                if n == 1:
                    second_program.set()
                    return RunResult("TLE", 1, 1000, 200)
                return RunResult("OK", 0, 10, 100)
            checks.append(int(Path(command[1]).stem))
            self.assertTrue(second_program.wait(2))
            return RunResult("OK", 0, 1, 1)

        result = self.evaluate(fake_run)
        self.assertEqual((result.verdict, result.checked), ("TLE", 1))
        self.assertEqual(programs, [0, 1, 1]); self.assertEqual(checks, [0])

    def test_transient_timeout_rechecks_same_limits_and_checks_retry_output(self):
        attempts = []

        def fake_run(command, cwd, output, error, **kwargs):
            if output.name == "program.out":
                attempts.append(kwargs)
                output.write_text(str(len(attempts)))
                if len(attempts) == 1:
                    return RunResult("TLE", 1, 1000, 200)
                return RunResult("OK", 0, 10, 100)
            contestant = Path(command[2])
            self.assertNotEqual(contestant.read_text(), "1")
            return RunResult("OK", 0, 1, 1)

        result = self.evaluate(fake_run)
        self.assertEqual((result.verdict, result.checked), ("AC", 3))
        self.assertEqual(len(attempts), 4)
        self.assertEqual(attempts[0], attempts[1])
        report = json.loads((self.judge.root / "jobs/pipeline/result.json").read_text())
        first = report["cases"][0]
        self.assertEqual([x["run"]["verdict"] for x in first["attempts"]], ["TLE", "OK"])
        self.assertEqual(first["run"]["verdict"], "OK")

    def test_timeout_confirmation_is_bounded_per_submission(self):
        calls = []

        def fake_run(command, cwd, output, error, **kwargs):
            if output.name == "program.out":
                n = int(kwargs["input_file"].stem)
                calls.append(n)
                output.write_text(str(n))
                return RunResult("OK", 0, 10, 100) if len(calls) == 2 else RunResult("TLE", 1, 1000, 200)
            return RunResult("OK", 0, 1, 1)

        result = self.evaluate(fake_run)
        self.assertEqual((result.verdict, result.checked), ("TLE", 1))
        self.assertEqual(calls, [0, 0, 1])

    def test_last_checker_failure_cannot_return_ac(self):
        for code, expected in [(1, "WA"), (2, "WA"), (4, "WA"), (8, "WA"), (3, "Judge Error")]:
            with self.subTest(code=code):
                def fake_run(command, cwd, output, error, **kwargs):
                    if output.name == "program.out":
                        output.write_text("output")
                        return RunResult("OK", 0, 10, 100)
                    n = int(Path(command[1]).stem)
                    return RunResult("RE", code, 1, 1) if n == 2 else RunResult("OK", 0, 1, 1)

                result = self.evaluate(fake_run)
                self.assertEqual((result.verdict, result.checked), (expected, 2))

    def test_checker_exception_cancels_speculation_and_next_submission_works(self):
        second_program = threading.Event()

        def broken_run(command, cwd, output, error, **kwargs):
            if output.name == "program.out":
                n = int(kwargs["input_file"].stem)
                output.write_text(str(n))
                if n == 1:
                    second_program.set()
                    self.assertTrue(kwargs["stop"].events[-1].wait(2))
                    return RunResult("Cancelled", 1, 1, 1)
                return RunResult("OK", 0, 1, 1)
            self.assertTrue(second_program.wait(2))
            raise OSError("controlled checker failure")

        self.assertEqual(self.evaluate(broken_run).verdict, "Judge Error")
        self.assertFalse(self.judge.stop.is_set())
        self.assertEqual(self.evaluate(lambda *args, **kwargs: RunResult("OK", 0, 1, 1)).checked, 3)

    def test_shutdown_cancels_both_stages_and_returns_queued(self):
        second_program = threading.Event()

        def fake_run(command, cwd, output, error, **kwargs):
            if output.name == "program.out":
                n = int(kwargs["input_file"].stem)
                output.write_text(str(n))
                if n == 1:
                    self.judge.stop.set()
                    second_program.set()
                    return RunResult("Cancelled", 1, 1, 1)
                return RunResult("OK", 0, 1, 1)
            self.assertTrue(second_program.wait(2))
            self.assertTrue(kwargs["stop"].is_set())
            return RunResult("Cancelled", 1, 1, 1)

        self.assertEqual(self.evaluate(fake_run).verdict, "Queued")

    def test_real_fail_fast_terminates_speculative_program_and_child(self):
        p = self.problems["A"]
        p.config["timeLimitMs"] = 5000
        p.checker.write_text('''
#include <chrono>
#include <filesystem>
#include <thread>
int main() {
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(4);
    while (!std::filesystem::exists("spawned.pid") && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    return 1;
}
''')
        self.judge.checkers.clear()
        self.judge.prepare_checkers()
        source = """import subprocess, sys, time
n = int(sys.stdin.read())
if n == 1:
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
    with open('spawned.pid', 'w') as file:
        file.write(str(child.pid))
    time.sleep(120)
print(n)
"""
        result = self.judge.evaluate("A", source, "python", "real-pipeline")
        self.assertEqual((result.verdict, result.checked), ("WA", 0))
        work = self.judge.root / "jobs" / "real-pipeline"
        child_pid = int((work / "spawned.pid").read_text())
        self.assertFalse(psutil.pid_exists(child_pid))
        report = json.loads((work / "result.json").read_text())
        self.assertEqual(len(report["cases"]), 2)
        self.assertEqual(report["cases"][1]["run"]["verdict"], "Cancelled")
        self.assertTrue(report["cases"][1]["discarded"])


class PreparationTests(JudgeFixture, unittest.TestCase):
    def test_worker_prepares_all_checkers_before_accepting_recovered_submission(self):
        self.problems["B"] = replace(self.problems["A"], id="B")
        storage = Mock()
        storage.recover.return_value = [1]
        storage.get_submission.return_value = {"problem": "A", "source": "print(1)", "language": "python"}
        judge = Judge(self.problems, self.root / "worker", storage)
        prepared, evaluated = [], threading.Event()

        def prepare(p):
            prepared.append(p.id)
            return p.checker

        def evaluate(*args):
            self.assertCountEqual(prepared, ["A", "B"])
            self.assertTrue(judge.checkers_ready.is_set())
            evaluated.set(); judge.stop.set()
            from backend.judge import Verdict
            return Verdict("AC", "", 3)

        with patch.object(judge, "checker", side_effect=prepare) as build, patch.object(judge, "evaluate", side_effect=evaluate):
            try:
                judge.start("input")
                self.assertTrue(evaluated.wait(2))
                judge.prepare_checkers()
                self.assertEqual(build.call_count, 2, "preparation was repeated")
            finally:
                judge.close()

    def test_checker_failure_isolated_to_its_problem(self):
        self.problems["B"] = replace(self.problems["A"], id="B")
        judge = Judge(self.problems, self.root / "prepare")

        def prepare(p):
            if p.id == "B":
                raise RuntimeError("controlled build error")
            return p.checker

        with patch.object(judge, "checker", side_effect=prepare), self.assertLogs(level="ERROR"):
            judge.prepare_checkers()
        self.assertTrue(judge.checkers_ready.is_set())
        self.assertIn("A", judge.checkers)
        self.assertIn("B", judge.checker_errors)
        self.assertEqual(judge.evaluate("B", "print(1)", "python").verdict, "Judge Error")
        judge.close()

    def test_interrupted_build_is_never_published_as_cached(self):
        judge = self.judge

        def interrupted(p, source, output, work):
            output.write_bytes(b"unfinished executable")
            judge.stop.set()
            return RunResult("Cancelled", 1, 1, 1), ""

        with patch.object(judge, "compile", side_effect=interrupted):
            judge.prepare_checkers()
        self.assertFalse(judge.checkers_ready.is_set())
        self.assertEqual(list((judge.root / "cache").rglob("checker*")), [])
