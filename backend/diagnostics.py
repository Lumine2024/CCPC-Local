"""Opt-in bounded diagnostics, with no polling in the request/judge paths."""
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
import time
import traceback

import psutil

_sink = None


def emit(event, **fields):
    if _sink is not None:
        try:
            _sink.info(json.dumps(dict(event=event, wall=time.time(), mono=time.monotonic(),
                                       pid=os.getpid(), thread=threading.current_thread().name, **fields),
                                  ensure_ascii=False))
        except Exception:
            # Instrumentation must never change a contestant verdict.
            pass


def process_info(process):
    try:
        with process.oneshot():
            cpu = process.cpu_times()
            return dict(pid=process.pid, created=process.create_time(), status=process.status(),
                        rss=process.memory_info().rss, cpu_user=cpu.user, cpu_system=cpu.system,
                        threads=process.num_threads(),
                        handles=process.num_handles() if os.name == "nt" else process.num_fds())
    except (psutil.Error, OSError) as exc:
        return dict(pid=process.pid, error=type(exc).__name__)


class Monitor:
    def __init__(self, root, interval, app, server):
        global _sink
        if interval <= 0:
            raise ValueError("diagnostics interval must be positive")
        self.app, self.server, self.interval = app, server, interval
        self.stop_file = Path(root) / "diagnostics-stop.request"
        self.stop = threading.Event()
        self.log = logging.getLogger("ccpc.diagnostics")
        self.log.propagate = False
        self.log.setLevel(logging.INFO)
        self.handler = RotatingFileHandler(Path(root) / "diagnostics.jsonl", maxBytes=8*1024*1024,
                                           backupCount=3, encoding="utf-8")
        self.log.addHandler(self.handler)
        _sink = self.log
        self.thread = threading.Thread(target=self.loop, name="diagnostic-monitor", daemon=True)
        emit("monitor_start", interval=interval, python=sys.version, executable=sys.executable,
             address=server.server_address)
        self.thread.start()

    def sample(self):
        judge = self.app.judge
        with self.server.tracking_lock:
            requests = [dict(value, age_s=time.monotonic()-value["started"])
                        for value in self.server.active_requests.values()]
        proc = psutil.Process()
        emit("sample", process=process_info(proc), available_memory=psutil.virtual_memory().available,
             system_cpu=psutil.cpu_times()._asdict(),
             children=[process_info(p) for p in proc.children(recursive=True)],
             requests=requests, queue=judge.queue.qsize(),
             worker_alive=bool(judge.thread and judge.thread.is_alive()),
             checkers_ready=judge.checkers_ready.is_set(),
             threads=[dict(name=t.name, ident=t.ident) for t in threading.enumerate()])
        if any(r["age_s"] > self.interval * 2 for r in requests) or (
                judge.queue.qsize() and judge.thread and not judge.thread.is_alive()):
            emit("stacks", stacks={str(tid): traceback.format_stack(frame)
                                    for tid, frame in sys._current_frames().items()})

    def loop(self):
        while not self.stop.is_set():
            try:
                self.sample()
                if self.stop_file.is_file():
                    emit("shutdown_requested")
                    self.server.shutdown()
                    return
            except Exception as exc:
                emit("sample_error", error=repr(exc))
            self.stop.wait(self.interval)

    def close(self):
        global _sink
        self.stop.set()
        self.thread.join(timeout=5)
        emit("monitor_stop")
        _sink = None
        self.log.removeHandler(self.handler)
        self.handler.close()
