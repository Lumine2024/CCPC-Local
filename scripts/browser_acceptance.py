"""Playwright acceptance of the actual launcher and UI, including screenshots."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright, expect

OUTPUT = ROOT / "tmp" / "browser-acceptance"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    log = OUTPUT / "launcher.log"
    command = [sys.executable, str(ROOT / "launcher.py"), "--problem-list",
               str(ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest"),
               "--submissions", str(ROOT / "tests/contest.txt"), "--port", "0", "--no-browser",
               "--data-dir", str(OUTPUT / f"state-{int(time.time())}")]
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=stream, cwd=ROOT,
                                   env=os.environ | {"PYTHONIOENCODING": "utf-8"},
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
    report = {"success": False, "checks": [], "console_errors": []}
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            output = log.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"http://127\.0\.0\.1:\d+/", output)
            if match:
                break
            if process.poll() is not None:
                raise RuntimeError(output)
            time.sleep(0.3)
        else:
            raise RuntimeError("Launcher readiness timeout")
        url = match.group(0)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, permissions=["clipboard-read", "clipboard-write"])
            external = []
            def network(route):
                if route.request.url.startswith(url): route.continue_()
                else: external.append(route.request.url); route.abort()
            context.route("**/*", network)
            page = context.new_page()
            page.on("pageerror", lambda error: report["console_errors"].append(str(error)))
            page.on("console", lambda message: report["console_errors"].append(message.text) if message.type == "error" else None)
            page.goto(url)
            expect(page.locator("#vp-name")).to_be_visible()
            expect(page.locator("#content tbody tr")).to_have_count(13)
            assert page.locator(".problem-stats.hidden-count").count() == 13
            page.screenshot(path=str(OUTPUT / "01-home-desktop.png"), full_page=True)
            page.fill("#vp-name", "验收 VP 队伍")
            page.get_by_role("button", name="开始 VP", exact=True).click()
            expect(page.locator(".vp-panel")).to_contain_text("验收 VP 队伍")
            state = page.evaluate("async()=>await (await fetch('/api/state')).json()")
            session_id = state["session"]["id"]
            report["checks"].append("Launcher, lobby masking, VP start")
            page.goto(url + "#problem/L")
            expect(page.locator(".samples")).to_have_count(5)
            expect(page.locator(".katex").first).to_be_visible()
            page.evaluate("()=>{const write=navigator.clipboard.writeText.bind(navigator.clipboard);navigator.clipboard.writeText=async text=>{window.copiedText=text;return write(text);};}")
            page.locator(".copy-button").first.click()
            clipboard = page.evaluate("navigator.clipboard.readText()")
            expected = (ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest/L/exported-tests/sample/sample.in").read_text()
            assert page.evaluate("window.copiedText") == expected
            # Windows clipboard storage normalizes LF to CRLF; the content
            # passed to writeText above remains byte-for-byte sample text.
            assert clipboard.replace("\r\n", "\n") == expected
            page.screenshot(path=str(OUTPUT / "02-problem-desktop.png"), full_page=True)
            report["checks"].append("Offline Markdown, LaTeX, five sample pairs, exact copy")
            for pid in ("D", "I"):
                page.goto(url + f"#problem/{pid}")
                expect(page.locator("#statement img")).to_be_visible()
                expect(page.locator("#statement img")).to_have_attribute("src", re.compile(f"/api/problems/{pid}/assets/"))
                page.wait_for_function("()=>document.querySelector('#statement img')?.naturalWidth > 0")
            report["checks"].append("D and I relative illustration assets")
            page.goto(url + "#submit/L")
            expect(page.locator("#source-code")).to_be_visible()
            expect(page.locator("#submit-problem")).to_have_value("L")
            source = ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest/L/src/solution.cpp"
            page.set_input_files("#source-file", str(source))
            expect(page.locator("#source-code")).to_have_value(source.read_text())
            page.get_by_role("button", name="提交代码", exact=True).click()
            expect(page.locator("#content .verdict")).to_have_text("AC", timeout=120000)
            page.screenshot(path=str(OUTPUT / "03-submission-desktop.png"), full_page=True)
            state = page.evaluate("async()=>await (await fetch('/api/state')).json()")
            assert state["submissions"][0]["verdict"] == "AC"
            assert "time_ms" not in state["submissions"][0] and "memory_kb" not in state["submissions"][0]
            report["checks"].append("Uploaded C++ main solution: 38 cases, real AC, no runtime or memory API fields")
            page.goto(url + "#submissions")
            expect(page.locator(".submission-table")).to_be_visible()
            assert not page.get_by_role("columnheader", name="耗时", exact=True).count()
            page.reload()
            page.wait_for_function("()=>document.querySelector('.submission-table') !== null")
            restored = page.evaluate("async()=>await (await fetch('/api/state')).json()")
            assert restored["session"]["id"] == session_id
            page.goto(url + "#board")
            expect(page.locator("#my-team")).to_be_attached()
            assert page.locator("#my-team").inner_text().find("其他1题") >= 0
            page.fill("#team-filter", "验收")
            page.wait_for_timeout(4500)
            expect(page.locator("#team-filter")).to_be_focused()
            expect(page.locator("#team-filter")).to_have_value("验收")
            page.get_by_role("button", name="定位我的队伍").click()
            page.screenshot(path=str(OUTPUT / "04-board-desktop.png"))
            report["checks"].append("Refresh preserves session, hidden AC aggregated into Other, locate team")
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(url + "#problems")
            expect(page.locator("#content tbody tr")).to_have_count(13)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.screenshot(path=str(OUTPUT / "05-home-mobile.png"), full_page=True)
            page.goto(url + "#board")
            expect(page.locator("#board-table")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.screenshot(path=str(OUTPUT / "06-board-mobile.png"))
            report["checks"].append("390px mobile home and board: no document overflow")
            assert not external, external
            assert not report["console_errors"], report["console_errors"]
            report["checks"].append("Only loopback network requests; no browser console errors")
            browser.close()
        report["success"] = True
    finally:
        if process.poll() is None:
            if os.name == "nt": process.send_signal(signal.CTRL_BREAK_EVENT)
            else: process.send_signal(signal.SIGINT)
            try: process.wait(timeout=20)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        (OUTPUT / "browser-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
