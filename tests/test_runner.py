import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

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
