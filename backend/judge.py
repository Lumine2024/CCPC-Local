"""Compile and judge submissions using the problem's actual testlib checker."""
import hashlib
import json
import logging
import os
import queue
import re
import shutil
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

from .problems import Problem
from .runner import run


@dataclass
class Verdict:
    verdict: str
    message: str
    checked: int = 0
    time_ms: int = 0
    memory_kb: int = 0


class StopSignal:
    """Combine service shutdown and submission-local pipeline cancellation."""
    def __init__(self, *events):
        self.events = events

    def is_set(self):
        return any(event.is_set() for event in self.events)


class Judge:
    def __init__(self, problems, data_root, storage=None):
        self.problems = problems
        self.root = Path(data_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.storage = storage
        self.stop = threading.Event()
        self.queue = queue.Queue()
        self.thread = None
        self.checker_locks = {pid: threading.Lock() for pid in problems}
        self.prepare_lock = threading.Lock()
        self.checkers = {}
        self.checker_errors = {}
        self.checkers_ready = threading.Event()
        self.compilers = {}
        for pid, p in problems.items():
            compiler = p.config.get("build", {}).get("cppCompiler", "g++")
            resolved = shutil.which(compiler)
            if not resolved:
                raise ValueError(f"题目 {pid}: 找不到编译器 {compiler}，请安装 GCC 并加入 PATH")
            self.compilers[pid] = resolved
        self.languages = [{"id": "cpp", "name": "GNU C++20（题包标准）"}, {"id": "python", "name": "Python 3"}]

    def compile(self, problem: Problem, source: Path, output: Path, work: Path):
        build = problem.config.get("build", {})
        flags = build.get("cppFlags", ["-std={{standard}}", "-O2", "-pipe"])
        if not isinstance(flags, list) or any(not isinstance(x, str) for x in flags):
            raise ValueError("cppFlags 必须为字符串数组")
        flags = [x.replace("{{standard}}", problem.config["standard"]) for x in flags]
        if any("{{" in x for x in flags):
            raise ValueError("未知编译参数模板")
        command = [self.compilers[problem.id], *flags, "-I", str(problem.include), str(source), "-o", str(output)]
        if os.name == "nt":
            command.append("-Wl,--stack,268435456")
        result = run(command, work, work / "compile.out", work / "compile.err",
                     timeout_ms=120000, memory_mb=0, stop=self.stop)
        diagnostic = (work / "compile.err").read_text(encoding="utf-8", errors="replace")[:16000]
        return result, diagnostic

    def checker(self, p: Problem) -> Path:
        flags = p.config.get("build", {})
        digest = hashlib.sha256(p.checker.read_bytes() + (p.include / "testlib.h").read_bytes() +
                                json.dumps([flags, p.config["standard"], self.compilers[p.id]], sort_keys=True).encode()).hexdigest()
        folder = self.root / "cache" / p.id / digest
        executable = folder / ("checker.exe" if os.name == "nt" else "checker")
        with self.checker_locks[p.id]:
            if executable.is_file():
                return executable
            folder.mkdir(parents=True, exist_ok=True)
            # Publish only a completed build; shutdown must not leave an
            # incomplete executable that a later launch accepts as cached.
            building = folder / ("checker-building.exe" if os.name == "nt" else "checker-building")
            building.unlink(missing_ok=True)
            try:
                result, _ = self.compile(p, p.checker, building, folder)
                if result.verdict != "OK" or not building.is_file():
                    raise RuntimeError(f"题目 {p.id} 的 checker 编译失败，请查看内部编译日志")
                building.replace(executable)
            finally:
                building.unlink(missing_ok=True)
        return executable

    def prepare_checkers(self):
        """Build/load every checker before consuming the submission queue."""
        with self.prepare_lock:
            if self.checkers_ready.is_set():
                return
            logging.info("Preparing %d problem checkers", len(self.problems))

            def prepare(problem):
                pid = problem.id
                if self.stop.is_set():
                    return
                try:
                    self.checkers[pid] = self.checker(problem)
                except Exception:
                    if self.stop.is_set():
                        return
                    self.checker_errors[pid] = f"题目 {pid} 的 checker 构建失败，请查看服务端日志"
                    logging.exception("Problem %s checker preparation failed", pid)

            # Bound compiler concurrency; do not launch a compiler per problem
            # or run warm-up alongside resource-limited contestant programs.
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="checker-build") as executor:
                futures = [executor.submit(prepare, problem) for problem in self.problems.values()]
                for future in futures:
                    future.result()
            if not self.stop.is_set():
                self.checkers_ready.set()
                logging.info("Checkers ready: %d available, %d failed", len(self.checkers), len(self.checker_errors))

    @staticmethod
    def checker_verdict(result):
        if result.verdict == "OK":
            return "AC", ""
        if result.verdict == "Cancelled":
            return "Queued", ""
        if result.exit_code in {1, 2, 4, 8} and result.verdict == "RE":
            return "WA", ""
        return "Judge Error", "评测器异常，请查看服务端日志"

    def evaluate_cases(self, p, command, checker, work):
        """One program run overlaps one checker, with at most one case ahead."""
        program_stop, checker_stop = threading.Event(), threading.Event()
        program_signal = StopSignal(self.stop, program_stop)
        checker_signal = StopSignal(self.stop, checker_stop)
        logs, checked, pending = [], 0, None
        verdict, message = "AC", ""

        def check(case, folder, entry):
            try:
                result = run([str(checker), str(case.input), str(folder / "program.out"), str(case.answer)],
                             work, folder / "checker.out", folder / "checker.err",
                             timeout_ms=10000, memory_mb=0, stop=checker_signal)
                entry["checker"] = asdict(result)
                status = self.checker_verdict(result)
                if status[0] != "AC":
                    program_stop.set()
                return status
            except Exception:
                program_stop.set()
                raise

        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="case-checker")
        try:
            for index, case in enumerate(p.cases):
                # If the previous answer is already known, avoid even starting
                # a speculative run for the next input after a failure.
                if pending and pending.done():
                    verdict, message = pending.result()
                    pending = None
                    if verdict != "AC":
                        break
                    checked += 1
                if self.stop.is_set():
                    verdict, message = "Queued", ""
                    break
                folder = work / "cases" / f"{index + 1:05d}"
                folder.mkdir(parents=True, exist_ok=True)
                result = run(command, work, folder / "program.out", folder / "program.err",
                             input_file=case.input, timeout_ms=p.config["timeLimitMs"],
                             memory_mb=p.config["memoryLimitMb"], stop=program_signal)
                entry = {"case": case.name, "run": asdict(result)}
                logs.append(entry)
                if pending:
                    # A later RE/TLE must not replace an earlier WA or checker
                    # failure. Resolve in manifest order, then count passed cases.
                    verdict, message = pending.result()
                    pending = None
                    if verdict != "AC":
                        entry["discarded"] = True
                        break
                    checked += 1
                if result.verdict != "OK":
                    verdict = "Queued" if result.verdict == "Cancelled" else result.verdict
                    message = ""
                    break
                pending = executor.submit(check, case, folder, entry)
            else:
                if pending:
                    verdict, message = pending.result()
                    pending = None
                    if verdict == "AC":
                        checked += 1
        finally:
            # On failure, shutdown, or an exception, stop any in-flight work
            # before returning or processing another submission.
            program_stop.set()
            checker_stop.set()
            executor.shutdown(wait=True, cancel_futures=True)
        if verdict == "Queued":
            return Verdict("Queued", ""), logs
        measured = [entry["run"] for entry in logs if not entry.get("discarded")]
        return Verdict(verdict, message, checked,
                       max((entry["time_ms"] for entry in measured), default=0),
                       max((entry["memory_kb"] for entry in measured), default=0)), logs

    def evaluate(self, pid, source, language="cpp", job_id=None, progress=None) -> Verdict:
        import uuid
        p = self.problems[pid]
        work = self.root / "jobs" / str(job_id or uuid.uuid4().hex)
        work.mkdir(parents=True, exist_ok=True)
        src = work / ("submission.cpp" if language == "cpp" else "submission.py")
        src.write_text(source, encoding="utf-8")
        if progress:
            progress("Compiling")
        try:
            if language == "cpp":
                binary = work / ("submission.exe" if os.name == "nt" else "submission")
                # Never accept a stale executable after an interrupted compilation.
                if binary.exists():
                    binary.unlink()
                compilation, diagnostic = self.compile(p, src, binary, work)
                if compilation.verdict == "Cancelled":
                    return Verdict("Queued", "")
                if compilation.verdict != "OK" or not binary.exists():
                    message = diagnostic.replace(str(work), "<submission>").replace(str(p.root), "<problem>")
                    return Verdict("CE", message or "编译失败或超时")
                command = [str(binary)]
            elif language == "python":
                try:
                    compile(source, "<submission>", "exec")
                except (SyntaxError, ValueError) as exc:
                    return Verdict("CE", f"Python 语法错误：{exc}")
                command = [sys.executable, "-I", str(src)]
            else:
                return Verdict("Judge Error", "不支持的语言")
            if self.stop.is_set():
                return Verdict("Queued", "")
            # Submission processing never compiles a checker. Production
            # prepares all problems before taking the first queued submission;
            # standalone callers explicitly call prepare_checkers() first.
            checker = self.checkers.get(pid)
            if checker is None or not checker.is_file():
                return Verdict("Judge Error", self.checker_errors.get(pid, "checker 尚未就绪，请查看服务端日志"))
            if progress:
                progress("Running")
            verdict, case_logs = self.evaluate_cases(p, command, checker, work)
            (work / "result.json").write_text(json.dumps({"problem": pid, "result": asdict(verdict),
                                                          "cases": case_logs}, ensure_ascii=False, indent=2), encoding="utf-8")
            return verdict
        except Exception:
            (work / "exception.log").write_text(traceback.format_exc(), encoding="utf-8")
            return Verdict("Queued" if self.stop.is_set() else "Judge Error", "评测服务异常，请查看服务端日志")

    def start(self, input_id):
        for sub_id in self.storage.recover(input_id):
            self.queue.put(sub_id)
        self.thread = threading.Thread(target=self.worker, name="local-judge", daemon=True)
        self.thread.start()

    def worker(self):
        self.prepare_checkers()
        while not self.stop.is_set():
            try:
                sub_id = self.queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                sub = self.storage.get_submission(sub_id)
                if sub:
                    result = self.evaluate(sub["problem"], sub["source"], sub["language"], sub_id,
                                           lambda state: self.storage.update(sub_id, verdict=state))
                    self.storage.update(sub_id, **asdict(result))
            finally:
                self.queue.task_done()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=15)
            if self.thread.is_alive():
                raise RuntimeError("判题进程未能及时停止")
