"""Browser regression for numbered and unnumbered Markdown sample pairs."""
import json
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.contest import App
from backend.server import Server
from playwright.sync_api import sync_playwright, expect


def groups(page):
    return page.locator('.samples').evaluate_all('''nodes => nodes.map(group =>
        Array.from(group.children).map(block => ({
            label: block.querySelector('.sample-head span').textContent,
            text: block.querySelector('pre code').textContent
        })))''')


def pair(label, source, answer):
    return [{'label': f'input {label}', 'text': source}, {'label': f'output {label}', 'text': answer}]


def fixture(page, markdown):
    page.evaluate("text => document.querySelector('#content').replaceChildren(renderMarkdown(text, 'B'))", markdown)


def fence(kind, value):
    return f'```{kind}\n{value}\n```\n\n'


def main():
    output = ROOT / 'tmp/sample-acceptance'
    output.mkdir(parents=True, exist_ok=True)
    workspace = ROOT / 'uestc-school-contest-prelimery/ccpc-local'
    report = {'success': False, 'checks': [], 'problems': [], 'pageErrors': []}
    with tempfile.TemporaryDirectory(prefix='state-', dir=output) as data:
        app = App(workspace / 'problems', workspace / 'contest.txt', Path(data), start_worker=False)
        server = Server(('127.0.0.1', 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.on('pageerror', lambda error: report['pageErrors'].append(str(error)))
                url = f'http://127.0.0.1:{server.server_port}/'
                page.goto(url)
                expect(page.locator('#vp-name')).to_be_visible()
                for pid, problem in app.problems.items():
                    page.goto(url + f'#problem/{pid}')
                    expect(page.locator('#statement')).to_be_visible()
                    cases = [case for case in problem.cases if case.group == 'sample']
                    expected = [pair(i, c.input.read_text(encoding='utf-8').rstrip() + '\n',
                                     c.answer.read_text(encoding='utf-8').rstrip() + '\n')
                                for i, c in enumerate(cases, 1)]
                    assert groups(page) == expected, pid
                    assert page.locator('#statement h3').evaluate_all(r'''nodes => nodes.filter(n =>
                        /^样例 \d+$/.test(n.textContent)).every(n => n.nextElementSibling.classList.contains('samples'))''')
                    report['problems'].append({'id': pid, 'samplePairs': len(cases), 'success': True})
                report['checks'].append('All 16 UESTC statements: one input/output pair under each sample heading, original order and text')
                page.goto(url + '#problem/B')
                expect(page.locator('#statement .samples')).to_have_count(2)
                page.evaluate('navigator.clipboard.writeText = async text => { window.copiedSample = text; }')
                for button, item in zip(page.locator('#statement .copy-button').all(), [b for g in groups(page) for b in g]):
                    button.click()
                    assert page.evaluate('window.copiedSample') == item['text']
                page.screenshot(path=str(output / 'uestc-B-desktop.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                expect(page.locator('#statement .samples')).to_have_count(2)
                assert [len(group) for group in groups(page)] == [2, 2]
                page.screenshot(path=str(output / 'uestc-B-mobile.png'), full_page=True)
                report['checks'].append('Screenshot B regression: desktop/mobile pairing and all four copy buttons preserve exact text')
                fixture(page, fence('input', 'a') + fence('input', 'b') + fence('output', 'A') + fence('output', 'B'))
                assert groups(page) == [pair(1, 'a\n', 'A\n'), pair(2, 'b\n', 'B\n')]
                fixture(page, fence('output2', 'B') + fence('input1', 'a') + fence('input2', 'b') + fence('output1', 'A'))
                assert groups(page) == [pair(2, 'b\n', 'B\n'), pair(1, 'a\n', 'A\n')]
                fixture(page, fence('input3', 'c') + fence('output3', 'C') + fence('input', 'a') + fence('output', 'A') +
                        fence('input1', 'd') + fence('output1', 'D') + fence('input', 'b') + fence('output', 'B'))
                assert groups(page) == [pair(3, 'c\n', 'C\n'), pair(2, 'a\n', 'A\n'),
                                        pair(1, 'd\n', 'D\n'), pair(4, 'b\n', 'B\n')]
                report['checks'].append('Unnumbered batches, out-of-order numbered blocks, and mixed fences pair without merging')
                reference = ROOT / 'tests/ICPC-Shaanxi-2025-National-Invitational-Contest/L'
                fixture(page, (reference / 'docs/statement.md').read_text(encoding='utf-8'))
                actual = groups(page)
                assert len(actual) == 5 and all(len(group) == 2 for group in actual)
                assert actual[0][0]['text'] == (reference / 'exported-tests/sample/sample.in').read_text(encoding='utf-8')
                assert not report['pageErrors']
                report['checks'].append('Existing Shaanxi L statement retains five numbered sample pairs and unchanged copy text')
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
