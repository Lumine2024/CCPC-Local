"""Compile and judge submissions using the problem's actual testlib checker."""
import hashlib
import json
import os
import queue
import re
import shutil
import sys
import threading
import traceback
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


class Judge:
    def __init__(self, problems, data_root, storage=None):
        self.problems = problems
        self.root = Path(data_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.storage = storage
        self.stop = threading.Event()
        self.queue = queue.Queue()
        self.thread = None
        self.compile_lock = threading.Lock()
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
        with self.compile_lock:
            if executable.is_file():
                return executable
            folder.mkdir(parents=True, exist_ok=True)
            result, _ = self.compile(p, p.checker, executable, folder)
            if result.verdict != "OK" or not executable.is_file():
                raise RuntimeError(f"题目 {p.id} 的 checker 编译失败，请查看内部编译日志")
        return executable

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
            checker = self.checker(p)
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
            if progress:
                progress("Running")
            checked, max_time, max_memory = 0, 0, 0
            case_logs = []
            for case in p.cases:
                output, error = work / "program.out", work / "program.err"
                result = run(command, work, output, error, input_file=case.input,
                             timeout_ms=p.config["timeLimitMs"], memory_mb=p.config["memoryLimitMb"], stop=self.stop)
                max_time, max_memory = max(max_time, result.time_ms), max(max_memory, result.memory_kb)
                case_logs.append({"case": case.name, "run": asdict(result)})
                if result.verdict == "Cancelled":
                    return Verdict("Queued", "")
                if result.verdict != "OK":
                    verdict = Verdict(result.verdict, "", checked, max_time, max_memory)
                    break
                judge_result = run([str(checker), str(case.input), str(output), str(case.answer)], work,
                                   work / "checker.out", work / "checker.err", timeout_ms=10000,
                                   memory_mb=0, stop=self.stop)
                case_logs[-1]["checker"] = asdict(judge_result)
                if judge_result.verdict == "Cancelled":
                    return Verdict("Queued", "")
                if judge_result.exit_code in {1, 2, 4, 8} and judge_result.verdict == "RE":
                    verdict = Verdict("WA", "", checked, max_time, max_memory)
                    break
                if judge_result.verdict != "OK":
                    verdict = Verdict("Judge Error", "评测器异常，请查看服务端日志", checked, max_time, max_memory)
                    break
                checked += 1
            else:
                verdict = Verdict("AC", "", checked, max_time, max_memory)
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
