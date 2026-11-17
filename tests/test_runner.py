import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import psutil
from backend.runner import run


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="runner space ")
        self.root = Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def run_python(self, source, **kwargs):
        file = self.root / "program.py"; file.write_text(source)
        return run([sys.executable, "-I", str(file)], self.root, self.root / "stdout", self.root / "stderr", **kwargs)

    def test_timeout_and_tree_cleanup(self):
        result = self.run_python("import subprocess,sys,time\np=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)'])\nopen('child.pid','w').write(str(p.pid))\ntime.sleep(120)", timeout_ms=800, memory_mb=256)
        self.assertEqual(result.verdict, "TLE")
        pid = int((self.root / "child.pid").read_text())
        self.assertFalse(psutil.pid_exists(pid))

    def test_root_exit_cleans_surviving_child(self):
        result = self.run_python("import subprocess,sys,time\np=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)'])\nopen('child.pid','w').write(str(p.pid))\ntime.sleep(.1)", timeout_ms=2000, memory_mb=256)
        self.assertEqual(result.verdict, "OK")
        self.assertFalse(psutil.pid_exists(int((self.root / "child.pid").read_text())))

    def test_memory_and_output_limits(self):
        result = self.run_python("import time\na=bytearray(128*1024*1024)\ntime.sleep(3)", timeout_ms=3000, memory_mb=64)
        self.assertEqual(result.verdict, "MLE")
        result = self.run_python("import sys\nsys.stdout.write('x'*1000000)", timeout_ms=3000, memory_mb=128, output_limit=10000)
        self.assertEqual(result.verdict, "OLE")

    def test_cancellation_and_runtime_error(self):
        stopped = threading.Event(); stopped.set()
        result = self.run_python("import time;time.sleep(120)", stop=stopped, timeout_ms=1000)
        self.assertEqual(result.verdict, "Cancelled")
        result = self.run_python("raise RuntimeError('controlled')", timeout_ms=3000)
        self.assertEqual(result.verdict, "RE")

    def test_scheduler_pause_after_poll_does_not_turn_finished_program_into_tle(self):
        real_popen = subprocess.Popen

        def delayed_popen(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            real_poll = process.poll
            delayed = False

            def poll():
                nonlocal delayed
                code = real_poll()
                if not delayed and code is None:
                    delayed = True
                    # Simulate the monitoring thread being descheduled after
                    # observing a live process. The child exits during the gap.
                    process.wait(timeout=3)
                    threading.Event().wait(0.25)
                return code

            process.poll = poll
            return process

        with patch("backend.runner.subprocess.Popen", side_effect=delayed_popen):
            result = self.run_python("pass", timeout_ms=200)
        self.assertEqual(result.verdict, "OK")


@unittest.skipUnless(os.name == "nt" and shutil.which("g++"), "Windows Job regression tests require GCC")
class WindowsJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="native job space ")
        cls.root = Path(cls.temp.name)
        cls.binary = cls.root / "program.exe"
        source = cls.root / "program.cpp"
        source.write_text(r'''
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <string>
int main(int argc, char** argv) {
    if (argc < 2) return 0;
    if (!std::strcmp(argv[1], "memory")) {
        volatile char* p = new char[40*1024*1024];
        for (int i=0; i<40*1024*1024; ++i) p[i] = 1;
        Sleep(120000); return 0;
    }
    if (!std::strcmp(argv[1], "sleep")) { Sleep(120000); return 0; }
    int count = !std::strcmp(argv[1], "many") ? 20 : 2;
    FILE* file = std::fopen("children.pid", "w");
    for (int i=0; i<count; ++i) {
        std::string command = std::string("\"") + argv[0] + "\" " + (count == 2 ? "memory" : "sleep");
        STARTUPINFOA si = {}; si.cb = sizeof(si);
        PROCESS_INFORMATION pi = {};
        if (!CreateProcessA(nullptr, command.data(), nullptr, nullptr, FALSE,
                            CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi)) return 1;
        std::fprintf(file, "%lu\n", pi.dwProcessId);
        CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    }
    std::fclose(file);
    Sleep(count == 2 ? 120000 : 100); return 0;
}
''')
        try:
            subprocess.run([shutil.which("g++"), "-O2", str(source), "-o", str(cls.binary)], check=True, capture_output=True)
        except Exception:
            cls.temp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def execute(self, *args, **kwargs):
        return run([str(self.binary), *args], self.root, self.root / "stdout", self.root / "stderr", **kwargs)

    def assert_children_gone(self):
        for pid in (self.root / "children.pid").read_text().splitlines():
            self.assertFalse(psutil.pid_exists(int(pid)))

    def test_job_members_grow_and_cleanup_after_root_exit(self):
        result = self.execute("many", timeout_ms=10000, memory_mb=1024)
        self.assertEqual(result.verdict, "OK")
        self.assertEqual(len((self.root / "children.pid").read_text().splitlines()), 20)
        self.assert_children_gone()

    def test_aggregate_child_memory(self):
        result = self.execute("spawn", timeout_ms=10000, memory_mb=64)
        self.assertEqual(result.verdict, "MLE")
        self.assert_children_gone()
