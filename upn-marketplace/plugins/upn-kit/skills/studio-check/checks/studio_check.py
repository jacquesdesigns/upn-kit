#!/usr/bin/env python3
"""The studio check kit: one kit for every job; the job supplies only job.json.

    <repo>/<python> "<kit_root>/skills/studio-check/checks/studio_check.py" --job <job dir>
        [--url URL] [--live] [--only group,group] [--pages a,b] [--quick] [--list]

Serves job.json `serve.root` on a free 127.0.0.1 port unless --url (any address) or --live (job.json
`live_url`). --quick is for fast loops while building: Chromium only, at 390, 1280 and 1440, no films.
The full run is the gate. --list prints every check with what it protects, its limit and what taught it.

Writes <job>/evidence/checks/<YYYYMMDD-HHMMSS>/ (report.json, report.md, shots/, films/, sheets/) and
<job>/evidence/checks/latest naming the newest run. Exits 1 on any fail or error, 0 otherwise.
A skip is never a pass: it always says why in `measured`.
"""
import argparse
import importlib
import json
import math
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True       # nothing written into the repo but evidence
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402

import common  # noqa: E402
from common import GROUPS, Job, Report, Server, Session, contact_sheet, join_url, shot_name, stamp  # noqa: E402

# groups measured together in one shared sweep: each page loaded once per size, walked fold by fold
SWEEP = ['layout', 'grid', 'spacing', 'hierarchy', 'type_colour']


def load_modules():
    return {g: importlib.import_module(g) for g in GROUPS}


def list_checks():
    load_modules()
    lim = json.loads((common.KIT / 'limits.json').read_text(encoding='utf-8'))['limits']
    lim['unknown_marker'] = 'to confirm'
    for g in GROUPS:
        print('\n%s' % g)
        for c, spec in common.REGISTRY.get(g, {}).items():
            print('  %-24s %s\n  %-24s limit: %s\n  %-24s taught by: %s' % (
                c, spec['protects'], '', spec['limit'].format_map(common._Blank(lim)), '', spec['taught_by']))


def sweep(sess, mods, active):
    """every page at every sweep size in Chromium: fold shots, a full-page shot, and each sweep group's measures"""
    L = sess.L
    for size in sess.sweep_sizes():
        w, h = size
        ctx, why = sess.context('chromium', size)
        if not ctx:
            for g in active:
                sess.rec(g, list(common.REGISTRY[g])[0], 'skip', why, None, size, 'chromium')
            continue
        try:
            for page in sess.pages:
                name = page.get('name') or 'page'
                states = {g: {} for g in active}
                shots = {'folds': [], 'full': []}
                try:
                    pg = sess.open(ctx, page)
                except Exception as e:
                    for g in active:
                        sess.rec(g, list(common.REGISTRY[g])[0], 'error', 'the page did not load: %s' % str(e).splitlines()[0][:200],
                                 page, size, 'chromium')
                    continue
                try:
                    ok = {}
                    for g in active:
                        fn = getattr(mods[g], 'before_walk', None)
                        ok[g] = True
                        if fn and sess.guard(g, list(common.REGISTRY[g])[0], lambda: fn(sess, pg, page, size, states[g]) or True,
                                             page=name, size=size, engine='chromium') is None:
                            ok[g] = False
                    maxy = pg.evaluate('() => __sc.maxY()')
                    folds = min(L['max_folds'], int(math.ceil((maxy + h) / float(h))) if h else 1)
                    for k in range(1, folds + 1):
                        pg.evaluate('(y) => __sc.to(y)', (k - 1) * h)
                        pg.wait_for_timeout(sess.settle_ms())
                        p = sess.shots / shot_name(name, w, h, 'chromium', k)
                        try:
                            pg.screenshot(path=str(p))
                            shots['folds'].append(sess.rel(p))
                        except Exception:
                            pass
                        for g in active:
                            fn = getattr(mods[g], 'at_fold', None)
                            if fn and ok[g]:
                                if sess.guard(g, list(common.REGISTRY[g])[0], lambda: fn(sess, pg, page, size, k, states[g]) or True,
                                              page=name, size=size, engine='chromium') is None:
                                    ok[g] = False
                        if k < folds and pg.evaluate('() => __sc.maxY()') > maxy + 2:
                            maxy = pg.evaluate('() => __sc.maxY()')
                            folds = min(L['max_folds'], int(math.ceil((maxy + h) / float(h))))
                    if folds >= L['max_folds'] and pg.evaluate('() => __sc.maxY()') + h > folds * h:
                        sess.report.notes.append('%s at %dx%d: stopped after %d folds (limits.max_folds)' % (name, w, h, folds))
                    pg.evaluate('() => __sc.to(0)')
                    pg.wait_for_timeout(min(600, sess.settle_ms()))
                    for g in active:
                        fn = getattr(mods[g], 'after_walk', None)
                        if fn and ok[g]:
                            if sess.guard(g, list(common.REGISTRY[g])[0], lambda: fn(sess, pg, page, size, states[g]) or True,
                                          page=name, size=size, engine='chromium') is None:
                                ok[g] = False
                    p = sess.shots / shot_name(name, w, h, 'chromium')
                    try:
                        pg.screenshot(path=str(p), full_page=True)
                        shots['full'].append(sess.rel(p))
                    except Exception as e:
                        sess.report.notes.append('full-page shot of %s at %dx%d failed: %s' % (name, w, h, str(e)[:100]))
                    sess.fold_shots[(name, w, h, 'chromium')] = shots['folds']
                    for g in active:
                        if ok[g]:
                            sess.guard(g, list(common.REGISTRY[g])[0], lambda: mods[g].finish(sess, page, size, states[g], shots),
                                       page=name, size=size, engine='chromium')
                finally:
                    pg.close()
        finally:
            ctx.close()


