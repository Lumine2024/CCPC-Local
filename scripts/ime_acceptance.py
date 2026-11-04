"""Browser regression for VP caret stability and Chinese IME composition.

Chromium's native composition events are driven with CDP. This checks the
browser behavior shared by IMEs; it does not automate the installed Sogou UI.
"""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.contest import App
from backend.server import Server
from playwright.sync_api import sync_playwright, expect


def main():
    output = ROOT / 'tmp/ime-acceptance'
    output.mkdir(parents=True, exist_ok=True)
    report = {'success': False, 'nativeCompositionViaCDP': True,
              'sogouUIAutomated': False, 'checks': [], 'pageErrors': []}
    now = [time.time()]
    with tempfile.TemporaryDirectory(prefix='state-', dir=output) as data:
        app = App(ROOT / 'tests/ICPC-Shaanxi-2025-National-Invitational-Contest', ROOT / 'tests/contest.txt',
                  Path(data), clock=lambda: now[0], start_worker=False)
        server = Server(('127.0.0.1', 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()
                page.on('pageerror', lambda error: report['pageErrors'].append(str(error)))
                posts = []
                page.on('request', lambda request: posts.append(request.post_data_json)
                        if request.method == 'POST' and request.url.endswith('/api/vp') else None)
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                expect(page.locator('#vp-name')).to_be_visible()
                page.fill('#vp-name', '中文队伍名称')
                page.evaluate('''() => {
                    window.vpInput = document.querySelector('#vp-name');
                    window.vpPanel = vpInput.closest('.vp-panel');
                    vpInput.setSelectionRange(1, 4, 'backward');
                }''')
                page.evaluate('''async () => { for (let i = 0; i < 4; i++) await refresh(); }''')
                assert page.evaluate('''() => vpInput === document.querySelector('#vp-name') &&
                    vpPanel === document.querySelector('.vp-panel') && document.activeElement === vpInput &&
                    vpInput.value === '中文队伍名称' && vpInput.selectionStart === 1 &&
                    vpInput.selectionEnd === 4 && vpInput.selectionDirection === 'backward' ''')
                report['checks'].append('Four state refreshes preserve input, ancestors, focus, text and selection')
                page.fill('#vp-name', '')
                page.evaluate('document.querySelector("#vp-name").blur()')
                page.evaluate('refresh()')
                expect(page.locator('#vp-name')).to_have_value('')
                report['checks'].append('An empty draft remains empty after blur and refresh')
                page.focus('#vp-name')
                page.evaluate('''() => {
                    window.compositionEvents = [];
                    vpInput.addEventListener('compositionstart', () => compositionEvents.push('start'));
                    vpInput.addEventListener('compositionend', () => compositionEvents.push('end'));
                }''')
                cdp = page.context.new_cdp_session(page)
                cdp.send('Input.imeSetComposition', {'text': 'zhongwen', 'selectionStart': 8, 'selectionEnd': 8})
                assert page.evaluate('compositionEvents.join(",")') == 'start'
                # Hold native composition across both explicit and actual 4s polling.
                page.evaluate('''async () => { for (let i = 0; i < 3; i++) await refresh(); }''')
                page.wait_for_timeout(4500)
                assert page.evaluate('''() => compositionEvents.join(',') === 'start' &&
                    document.querySelector('#vp-name') === vpInput && vpInput.value === 'zhongwen' &&
                    document.activeElement === vpInput && vpInput.selectionStart === 8''')
                page.press('#vp-name', 'Enter')
                assert not posts
                expect(page.locator('#vp-name')).to_be_visible()
                report['checks'].append('Native preedit survives automatic polling; candidate Enter does not start VP')
                cdp.send('Input.insertText', {'text': '中文队伍'})
                expect(page.locator('#vp-name')).to_have_value('中文队伍')
                assert page.evaluate('compositionEvents.join(",")') == 'start,end'
                assert page.evaluate('''() => {
                    const event = new KeyboardEvent('keydown', {
                        key: 'Enter', keyCode: 229, bubbles: true, cancelable: true
                    });
                    vpInput.dispatchEvent(event);
                    return event.defaultPrevented;
                }''')
                page.evaluate('refresh()')
                page.press('#vp-name', 'Enter')
                expect(page.locator('.vp-panel')).to_contain_text('中文队伍')
                expect(page.locator('#vp-name')).to_have_count(0)
                assert posts == [{'name': '中文队伍'}], posts
                report['checks'].append('IME commit is complete; code 229 is guarded; ordinary Enter submits once')
                current = page.evaluate("async () => (await (await fetch('/api/state')).json())")
                now[0] = current['session']['started'] + app.contest.duration
                page.evaluate('refresh()')
                expect(page.get_by_role('button', name='重新 VP', exact=True)).to_be_visible()
                page.fill('#vp-name', '新的中文队伍')
                page.evaluate('''async () => { for (let i = 0; i < 3; i++) await refresh(); }''')
                page.get_by_role('button', name='重新 VP', exact=True).click()
                expect(page.locator('.vp-panel')).to_contain_text('新的中文队伍')
                expect(page.locator('#session-select option')).to_have_count(2)
                assert len(posts) == 2
                assert not report['pageErrors']
                report['checks'].append('Ended VP changes panel normally; restarted VP and archives work without duplicate listeners')
                report['success'] = True
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            app.close()
            (output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
