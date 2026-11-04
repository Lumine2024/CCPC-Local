"""Export a standings snapshot with optional explicitly estimated RJ events.

This is not a submission-log importer. It preserves raw cells, colors, merges,
unresolved records and minute precision. --rj-distribution reconstructs failed
attempt times from reported attempt counts; none preserves AC-only export.
Each team's earliest recognizable AC estimates the first submission; its start
is that minute minus --warmup-minutes. Only [0, --window-minutes) is exported.
Use a layout JSON for OCR-derived workbooks with missing/misrecognized headers.
"""
import argparse
from bisect import bisect_left
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.contest_parser import parse_contest
from backend.problems import load_problems


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def column_number(name):
    if not re.fullmatch(r"[A-Z]+", name):
        raise ValueError(f"Invalid XLSX column: {name}")
    number = 0
    for letter in name:
        number = number * 26 + ord(letter) - 64
    return number


def cell_position(address):
    match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", address)
    if not match:
        raise ValueError(f"Invalid XLSX address: {address}")
    return column_number(match[1]), int(match[2])


def read_workbook(path, sheet_name=None):
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(t.text or "" for t in e.findall('.//{*}t'))
                      for e in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        book = ET.fromstring(z.read("xl/workbook.xml"))
        sheets = book.findall('{*}sheets/{*}sheet')
        if sheet_name is None and len(sheets) != 1:
            raise ValueError("Workbook has multiple sheets; select --sheet")
        sheet = next((s for s in sheets if sheet_name is None or s.get('name') == sheet_name), None)
        if sheet is None:
            raise ValueError(f"Sheet not found: {sheet_name}")
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rid = next(v for k, v in sheet.attrib.items() if k.endswith('}id'))
        target = next(r.get('Target') for r in rels if r.get('Id') == rid)
        target = target.lstrip('/') if target.startswith('/') else str(PurePosixPath('xl') / target)
        if '..' in PurePosixPath(target).parts:
            raise ValueError('Unsafe worksheet relationship')
        doc = ET.fromstring(z.read(target))
        styles = ET.fromstring(z.read('xl/styles.xml'))
        xfs, fills = styles.find('{*}cellXfs'), styles.find('{*}fills')
        rows = []
        for row in doc.findall('.//{*}sheetData/{*}row'):
            cells = []
            for c in row.findall('{*}c'):
                value = c.findtext('{*}v', '') or ''
                if c.get('t') == 's' and value:
                    value = shared[int(value)]
                elif c.get('t') == 'inlineStr':
                    value = ''.join(t.text or '' for t in c.findall('.//{*}t'))
                fill = fills[int(xfs[int(c.get('s', '0'))].get('fillId', '0'))]
                color = fill.find('{*}patternFill/{*}fgColor')
                rgb = color.get('rgb', '')[-6:].upper() if color is not None else ''
                cells.append({'cell': c.get('r'), 'value': value, 'style': int(c.get('s', '0')), 'fill': rgb,
                              'formula': c.findtext('{*}f')})
            rows.append({'row': int(row.get('r')), 'cells': cells})
        merges = [m.get('ref') for m in doc.findall('.//{*}mergeCell')]
        return {'sheet': sheet.get('name'), 'rows': rows, 'merges': merges}


def accepted_minute(value):
    # Whole-cell match: never scrape a number out of merged/noisy OCR text.
    match = re.fullmatch(r'\s*(\d+)\s*(?:\n\s*(?:(\d+)\s*)?tr(?:y|ies))?\s*', value, re.I)
    return (int(match[1]), int(match[2]) if match[2] else None) if match else None


def normalize_ac(records, warmup=20, window=300):
    if not records:
        return None, []
    first = min(r['acceptedMinute'] for r in records)
    start = first - warmup
    normalized = []
    for record in records:
        item = dict(record)
        item['elapsedSeconds'] = (item['acceptedMinute'] - start) * 60
        item['withinWindow'] = 0 <= item['elapsedSeconds'] < window * 60
        normalized.append(item)
    return start, normalized


def rejected_count(value):
    match = re.fullmatch(r'\s*(\d+)\s*tr(?:y|ies)\s*', value, re.I)
    return int(match[1]) if match and int(match[1]) > 0 else None


