"""Recover AC minutes from outlined (textless) DOMjudge standings PDFs.

Optional import-time tool, requires pymupdf. Calibrate digit shapes from a
visually checked first row in a layout JSON. Only unambiguous outline matches
are emitted; this does not perform OCR or infer submission times.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.standings_to_history import read_workbook


def shape(drawing):
    rect = drawing['rect']
    points, types = [], []
    for item in drawing['items']:
        types.append(item[0])
        for point in item[1:]:
            if hasattr(point, 'x'):
                points.extend([point.x - rect.x0, point.y - rect.y0])
            elif hasattr(point, 'x0'):
                points.extend([point.x0 - rect.x0, point.y0 - rect.y0,
                               point.x1 - rect.x0, point.y1 - rect.y0])
    return tuple(types), [rect.width, rect.height, *points]


def distance(a, b):
    if a[0] != b[0] or len(a[1]) != len(b[1]):
        return float('inf')
    return max(abs(x - y) for x, y in zip(a[1], b[1]))


def glyphs_in(rect, drawings):
    return sorted((d for d in drawings if d['fill'] == (0., 0., 0.)
                   and rect.x0 < d['rect'].x0 and d['rect'].x1 < rect.x1
                   and rect.y0 < d['rect'].y0 < rect.y0 + 10
                   and 5 < d['rect'].height < 9), key=lambda d: d['rect'].x0)


def attempt_glyphs(rect, drawings):
    return sorted((d for d in drawings if d['fill'] == (0., 0., 0.)
                   and rect.x0 < d['rect'].x0 and d['rect'].x1 < rect.x1
                   and rect.y0 + 10 < d['rect'].y0 < rect.y1
                   and 4.4 < d['rect'].height < 5.1), key=lambda d: d['rect'].x0)


def match_digit(glyph, templates, maximum):
    signature = shape(glyph)
    scores = {digit: min(distance(signature, s) for d, s in templates if d == digit) for digit in '0123456789'}
    ordered = sorted(scores.items(), key=lambda p: p[1])
    best, diff = ordered[0]
    return (best if diff <= maximum and ordered[1][1] - diff >= .2 else None), diff


def extract(pdf_path, workbook, layout):
    import pymupdf
    geometry = layout['pdfOutline']
    colors = set(layout['acceptedColors'])
    rejected_colors = set(layout.get('rejectedColors', []))
    first_center = geometry['firstProblemCenterX']
    step = geometry['problemColumnStep']
    columns = list(layout['problemColumns'])
    def rectangles(drawings, selected_colors=None):
        found = []
        for d in drawings:
            if d['fill'] is None:
                continue
            color = ''.join(f'{round(c * 255):02X}' for c in d['fill'])
            if color not in (colors if selected_colors is None else selected_colors):
                continue
            for item in d['items']:
                if item[0] != 're':
                    continue
                rect = item[1]
                if 30 < rect.width < 36 and 18 < rect.height < 25 and rect.x0 > 240:
                    found.append(rect)
        return found
    book = read_workbook(workbook)
    team_rows = []
    for row in book['rows']:
        if row['row'] in layout.get('headerRows', []) + layout.get('ignoredRows', []) or row['row'] < layout['firstTeamRow']:
            continue
        if any(c['value'].strip().upper() == layout['stopText'] for c in row['cells']):
            break
        team_rows.append(row['row'])
    templates = []
    records, unknown, badges_seen = [], [], 0
    rejected, unknown_attempts, attempt_templates = [], [], []
    with pymupdf.open(pdf_path) as pdf:
        first_drawings = pdf[0].get_drawings()
        first_cells = sorted([r for r in rectangles(first_drawings) if abs(r.y0 - geometry['calibrationTopY']) < .2], key=lambda r: r.x0)
        expected = geometry['calibrationMinutes']
        if len(first_cells) != len(expected):
            raise ValueError('Calibration rectangle count differs from reviewed first row')
        for rect, number in zip(first_cells, expected):
            glyphs = glyphs_in(rect, first_drawings)
            if len(glyphs) != len(str(number)):
                raise ValueError(f'Calibration glyph count differs for {number}')
            templates.extend((digit, shape(glyph)) for digit, glyph in zip(str(number), glyphs))
        for reference in geometry.get('additionalCalibration', []):
            drawings = pdf[reference['page'] - 1].get_drawings()
            cells = [r for r in rectangles(drawings) if abs(r.y0 - reference['topY']) < .2
                     and abs((r.x0 + r.x1) / 2 - first_center - columns.index(reference['problem']) * step) < 2]
            if len(cells) != 1:
                raise ValueError('Additional calibration cell is ambiguous')
            glyphs = glyphs_in(cells[0], drawings)
            if len(glyphs) != len(str(reference['minute'])):
                raise ValueError('Additional calibration digit count differs')
            templates.extend((digit, shape(glyph)) for digit, glyph in zip(str(reference['minute']), glyphs))
        if {digit for digit, _ in templates} != set('0123456789'):
            raise ValueError('Calibration must contain all ten digits')
        for reference in geometry.get('attemptCalibration', []):
            drawings = pdf[reference['page'] - 1].get_drawings()
            cells = [r for r in rectangles(drawings, colors | rejected_colors) if abs(r.y0 - reference['topY']) < .2
                     and abs((r.x0 + r.x1) / 2 - first_center - columns.index(reference['problem']) * step) < 2]
            if len(cells) != 1:
                raise ValueError('Attempt calibration cell is ambiguous')
            glyphs = attempt_glyphs(cells[0], drawings)[:len(str(reference['tries']))]
            if len(glyphs) != len(str(reference['tries'])):
                raise ValueError('Attempt calibration digit count differs')
            attempt_templates.extend((digit, shape(glyph)) for digit, glyph in zip(str(reference['tries']), glyphs))
        if attempt_templates and {digit for digit, _ in attempt_templates} != set('0123456789'):
            raise ValueError('Attempt calibration must contain all ten digits')
        for page in pdf:
            drawings = page.get_drawings()
            badges = sorted([pymupdf.Rect(i['bbox']) for i in page.get_image_info()
                             if 50 < i['bbox'][0] < 60 and 14 < i['bbox'][2] - i['bbox'][0] < 20], key=lambda r: r.y0)
            accepted_rects = rectangles(drawings)
            for rect in accepted_rects + rectangles(drawings, rejected_colors):
                x, y = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
                column = round((x - first_center) / step)
                if not 0 <= column < len(columns) or abs(x - first_center - column * step) > 2:
                    raise ValueError('AC rectangle has ambiguous problem column')
                candidates = [(abs(y - (b.y0 + b.y1) / 2), index) for index, b in enumerate(badges)]
                if not candidates or min(candidates)[0] > 3:
                    raise ValueError('AC rectangle has no matching team badge')
                index = badges_seen + min(candidates)[1]
                row = team_rows[index]
                common = {'sourceRow': row, 'problem': columns[column], 'pdfPage': page.number + 1, 'pdfRect': list(rect)}
                tries = None
                if attempt_templates:
                    digits, worst_attempt, previous_right = '', 0, None
                    for glyph in attempt_glyphs(rect, drawings):
                        if previous_right is not None and glyph['rect'].x0 - previous_right > 2.5:
                            break  # Space and the skipped t/r separate "tries".
                        digit, diff = match_digit(glyph, attempt_templates, geometry.get('maxShapeDistance', .25))
                        if digit is None:
                            digits = ''  # Never accept a truncated multi-digit count.
                            break
                        digits += digit
                        worst_attempt = max(worst_attempt, diff)
                        previous_right = glyph['rect'].x1
                    if digits and int(digits) > 0:
                        tries = int(digits)
                    else:
                        unknown_attempts.append({**common, 'reason': 'attempt-count-outline-unmatched'})
                if rect not in accepted_rects:
                    rejected.append({**common, 'reportedTries': tries, 'basis': 'pdf-vector-attempt-outline'})
                    continue
                glyphs = glyphs_in(rect, drawings)
                text, worst, gaps = '', 0, []
                for glyph in glyphs:
                    signature = shape(glyph)
                    scores = {digit: min(distance(signature, s) for d, s in templates if d == digit) for digit in '0123456789'}
                    ordered = sorted(scores.items(), key=lambda p: p[1])
                    best, diff = ordered[0]
                    gap = ordered[1][1] - diff
                    if diff > geometry.get('maxShapeDistance', .25) or gap < .2:
                        text += '?'
                    else:
                        text += best
                    worst = max(worst, diff)
                    gaps.append(gap)
                common.update(recognizedDigits=text, maxShapeDistance=worst if math.isfinite(worst) else None)
                if attempt_templates:
                    common['reportedTries'] = tries
                if not text or '?' in text:
                    unknown.append(common)
                else:
                    records.append({**common, 'acceptedMinute': int(text), 'basis': 'pdf-vector-digit-outline'})
            badges_seen += len(badges)
            print(f'PDF page {page.number + 1}: {len(badges)} teams; {len(records)} AC, {len(rejected)} rejected cells; '
                  f'{len(unknown)} minute / {len(unknown_attempts)} attempt counts unresolved', flush=True)
    if badges_seen != len(team_rows):
        raise ValueError(f'PDF/XLSX team alignment mismatch: {badges_seen} / {len(team_rows)}')
    if len({(r['sourceRow'], r['problem']) for r in records}) != len(records):
        raise ValueError('Duplicate PDF team/problem cell')
    expected_counts = geometry.get('expectedACCounts')
    if expected_counts:
        counts = Counter(r['problem'] for r in records + unknown)
        if any(counts[pid] != expected_counts[pid] for pid in columns):
            raise ValueError('Recovered AC cell counts differ from reviewed PDF summary')
    return {'source': Path(pdf_path).name, 'pdfSha256': hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest(),
            'workbookSha256': hashlib.sha256(Path(workbook).read_bytes()).hexdigest(),
            'method': 'reviewed-digit-template-outline-matching',
            'teamCount': badges_seen, 'accepted': sorted(records, key=lambda r: (r['sourceRow'], r['problem'])), 'unresolved': unknown,
            'rejected': sorted(rejected, key=lambda r: (r['sourceRow'], r['problem'])), 'unresolvedAttempts': unknown_attempts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--workbook', type=Path, required=True)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.pdf, args.workbook, json.loads(args.layout.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
