"""Browser regression for numbered and unnumbered Markdown sample pairs."""
import argparse
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


def fixture(page, markdown, pid):
    page.evaluate("({text, pid}) => document.querySelector('#content').replaceChildren(renderMarkdown(text, pid))",
                  {'text': markdown, 'pid': pid})


def fence(kind, value):
    return f'```{kind}\n{value}\n```\n\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'docs/fixtures/sample-pairs.json')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    output = ROOT / config['output']
    output.mkdir(parents=True, exist_ok=True)
    report = {'success': False, 'checks': [], 'problems': [], 'pageErrors': []}
    with tempfile.TemporaryDirectory(prefix='state-', dir=output) as data:
        app = App(ROOT / config['problems'], ROOT / config['history'], Path(data), start_worker=False)
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
                report['checks'].append(f'All {len(app.problems)} statements preserve sample order and text')
                display = config['display_problem']
                sample_count = sum(c.group == 'sample' for c in app.problems[display].cases)
                page.goto(url + f'#problem/{display}')
                expect(page.locator('#statement .samples')).to_have_count(sample_count)
                page.evaluate('navigator.clipboard.writeText = async text => { window.copiedSample = text; }')
                for button, item in zip(page.locator('#statement .copy-button').all(), [b for g in groups(page) for b in g]):
                    button.click()
                    assert page.evaluate('window.copiedSample') == item['text']
                page.screenshot(path=str(output / 'samples-desktop.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                expect(page.locator('#statement .samples')).to_have_count(sample_count)
                assert all(len(group) == 2 for group in groups(page))
                page.screenshot(path=str(output / 'samples-mobile.png'), full_page=True)
                report['checks'].append('Desktop/mobile pairing and copy buttons preserve exact text')
                for case in config['fixtures']:
                    fixture(page, ''.join(fence(kind, value) for kind, value in case['blocks']), display)
                    assert groups(page) == [pair(label, source, answer) for label, source, answer in case['expected']]
                report['checks'].append('Unnumbered batches, out-of-order numbered blocks, and mixed fences pair without merging')
                reference = app.problems[config['reference_problem']]
                fixture(page, reference.statement, reference.id)
                actual = groups(page)
                reference_samples = [c for c in reference.cases if c.group == 'sample']
                assert len(actual) == len(reference_samples) and all(len(group) == 2 for group in actual)
                assert actual[0][0]['text'] == reference_samples[0].input.read_text(encoding='utf-8')
                assert not report['pageErrors']
                report['checks'].append('Reference statement retains numbered sample pairs and unchanged copy text')
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