def insert_times(x, y, count, distribution='uniform'):
    """Integer seconds, ordered before AC even when the interval is tiny."""
    if count < 0 or y < x or x < 0 or distribution not in {'uniform', 'exponential'}:
        raise ValueError('Invalid RJ interpolation parameters')
    times = []
    for i in range(1, count + 1):
        fraction = i / (count + 1)
        if distribution == 'exponential':
            fraction = math.expm1(3 * fraction) / math.expm1(3)
        # A zero-second AC permits same-second RJ; source order then determines
        # penalty. Otherwise the RJ must be strictly earlier than that AC.
        times.append(max(0, min(y - 1, x + int((y - x) * fraction))))
    return times


def reconstruct_events(accepted, rejected, playable, window=300, distribution='none'):
    if window <= 0 or distribution not in {'none', 'uniform', 'exponential'}:
        raise ValueError('Invalid reconstruction policy')
    events, unknown = [], []
    prior_times = sorted({r['elapsedSeconds'] for r in accepted})
    for record in accepted:
        if record['problem'] not in playable:
            continue
        y = record['elapsedSeconds']
        tries = record.get('reportedTries')
        good_count = type(tries) is int and tries > 0
        if distribution != 'none':
            if not good_count:
                unknown.append({'problem': record['problem'], 'reason': 'accepted-attempt-count-unknown'})
            else:
                position = bisect_left(prior_times, y)
                x = prior_times[position - 1] if position else 0
                for attempt, at in enumerate(insert_times(x, y, tries - 1, distribution), 1):
                    events.append({'problem': record['problem'], 'attempt': attempt, 'at': at, 'verdict': 'RJ',
                                   'syntheticTime': True, 'basis': f'{distribution}-between-previous-AC-and-current-AC',
                                   'intervalStartSeconds': x, 'intervalEndSeconds': y})
        events.append({'problem': record['problem'], 'attempt': tries if good_count and distribution != 'none' else 1,
                       'at': y, 'verdict': 'AC', 'syntheticTime': False, 'basis': 'reported-AC-minute'})
    if distribution != 'none':
        for record in rejected:
            if record['problem'] not in playable:
                continue
            tries = record.get('reportedTries')
            if type(tries) is not int or tries < 1:
                unknown.append({'problem': record['problem'], 'reason': 'rejected-attempt-count-unknown'})
                continue
            at = record.get('elapsedSeconds')
            if at is None:
                at = window * 60 - 1
                basis = 'unsolved-last-RJ-unknown; piled-at-window-end'
            else:
                basis = 'unsolved-piled-at-known-last-RJ'
            events.extend({'problem': record['problem'], 'attempt': i, 'at': at, 'verdict': 'RJ',
                           'syntheticTime': True, 'basis': basis} for i in range(1, tries + 1))
    # Reconstruct first, crop second: failures on a late AC may still fall into
    # the five-hour window. Keeping all metadata makes this decision auditable.
    for event in events:
        event['withinWindow'] = 0 <= event['at'] < window * 60
    return sorted(events, key=lambda e: (e['at'], e['problem'], e['attempt'])), unknown


def infer_layout(book, pids):
    header = book['rows'][0]
    columns = {}
    for c in header['cells']:
        if c['value'] in pids:
            if c['value'] in columns:
                raise ValueError('Duplicate problem headers; provide --layout')
            columns[c['value']] = c['cell'].rstrip('0123456789')
    if set(columns) != set(pids):
        raise ValueError('Missing problem headers; provide --layout with reviewed column spans')
    names = [c['cell'].rstrip('0123456789') for c in header['cells'] if c['value'].strip().upper() == 'TEAM']
    if len(names) != 1:
        raise ValueError('Missing/ambiguous TEAM header; provide --layout')
    return {'problemColumns': columns, 'teamColumns': names, 'firstTeamRow': header['row'] + 1,
            'stopText': 'SUMMARY', 'acceptedColors': ['60E760', '1DAA1D'], 'rejectedColors': ['E87272']}


