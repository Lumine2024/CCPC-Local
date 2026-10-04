"""Browser verification of real history with an injected server clock only.

No synthetic verdicts and no production clock-control endpoint are used.
"""
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.contest import App
from backend.server import Server
from playwright.sync_api import sync_playwright, expect


def main():
    output = ROOT / "tmp/phase-acceptance"
    output.mkdir(parents=True, exist_ok=True)
    now = [time.time()]
    app = App(ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest", ROOT / "tests/contest.txt",
              output / f"state-{int(now[0])}", clock=lambda: now[0], start_worker=False)
    server = Server(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    report = {"success": False, "injected_clock": True, "synthetic_verdicts": False, "checks": []}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(url); expect(page.locator("#vp-name")).to_be_visible()
            page.fill("#vp-name", "历史回放验收")
            page.get_by_role("button", name="开始 VP", exact=True).click()
            expect(page.locator(".vp-panel")).to_contain_text("历史回放验收")
            get_state = "async()=>await (await fetch('/api/state')).json()"
            first = page.evaluate(get_state); sid = first["session"]["id"]
            now[0] = first["session"]["started"] + 7200
            page.reload(); expect(page.locator("#elapsed-clock")).to_have_text("02:00:00")
            two = page.evaluate(get_state)
            assert two["board"]["visible"] == ["A", "G", "L"]
            assert two["board"]["counts"]["B"] is None
            page.screenshot(path=str(output / "07-two-hour-home.png"), full_page=True)
            report["checks"].append("2h real replay: only A/G/L pass threshold; other counts remain null")
            now[0] = first["session"]["started"] + 14400
            page.goto(url + "#board"); page.reload()
            expect(page.locator("#nav-phase")).to_have_text("四小时封榜")
            expect(page.locator(".board th")).to_have_count(17)
            four = page.evaluate(get_state)
            expected = dict(zip("ABCDEFGHIJKLM", [290,6,0,0,1,2,253,0,182,108,14,386,83]))
            assert four["board"]["counts"] == expected
            page.screenshot(path=str(output / "08-four-hour-board.png"))
            report["checks"].append("4h all 13 columns public; counts match independent baseline")
            now[0] = first["session"]["started"] + 15000
            page.reload(); expect(page.locator("#elapsed-clock")).to_have_text("04:10:00")
            later = page.evaluate(get_state)
            assert later["board"]["rows"] == four["board"]["rows"]
            assert later["board"]["counts"] == four["board"]["counts"]
            page.goto(url + "#submit/L")
            expect(page.locator("#send-code")).to_be_enabled()
            report["checks"].append("4h10m public rows frozen; submission form still enabled")
            now[0] = first["session"]["started"] + 18000
            page.reload(); expect(page.locator("#send-code")).to_be_disabled()
            page.goto(url + "#final")
            expect(page.locator("#content .panel-title")).to_contain_text("最终结果")
            final = page.evaluate("async()=>await (await fetch('/api/state?final=1')).json()")
            assert final["board"]["counts"] == dict(zip("ABCDEFGHIJKLM", [327,9,0,1,2,5,294,0,245,156,46,387,123]))
            page.screenshot(path=str(output / "09-final-board.png"))
            report["checks"].append("5h submissions disabled; explicit final result excludes 186 out-of-range events")
            page.get_by_role("button", name="重新 VP", exact=True).click()
            expect(page.locator("#nav-phase")).to_have_text("比赛进行中")
            new = page.evaluate(get_state)
            assert new["session"]["id"] != sid
            assert len(new["sessions"]) == 2
            page.select_option("#session-select", sid)
            expect(page.locator("#nav-phase")).to_have_text("比赛已结束")
            report["checks"].append("New VP and archive selector preserve previous session")
            browser.close()
        report["success"] = True
    finally:
        server.shutdown(); server.server_close(); thread.join(); app.close()
        (output / "phase-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
