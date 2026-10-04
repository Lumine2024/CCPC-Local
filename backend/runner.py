"""Bounded file-based process execution with process-tree cleanup.

Windows: suspended start + Job Object; private/working-set memory accounting.
POSIX: new process group + RSS polling. This is resource control, not a sandbox.
"""
import ctypes
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event

import psutil


class WindowsJob:
    def __init__(self):
        from ctypes import wintypes as w
        size = ctypes.c_size_t

        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", w.DWORD), ("minimum_ws", size), ("maximum_ws", size),
                        ("active", w.DWORD), ("affinity", size), ("priority", w.DWORD), ("scheduling", w.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("read_ops", "write_ops", "other_ops", "read", "write", "other")]

        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", size), ("job_memory", size),
                        ("peak_process", size), ("peak_job", size)]

        class Accounting(ctypes.Structure):
            _fields_ = [("user", ctypes.c_int64), ("kernel", ctypes.c_int64),
                        ("period_user", ctypes.c_int64), ("period_kernel", ctypes.c_int64),
                        ("faults", w.DWORD), ("total", w.DWORD), ("active", w.DWORD), ("terminated", w.DWORD)]

        self.Extended = Extended
        self.Accounting = Accounting
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.kernel.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p]
        self.kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.kernel.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        info = Extended()
        info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, no breakaway
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def attach_resume(self, process):
        if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())
        resume = ctypes.WinDLL("ntdll").NtResumeProcess
        resume.argtypes = [ctypes.c_void_p]
        resume.restype = ctypes.c_long
        if resume(int(process._handle)) != 0:
            raise OSError("无法恢复隔离评测进程")

    def peak(self):
        info = self.Extended()
        if self.kernel.QueryInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info), None):
            return info.peak_job
        return 0

    def close(self):
        if self.handle:
            self.kernel.TerminateJobObject(self.handle, 1)
            deadline = time.monotonic() + 5
            # Windows termination is asynchronous. Wait for *all* Job members,
            # not just the root, before closing redirected files or returning.
            while time.monotonic() < deadline:
                info = self.Accounting()
                if not self.kernel.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None) or not info.active:
                    break
                time.sleep(0.003)
            self.kernel.CloseHandle(self.handle)
            self.handle = None


@dataclass
class RunResult:
    verdict: str
    exit_code: int
    time_ms: int
    memory_kb: int


def run(command: list[str], cwd: Path, output: Path, error: Path, *, input_file: Path | None = None,
        timeout_ms=1000, memory_mb=256, output_limit=16 * 1024 * 1024, stop: Event | None = None) -> RunResult:
    job, process, peak, reason = None, None, 0, ""
    descendants = {}
    started = time.monotonic()
    try:
        if os.name == "nt":
            job = WindowsJob()
        with (input_file.open("rb") if input_file else open(os.devnull, "rb")) as stdin, \
                output.open("wb") as stdout, error.open("wb") as stderr:
            options = {"creationflags": 0x4 | 0x08000000} if os.name == "nt" else {"start_new_session": True}
            process = subprocess.Popen(command, cwd=cwd, stdin=stdin, stdout=stdout, stderr=stderr, **options)
            try:
                root = psutil.Process(process.pid)
            except psutil.NoSuchProcess:
                root = None  # A very short POSIX process may already be reaped.
            # Do not charge OS process creation, executable scanning or Job
            # setup to the contestant. On Windows the process is still suspended.
            started = time.monotonic()
            if job:
                job.attach_resume(process)
            while process.poll() is None:
                if stop and stop.is_set():
                    reason = "Cancelled"
                    break
                if (time.monotonic() - started) * 1000 >= timeout_ms:
                    reason = "TLE"
                    break
                used = 0
                try:
                    for child in ([root, *root.children(recursive=True)] if root else []):
                        descendants[child.pid] = child
                        try:
                            m = child.memory_info()
                            used += max(m.rss, getattr(m, "private", 0))
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                peak = max(peak, used)
                if memory_mb and peak > memory_mb * 1024 * 1024:
                    reason = "MLE"
                    break
                if output.stat().st_size > output_limit or error.stat().st_size > 1024 * 1024:
                    reason = "OLE"
                    break
                time.sleep(0.003)
            if job:
                peak = max(peak, job.peak())
                job.close()  # closes even if the root exited with live children
            elif process:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            # Windows Store/venv activation proxies may create descendants
            # outside the inherited Job. Retain Process objects (with creation
            # identity) rather than killing arbitrary reused numeric PIDs.
            for child in descendants.values():
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            psutil.wait_procs(list(descendants.values()), timeout=5)
            process.wait(timeout=5)
        if not reason and memory_mb and peak > memory_mb * 1024 * 1024:
            reason = "MLE"
        if not reason and (output.stat().st_size > output_limit or error.stat().st_size > 1024 * 1024):
            reason = "OLE"
        verdict = reason or ("OK" if process.returncode == 0 else "RE")
        return RunResult(verdict, process.returncode, int((time.monotonic() - started) * 1000), peak // 1024)
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.kill()
            process.wait()
        for child in descendants.values():
            try:
                if child.is_running():
                    child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