def convert(workbook, workspace, layout=None, sheet=None, source_duration=720, warmup=20, window=300, verified_ac=None,
            rj_distribution='none'):
    if source_duration <= 0 or window <= 0 or warmup < 0:
        raise ValueError('Durations must be positive and warmup nonnegative')
    if rj_distribution not in {'none', 'uniform', 'exponential'}:
        raise ValueError('Invalid reconstruction policy')
    workspace = Path(workspace).resolve()
    problems, _ = load_problems(workspace / 'problems')
    pids = set(problems)
    for folder in (workspace / 'unsupported').glob('*/config.json'):
        pids.add(folder.parent.name)
    book = read_workbook(workbook, sheet)
    layout = layout or infer_layout(book, pids)
    spans = {}
    for pid, spec in layout['problemColumns'].items():
        first, _, last = spec.partition(':')
        lo, hi = column_number(first), column_number(last or first)
        if hi < lo or pid not in pids:
            raise ValueError(f'Invalid problem span: {pid}: {spec}')
        for col in range(lo, hi + 1):
            if col in spans:
                raise ValueError('Overlapping problem column spans')
            spans[col] = pid
    if set(spans.values()) != pids:
        raise ValueError('Layout problem set differs from Polygon problem set')
    name_columns = set()
    for spec in layout['teamColumns']:
        first, _, last = spec.partition(':')
        name_columns.update(range(column_number(first), column_number(last or first) + 1))
    merge_bounds = {}
    for merge in book['merges']:
        first, _, last = merge.partition(':')
        lo, rlo = cell_position(first)
        hi, rhi = cell_position(last or first)
        merge_bounds[first] = (lo, hi, rlo, rhi)
    colors = set(layout['acceptedColors'])
    rejected_colors = set(layout.get('rejectedColors', ['E87272']))
    verified, verified_rejected = {}, {}
    if verified_ac:
        if verified_ac.get('workbookSha256') != hashlib.sha256(Path(workbook).read_bytes()).hexdigest():
            raise ValueError('PDF verification belongs to a different workbook')
        for r in verified_ac['accepted']:
            key = (r['sourceRow'], r['problem'])
            if key in verified or r['problem'] not in pids or not 0 <= r['acceptedMinute'] < source_duration:
                raise ValueError(f'Invalid/duplicate PDF verified AC: {r}')
            verified[key] = r
        for r in verified_ac.get('rejected', []):
            key = (r['sourceRow'], r['problem'])
            if key in verified_rejected or key in verified or r['problem'] not in pids:
                raise ValueError(f'Invalid/duplicate PDF rejected cell: {r}')
            verified_rejected[key] = r
    teams, unknown, events, observed, corrections = [], [], [], [], []
    audit, reconstruction_unknown = [], []
    for row in book['rows']:
        if row['row'] < layout['firstTeamRow']:
            continue
        if row['row'] in layout.get('headerRows', []) + layout.get('ignoredRows', []) or any(c['value'].strip().upper() == 'TEAM' for c in row['cells']):
            continue
        if any(c['value'].strip().upper() == layout.get('stopText', 'SUMMARY') for c in row['cells']):
            break
        names = [c['value'].strip() for c in row['cells'] if cell_position(c['cell'])[0] in name_columns and c['value'].strip()]
        name_basis = 'xlsx-team-columns'
        if not names and layout.get('mergedTeamAndRankColumn'):
            col = column_number(layout['mergedTeamAndRankColumn'])
            raw = next((c['value'] for c in row['cells'] if cell_position(c['cell'])[0] == col), '')
            parts = [p.strip() for p in raw.splitlines() if p.strip()]
            if parts:
                # Rank appears on an interior line, with the team name above it.
                # Keep a numeric team name on the first line.
                parts = parts[:1] + [p for p in parts[1:] if not p.isdigit()]
                parts[0] = re.sub(r'^\d+\s+\S{1,2}\s+', '', parts[0]) if len(parts) == 1 else parts[0]
                names = ['\n'.join(parts)]
                name_basis = 'xlsx-merged-team-rank-column; name-may-have-OCR-errors'
        if not names:
            unknown.append({'row': row['row'], 'reason': 'missing-team-name'})
            names = [f'名称未识别（源行 {row["row"]}）']
            name_basis = 'explicit-placeholder-name'
        name = ' '.join(names).replace('\r', '').replace('\n', ' | ')
        tid = f"xlsx-{row['row']:04d}"
        records, rejected_records = [], []
        for c in row['cells']:
            col, r = cell_position(c['cell'])
            if col not in spans or not c['value'].strip():
                continue
            pid = spans[col]
            bound = merge_bounds.get(c['cell'], (col, col, r, r))
            mapped = {spans.get(i) for i in range(bound[0], bound[1] + 1)}
            common = {'team': tid, 'problem': pid, 'cell': c['cell'], 'value': c['value'], 'fill': c['fill']}
            if mapped != {pid} or bound[2] != bound[3]:
                unknown.append({**common, 'reason': 'merged-across-problems-or-teams'})
                continue
            if c['fill'] in rejected_colors:
                tries = rejected_count(c['value'])
                rejected_records.append({**common, 'reportedTries': tries})
                if tries is None:
                    unknown.append({**common, 'reason': 'rejected-attempt-count-unreadable'})
                continue
            if c['fill'] not in colors:
                unknown.append({**common, 'reason': 'failed-pending-or-unrecognized-color; submission-time-unknown'})
                continue
            parsed = accepted_minute(c['value'])
            if parsed is None:
                unknown.append({**common, 'reason': 'accepted-cell-has-unreadable-minute'})
                continue
            minute, tries = parsed
            if not 0 <= minute < source_duration:
                unknown.append({**common, 'reason': 'outside-source-contest-duration'})
                continue
            records.append({**common, 'acceptedMinute': minute, 'reportedTries': tries})
        if verified_ac:
            xlsx_records = {r['problem']: r for r in records}
            records = []
            # A verified PDF is authoritative; do not retain XLSX-only green
            # cells which the source PDF did not confirm.
            for pid in sorted(pids):
                pdf_record = verified.get((row['row'], pid))
                if pdf_record:
                    xlsx_record = xlsx_records.get(pid)
                    if xlsx_record is None or xlsx_record['acceptedMinute'] != pdf_record['acceptedMinute']:
                        corrections.append({'team': tid, 'sourceRow': row['row'], 'problem': pid,
                                            'xlsxMinute': xlsx_record['acceptedMinute'] if xlsx_record else None,
                                            'pdfMinute': pdf_record['acceptedMinute'], 'pdfPage': pdf_record['pdfPage']})
                    tries = pdf_record.get('reportedTries')
                    tries = tries if tries is not None else xlsx_record.get('reportedTries') if xlsx_record else None
                    records.append({'team': tid, **pdf_record, 'reportedTries': tries})
            if 'rejected' in verified_ac:
                rejected_records = [{'team': tid, **verified_rejected[(row['row'], pid)]}
                                    for pid in sorted(pids) if (row['row'], pid) in verified_rejected]
        start, normalized = normalize_ac(records, warmup, window)
        team = {'id': tid, 'name': name, 'sourceRow': row['row'], 'estimatedStartMinute': start,
                'nameBasis': name_basis,
                'firstSubmissionProxyMinute': min((r['acceptedMinute'] for r in records), default=None),
                'startTimeBasis': 'earliest-readable-AC-minus-warmup' if records else 'unknown-no-readable-AC',
                'accepted': normalized, 'rejected': rejected_records}
        teams.append(team)
        for r in normalized:
            observed.append({'team': tid, **r})
        reconstructed, missing = reconstruct_events(normalized, rejected_records, problems, window, rj_distribution)
        audit.extend({'team': tid, **e} for e in reconstructed)
        reconstruction_unknown.extend({'team': tid, **e} for e in missing)
        events.extend({'team': tid, **e} for e in reconstructed if e['withinWindow'])
    if not teams:
        raise ValueError('No teams identified; review layout')
    if verified_ac and verified_ac.get('teamCount') != len(teams):
        raise ValueError('PDF verification team count differs from XLSX layout')
    title = json.loads((workspace / 'conversion-report.json').read_text(encoding='utf-8'))['title']
    output = workspace / 'standings'
    output.mkdir(parents=True, exist_ok=True)
    dump(output / 'workbook-cells.json', book)
    dump(output / 'standings.json', {'source': Path(workbook).name, 'sourceDurationMinutes': source_duration,
          'warmupMinutes': warmup, 'windowMinutes': window, 'rjDistribution': rj_distribution, 'layout': layout, 'teams': teams})
    dump(output / 'unresolved.json', unknown)
    dump(output / 'reconstructed-events.json', audit)
    dump(output / 'reconstruction-unresolved.json', reconstruction_unknown)
    if verified_ac:
        dump(output / 'pdf-verification.json', verified_ac)
        dump(output / 'pdf-corrections.json', corrections)
    history = workspace / 'contest.txt'
    history_label = 'AC时间近似回放' if rj_distribution == 'none' else '含近似RJ回放'
    lines = [f'@contest "{title}（每队{window / 60:g}小时·{history_label}）"', f'@contlen {window}', f'@problems {len(problems)}',
             f'@teams {len(teams)}', f'@submissions {len(events)}']
    lines += [f'@p {pid},{p.config["title"]},20,0' for pid, p in problems.items()]
    lines += [f'@t {t["id"]},0,0,{t["name"]}' for t in teams]
    lines += [f'@s {e["team"]},{e["problem"]},{e["attempt"]},{e["at"]},{"OK" if e["verdict"] == "AC" else "RJ"}'
              for e in sorted(events, key=lambda e: (e['at'], e['team'], e['problem'], e['attempt']))]
    history.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    contest = parse_contest(history)
    report = {'success': True, 'workbook': Path(workbook).name, 'workbookSha256': hashlib.sha256(Path(workbook).read_bytes()).hexdigest(),
              'sourceDurationMinutes': source_duration, 'windowMinutes': window, 'warmupMinutes': warmup,
              'teamCount': len(teams), 'teamsWithoutStartEstimate': sum(t['estimatedStartMinute'] is None for t in teams),
              'readableACCount': len(observed), 'exportedACCount': sum(e.verdict == 'AC' for e in contest.events),
              'exportedRJCount': sum(e.verdict == 'RJ' for e in contest.events), 'eventCount': len(contest.events),
              'rjDistribution': rj_distribution, 'reconstructionUnknownCount': len(reconstruction_unknown),
              'reconstructedRJOutsideWindow': sum(e['verdict'] == 'RJ' and not e['withinWindow'] for e in audit),
              'unsolvedRJPiledAtWindowEnd': sum(e['verdict'] == 'RJ' and 'piled-at-window-end' in e['basis'] for e in events),
              'unresolvedCellCount': len(unknown),
              'outsideWindowACCount': sum(not r['withinWindow'] for r in observed),
              'unsupportedACCountWithinWindow': sum(r['withinWindow'] and r['problem'] not in problems for r in observed),
              'pdfVerified': bool(verified_ac), 'pdfCorrectionCount': len(corrections),
              'limitations': ['Only recognizable AC minutes are used; AC seconds are unknown and represented at the minute boundary.',
                 'Earliest recognizable AC is a user-authorized proxy for first submission, not an actual submission timestamp.',
                 f'Estimated start = earliest recognizable AC minute - {warmup} minutes; no clamping to contest zero.',
                 ('No failed submissions are synthesized.' if rj_distribution == 'none' else
                  f'RJ counts follow reported tries; times are estimated with {rj_distribution} interpolation.'),
                 'Unsolved cells have no last rejection time; their RJ events are piled at window end unless a time is supplied.',
                 'The twelve-hour standings cannot determine which failed submissions really occurred in the five-hour window.',
                 'XLSX anomalies are retained; verified PDF AC minutes take precedence when supplied.',
                 'Interactive problems may anchor start estimates but are omitted from the loadable contest.']}
    dump(output / 'report.json', report)
    print(f"History: {len(teams)} teams, {report['exportedACCount']} AC, {report['exportedRJCount']} RJ; "
          f"{len(reconstruction_unknown)} unknown attempt counts", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--layout', type=Path)
    parser.add_argument('--sheet')
    parser.add_argument('--verified-ac', type=Path, help='Authoritative PDF minutes from pdf_outline_standings.py')
    parser.add_argument('--source-duration-minutes', type=int, default=720)
    parser.add_argument('--warmup-minutes', type=int, default=20)
    parser.add_argument('--window-minutes', type=int, default=300)
    parser.add_argument('--rj-distribution', choices=['none', 'uniform', 'exponential'], default='none',
                        help='Estimate failed attempt times; none exports AC only')
    args = parser.parse_args()
    if args.source_duration_minutes <= 0 or args.window_minutes <= 0 or args.warmup_minutes < 0:
        parser.error('Durations must be positive and warmup nonnegative')
    layout = json.loads(args.layout.read_text(encoding='utf-8')) if args.layout else None
    verified = json.loads(args.verified_ac.read_text(encoding='utf-8')) if args.verified_ac else None
    convert(args.workbook, args.workspace, layout, args.sheet, args.source_duration_minutes, args.warmup_minutes,
            args.window_minutes, verified, args.rj_distribution)


if __name__ == '__main__':
    main()
