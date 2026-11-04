"""Check all configured main solutions through the production CCPC Local judge."""
import argparse
from dataclasses import asdict
import hashlib
from http.cookiejar import CookieJar
import json
from pathlib import Path
import sys
import threading
from urllib.request import build_opener, HTTPCookieProcessor, Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.contest import App
from backend.judge import Judge
from backend.problems import load_problems
from backend.server import Server


def verify_http(app):
    server = Server(('127.0.0.1', 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    checks = []
    try:
        def get(path):
            with opener.open(url + path, timeout=10) as response:
                checks.append({'path': path, 'status': response.status})
                return response.read()
        assert b'<html' in get('/').lower()
        state = json.loads(get('/api/state'))
        request = Request(url + '/api/vp', data=json.dumps({'name': 'HTTP import acceptance'}).encode(),
                          headers={'Content-Type': 'application/json', 'X-CSRF-Token': state['csrf']}, method='POST')
        with opener.open(request, timeout=10) as response:
            assert response.status == 200
            checks.append({'path': '/api/vp', 'status': response.status})
        for pid, problem in app.problems.items():
            assert json.loads(get(f'/api/problems/{pid}'))
            for reference, asset in problem.assets.items():
                body = get(f'/api/problems/{pid}/assets/{reference}')
                assert hashlib.sha256(body).digest() == hashlib.sha256(asset.read_bytes()).digest()
        return {'success': True, 'checks': checks}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    problems, digest = load_problems(args.workspace / 'problems')
    app = App(args.workspace / 'problems', args.workspace / 'contest.txt', args.output / 'app', start_worker=False)
    try:
        session = app.start('acceptance', 'Import acceptance')
        state = app.state('acceptance', session['id'])
        if len(state['problems']) != len(problems):
            raise ValueError('App did not expose all imported problems')
        team_count = len(app.contest.teams)
        history_count = len(app.contest.events)
        http_checks = verify_http(app)
    finally:
        app.close()
    report = {'success': False, 'inputDigest': digest, 'problemCount': len(problems),
              'caseCount': sum(len(p.cases) for p in problems.values()), 'teamCount': team_count,
              'historyCount': history_count, 'http': http_checks, 'results': []}
    judge = Judge(problems, args.output / 'judge')
    judge.prepare_checkers()
    for pid, p in problems.items():
        main = next((s for s in p.config.get('solutions', []) if s.get('role') == 'main'), None)
        if main is None:
            raise ValueError(f'{pid}: main solution is not available for verification')
        source = (p.root / main['path']).read_text(encoding='utf-8-sig')
        result = judge.evaluate(pid, source, main['language'], f'{pid}-main')
        good = result.verdict == 'AC' and result.checked == len(p.cases)
        report['results'].append({'problem': pid, 'caseCount': len(p.cases), 'passed': good, **asdict(result)})
        (args.output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'{pid}: {result.verdict} {result.checked}/{len(p.cases)}', flush=True)
    _, after = load_problems(args.workspace / 'problems')
    first_pid = next(iter(problems))
    negative = judge.evaluate(first_pid, 'int main() { return 0; }', 'cpp', 'empty-output-probe')
    report['negativeProbe'] = {'problem': first_pid, 'expected': 'WA', **asdict(negative)}
    report['inputDigestAfter'] = after
    report['success'] = all(r['passed'] for r in report['results']) and digest == after and negative.verdict == 'WA'
    (args.output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
