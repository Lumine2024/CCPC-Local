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
from .diagnostics import emit, process_info

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
        self.pid_capacity = 16
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

    def pids(self):
        """Query only this Job, without enumerating the entire machine."""
        from ctypes import wintypes as w
        while True:
            class ProcessList(ctypes.Structure):
                _fields_ = [("assigned", w.DWORD), ("count", w.DWORD),
                            ("ids", ctypes.c_size_t * self.pid_capacity)]

            info = ProcessList()
            if self.kernel.QueryInformationJobObject(self.handle, 3, ctypes.byref(info), ctypes.sizeof(info), None):
                return list(info.ids[:info.count])
            if ctypes.get_last_error() != 234:  # ERROR_MORE_DATA
                raise ctypes.WinError(ctypes.get_last_error())
            self.pid_capacity = max(self.pid_capacity * 2, info.assigned)

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
    members = {}
    next_tree_scan = 0
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
            emit("process_start", child=process.pid, command=command, cwd=str(cwd),
                 timeout_ms=timeout_ms, memory_mb=memory_mb, output=str(output))
            started = time.monotonic()
            if job:
                job.attach_resume(process)
                # Native children inherit the Job. Python activation proxies
                # can launch outside it, so discover those immediately; other
                # runs only need the compatibility scan every 50 ms.
                next_tree_scan = started if Path(command[0]).name.lower().startswith("python") else started + 0.05
            while process.poll() is None:
                if stop and stop.is_set():
                    reason = "Cancelled"
                    break
                if (time.monotonic() - started) * 1000 >= timeout_ms:
                    # The monitor may have been descheduled after the loop's
                    # poll. Do not kill/classify a child using that stale state.
                    if process.poll() is not None:
                        emit("deadline_recheck_exit", child=process.pid, command=command,
                             elapsed_ms=(time.monotonic()-started)*1000, output=str(output),
                             exit_code=process.returncode)
                        break
                    reason = "TLE"
                    emit("process_timeout", child=process_info(root) if root else None,
                         elapsed_ms=(time.monotonic()-started)*1000, command=command,
                         output=str(output), stdout_bytes=output.stat().st_size,
                         stderr_bytes=error.stat().st_size)
                    break
                used = 0
                try:
                    if job:
                        active_pids = set(job.pids())
                        for pid in active_pids - members.keys():
                            try:
                                members[pid] = psutil.Process(pid)
                            except psutil.NoSuchProcess:
                                pass
                        members = {pid: child for pid, child in members.items() if pid in active_pids}
                        if root and time.monotonic() >= next_tree_scan:
                            for child in root.children(recursive=True):
                                if child.pid not in active_pids:
                                    descendants[child.pid] = child
                            next_tree_scan = time.monotonic() + 0.05
                        monitored = {**descendants, **members}.values()
                    else:
                        monitored = [root, *root.children(recursive=True)] if root else []
                        for child in monitored:
                            descendants[child.pid] = child
                    for child in monitored:
                        try:
                            m = child.memory_info()
                            used += max(m.rss, getattr(m, "private", 0))
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                peak = max(peak, used)
                if job:
                    peak = max(peak, job.peak())
                if memory_mb and peak > memory_mb * 1024 * 1024:
                    reason = "MLE"
                    break
                if output.stat().st_size > output_limit or error.stat().st_size > 1024 * 1024:
                    reason = "OLE"
                    break
                # Python's sleep uses a high-resolution timer on Windows.
                # Popen.wait(timeout=.003) rounds to about 15 ms there and
                # adds substantial latency to short programs and checkers.
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
        elapsed_ms = int((time.monotonic() - started) * 1000)
        emit("process_complete", child=process.pid, verdict=verdict, command=command,
             output=str(output), elapsed_ms=elapsed_ms, peak_bytes=peak)
        return RunResult(verdict, process.returncode, elapsed_ms, peak // 1024)
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