def sheets(sess):
    """one sheet of every width per page (the first screen at each), and one of every fold at 390 and 1440"""
    for page in sess.pages:
        name = page.get('name') or 'page'
        items = []
        for (n, w, h, e), folds in sorted(sess.fold_shots.items(), key=lambda x: (x[0][1], x[0][2])):
            if n == name and folds:
                items.append((sess.run_dir / folds[0], '%dx%d' % (w, h)))
        if items:
            contact_sheet(items, sess.sheets / ('%s__widths.png' % common.safe_name(name)), cell_h=300)
        items = []
        for (n, w, h, e), folds in sorted(sess.fold_shots.items(), key=lambda x: (x[0][1], x[0][2])):
            if n == name and w in (390, 1440) and h == sess.job.sizes['height']:
                items += [(sess.run_dir / f, '%d fold %d' % (w, i + 1)) for i, f in enumerate(folds)]
        if items:
            contact_sheet(items, sess.sheets / ('%s__folds.png' % common.safe_name(name)), cell_h=360)


def main():
    ap = argparse.ArgumentParser(description='The studio check kit.')
    ap.add_argument('--job', help='the job folder (holds job.json)')
    ap.add_argument('--url', help='check this address instead of serving serve.root')
    ap.add_argument('--live', action='store_true', help='check job.json live_url')
    ap.add_argument('--only', help='comma-separated groups: ' + ','.join(GROUPS))
    ap.add_argument('--pages', help='comma-separated page names from job.json')
    ap.add_argument('--quick', action='store_true', help='Chromium only at 390, 1280, 1440; no films')
    ap.add_argument('--list', action='store_true', help='print every check and exit')
    args = ap.parse_args()
    if args.list:
        list_checks()
        return 0
    if not args.job:
        ap.error('--job is required')
    job = Job(args.job)
    mods = load_modules()
    groups = GROUPS
    if args.only:
        want = [g.strip() for g in args.only.split(',') if g.strip()]
        unknown = [g for g in want if g not in GROUPS]
        if unknown:
            ap.error('unknown group(s) %s; groups are %s' % (unknown, ', '.join(GROUPS)))
        groups = [g for g in GROUPS if g in want]
    server = None
    live = False
    if args.live:
        if not job.get('live_url'):
            print('studio_check: --live but job.json has no live_url', file=sys.stderr)
            return 1
        base, live = job.get('live_url'), True
    elif args.url:
        base = args.url
    else:
        server = Server(job.path(job.get('serve', 'root', default='.')))
        base = server.base
    run = stamp()
    out = job.dir / 'evidence' / 'checks'
    run_dir = out / run
    while run_dir.exists():
        time.sleep(1)
        run = stamp()
        run_dir = out / run
    run_dir.mkdir(parents=True)
    mode = 'quick' if (args.quick or args.only) else 'full'
    report = Report(job.name, run, join_url(base, job.get('serve', 'entry', default='/')), live, mode=mode, groups=groups)
    sess = Session(job, args, report, base, run_dir)
    if not sess.pages:
        print('studio_check: no pages to check (job.json pages, or --pages matched none)', file=sys.stderr)
    t0 = time.time()
    print('studio check: %s, %s run, %s, groups %s' % (job.name, mode, base, ', '.join(groups)), flush=True)
    try:
        with sync_playwright() as pw:
            sess.pw = pw
            active = [g for g in SWEEP if g in groups]
            if active and sess.pages:
                sweep(sess, mods, active)
                sheets(sess)
            for g in groups:
                if g in SWEEP:
                    continue
                if g not in ('system',) and not sess.pages:
                    continue
                sess.guard(g, list(common.REGISTRY[g])[0], lambda: mods[g].run(sess))
            sess.close()
    finally:
        if server:
            server.stop()
        report.notes.append('ran in %.0fs' % (time.time() - t0))
        report.write(run_dir)
        (out / 'latest').write_text(run + '\n', encoding='utf-8')
        # the judge and the handback read latest-full, so a quick run afterwards cannot stand in for the gate run
        if json.loads((run_dir / 'report.json').read_text(encoding='utf-8')).get('mode') == 'full':
            (out / 'latest-full').write_text(run + '\n', encoding='utf-8')
    s = report.summary()
    print('\n%d pass, %d fail, %d skip, %d error  ->  %s' % (s['pass'], s['fail'], s['skip'], s['error'], run_dir / 'report.md'))
    return 1 if (s['fail'] or s['error']) else 0


if __name__ == '__main__':
    sys.exit(main())
