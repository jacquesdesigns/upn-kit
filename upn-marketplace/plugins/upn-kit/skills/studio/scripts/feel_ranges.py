#!/usr/bin/env python3
"""What a set of captured site references agrees on, as ranges.

  feel_ranges.py REFERENCES_DIR [--kind feel]

Reads every <ref>/measure.json under REFERENCES_DIR (and index.jsonl, if present, to keep only refs of
--kind). Prints a markdown table of min / median / max across the set, so a design takes its values from
the set's range rather than from one favourite site.
"""
import argparse, json, pathlib, re, statistics


def secs(t):
    m = re.match(r'([\d.]+)(ms|s)', t)
    return float(m.group(1)) / (1000 if m.group(2) == 'ms' else 1) if m else None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('--kind')
    a = ap.parse_args(); root = pathlib.Path(a.dir)
    keep = None
    idx = root / 'index.jsonl'
    if a.kind and idx.exists():
        keep = {json.loads(l)['id'] for l in idx.read_text().splitlines() if l.strip() and json.loads(l).get('kind') == a.kind}
    rows = {}
    for m in sorted(root.glob('*/measure.json')):
        if keep is not None and m.parent.name not in keep:
            continue
        d = json.loads(m.read_text()); ms = d['measure']
        durs = [secs(k) for k, n in ms['transitionDurations'] for _ in range(n)]
        durs = [x for x in durs if x]
        rows[m.parent.name] = {
            'page length (screens)': ms['screens'],
            'distinct font sizes': ms['distinctFontSizes'],
            'pinned sections': len(ms['pinnedSections_screens']),
            'total pin hold (screens)': round(sum(ms['pinnedSections_screens']), 1),
            'median transition (s)': round(statistics.median(durs), 2) if durs else None,
            'mean px per wheel step': d.get('scroll', {}).get('meanStepPx'),
            'fixed or sticky elements': ms['fixedOrSticky'],
        }
    if not rows:
        raise SystemExit('no measure.json found')
    keys = list(next(iter(rows.values())).keys())
    print(f'Across {len(rows)} references: ' + ', '.join(rows))
    print('\n| measure | min | median | max |\n|---|---|---|---|')
    for k in keys:
        vals = [r[k] for r in rows.values() if r[k] is not None]
        if vals:
            print(f'| {k} | {min(vals)} | {statistics.median(vals)} | {max(vals)} |')
    libs = {}
    for m in root.glob('*/measure.json'):
        if keep is None or m.parent.name in keep:
            for k, v in json.loads(m.read_text())['measure']['libraries'].items():
                libs[k] = libs.get(k, 0) + bool(v)
    print('\nLibraries in use (count of references): ' + ', '.join(f'{k} {v}' for k, v in libs.items() if v))


if __name__ == '__main__':
    main()
