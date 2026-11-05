"""HIERARCHY , does each screen have one loudest thing, and is it the planned one?

Per fold (each viewport-height screen, as reached by scrolling): the distinct rendered text sizes
(sizes within a few per cent are one step), and the largest text against the body size (the size that
carries the most characters on the page at that width). The first fold, where a visitor lands, must
reach the job's display to body ratio. Where the job's composition plan (`00 brief/PLAN.md`) names a
fold's dominant thing, the largest text in that fold must be it, matched by selector (in backticks)
or by its words.

PLAN.md is read leniently: a heading naming the page (its job.json name), then under it either
headings or lines that say "Fold N" (a width such as 390 in that line scopes the row to that width;
without one the row is read at 1440), each with a line "Dominant: <words or `selector`>"; or a table
with a Fold column and a Dominant column.
"""
import re

from common import register

G = 'hierarchy'
CHECKS = register(G, {
    'sizes-per-fold': {
        'protects': 'a screen has a few clear steps of type, not a crowd of competing middle sizes',
        'limit': 'at most {sizes_per_fold} distinct sizes in any fold',
        'taught_by': 'the studio build notes: the portfolio mockups read as "clustered" (27 Sep)'},
    'display-to-body': {
        'protects': 'the first screen has one thing louder than everything else',
        'limit': 'largest text at least {display_to_body}x the body size in the first fold',
        'taught_by': 'the studio build notes: the portfolio mockups read as "clustered" (27 Sep)'},
    'plan-dominant': {
        'protects': 'the build shows what the composition plan said each fold would lead with',
        'limit': 'the largest text in the fold is the planned dominant thing',
        'taught_by': 'the build system, 29 Sep: the judge checks the build against the plan'},
})

FOLD_JS = r"""() => {
  const L = __sc, out = [];
  for (const el of L.textLeaves()) {
    const r = L.rangeRect(el);
    if (!L.inView(r)) continue;
    const cs = getComputedStyle(el);
    out.push({k: L.key(el), size: parseFloat(cs.fontSize), chars: L.ownText(el).length,
              area: Math.round(r.width * r.height), d: L.desc(el), text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120)});
  }
  return out;
}"""

MATCH_JS = r"""([k, sel]) => {
  const L = __sc;
  for (const el of document.body.querySelectorAll('*')) {
    if (L.key(el) !== k) continue;
    try { return !!(el.matches(sel) || el.closest(sel) || el.querySelector(sel)); } catch (e) { return 'bad selector: ' + e.message; }
  }
  return false;
}"""


def cluster(sizes, pct):
    steps = []
    for s in sorted(set(round(x, 1) for x in sizes if x > 0)):
        if steps and (s - steps[-1][-1] <= 1.0 or s <= steps[-1][-1] * (1 + pct / 100.0)):
            steps[-1].append(s)
        else:
            steps.append([s])
    return steps


# ==== PLAN.md
_EMPTY = re.compile(r'^[\s_.\-…<>\[\]()?]*$|^\s*(tbc|tbd|todo|none|n/a)\s*$', re.I)


def read_plan(job):
    """{page name lower: [(fold, width or None, spec)]} or None when there is no PLAN.md"""
    p = job.dir / '00 brief' / 'PLAN.md'
    if not p.exists():
        return None
    names = [(pg.get('name') or '').lower() for pg in (job.get('pages', default=[]) or [])]
    plan, page, fold, width = {}, None, None, None
    table = None
    for raw in p.read_text(encoding='utf-8', errors='replace').splitlines():
        line = raw.strip()
        h = re.match(r'^(#{1,6})\s+(.*)$', line)
        text = h.group(2) if h else line
        low = text.lower()
        fm = re.search(r'\bfold\s*(\d+)', low)
        if h and not fm:
            hit = [n for n in names if n and re.search(r'(^|[^a-z0-9])' + re.escape(n) + r'([^a-z0-9]|$)', low)]
            if hit:
                page, fold, table = max(hit, key=len), None, None
                continue
        if page is None:
            continue
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            lc = [c.lower() for c in cells]
            if any('fold' in c for c in lc) and any('dominant' in c for c in lc):
                table = (next(i for i, c in enumerate(lc) if 'fold' in c), next(i for i, c in enumerate(lc) if 'dominant' in c))
                continue
            if table and not set(line) <= set('|-: '):
                fi, di = table
                if fi < len(cells) and di < len(cells):
                    n = re.search(r'(\d+)', cells[fi])
                    wm = re.search(r'\b(3\d\d|4\d\d|7\d\d|1\d{3}|2\d{3}|3\d{3})\b', cells[fi].replace(n.group(1), '', 1) if n else '')
                    if n and not _EMPTY.match(cells[di]):
                        plan.setdefault(page, []).append((int(n.group(1)), int(wm.group(1)) if wm else None, cells[di]))
            continue
        table = None
        if fm:
            fold = int(fm.group(1))
            wm = re.search(r'\b(3\d\d|4\d\d|7\d\d|1\d{3}|2\d{3}|3\d{3})\b', low.replace(fm.group(0), ' '))
            width = int(wm.group(1)) if wm else None
        dm = re.search(r'dominant(?:\s+thing)?\s*\**\s*[:=\-]\s*\**\s*(.+)$', text, re.I)
        if dm and fold is not None and not _EMPTY.match(dm.group(1)):
            plan.setdefault(page, []).append((fold, width, dm.group(1).strip().strip('*').strip()))
    return plan


def spec_of(value):
    """a selector in backticks, else the words: a quoted phrase when there is one, else the whole value"""
    m = re.search(r'`([^`]+)`', value)
    if m:
        return ('selector', m.group(1))
    q = re.search(r'["\u201c]([^"\u201d]{2,})["\u201d]', value)
    return ('text', re.sub(r'\s+', ' ', (q.group(1) if q else value).strip(' "\'')).lower())


def text_matches(want, got):
    """one contains the other, or most of the shorter one's words are in the longer"""
    if not want or not got:
        return False
    if want in got or got in want:
        return True
    ww = set(re.findall(r'[a-z0-9\u00c0-\u024f]{3,}', want))
    gw = set(re.findall(r'[a-z0-9\u00c0-\u024f]{3,}', got))
    small = ww if len(ww) <= len(gw) else gw
    return bool(small) and len(ww & gw) / float(len(small)) >= 0.6


# ==== the sweep hooks
def before_walk(sess, pg, page, size, st):
    st['folds'] = {}
    if 'plan' not in sess.cache:
        sess.cache['plan'] = read_plan(sess.job)


def at_fold(sess, pg, page, size, k, st):
    rows = pg.evaluate(FOLD_JS)
    st['folds'][k] = rows
    plan = sess.cache.get('plan')
    if not plan or not rows:
        return
    want = [(f, w, v) for (f, w, v) in plan.get((page.get('name') or '').lower(), [])
            if f == k and ((w is None and size[0] == 1440) or w == size[0])]
    if not want:
        return
    top = max(rows, key=lambda r: (r['size'], r['area']))
    for f, w, v in want:
        kind, s = spec_of(v)
        if kind == 'selector':
            ok = pg.evaluate(MATCH_JS, [top['k'], s])
        else:
            ok = text_matches(s, top['text'].lower())
        st.setdefault('plan', []).append((k, v, top, ok))


def finish(sess, page, size, st, shots):
    L = sess.L
    pct = L['size_cluster_pct']
    all_rows = [r for rows in st['folds'].values() for r in rows]
    if not all_rows:
        for c in ('sizes-per-fold', 'display-to-body'):
            sess.rec(G, c, 'skip', 'no visible text on the page', page, size, 'chromium')
        return
    chars = {}
    for r in all_rows:
        b = round(r['size'], 1)
        chars[b] = chars.get(b, 0) + r['chars']
    body = max(chars.items(), key=lambda x: x[1])[0]
    crowded, ratios = [], []
    for k in sorted(st['folds']):
        rows = st['folds'][k]
        if not rows:
            continue
        steps = cluster([r['size'] for r in rows], pct)
        if len(steps) > L['sizes_per_fold']:
            crowded.append('fold %d has %d sizes %s' % (k, len(steps), [s[0] for s in steps]))
        ratios.append((k, max(r['size'] for r in rows) / body))
    ev = [shots['folds'][0]] if shots['folds'] else []
    sess.rec(G, 'sizes-per-fold', 'fail' if crowded else 'pass',
             '; '.join(crowded[:6]) if crowded else 'every fold within %d sizes' % L['sizes_per_fold'],
             page, size, 'chromium', evidence=ev)
    need = L['display_to_body']
    r_txt = 'body %.1fpx; ratios by fold %s' % (body, ', '.join('%d:%.2f' % (k, r) for k, r in ratios[:12]))
    if not need or need <= 1:
        sess.rec(G, 'display-to-body', 'skip', 'the job sets no display to body ratio; ' + r_txt, page, size, 'chromium')
    elif not ratios:
        sess.rec(G, 'display-to-body', 'skip', 'no text in the first fold', page, size, 'chromium')
    else:
        first = ratios[0][1]
        sess.rec(G, 'display-to-body', 'pass' if first >= need - 0.01 else 'fail',
                 'first fold %.2fx; %s' % (first, r_txt), page, size, 'chromium', evidence=ev)
    plan = sess.cache.get('plan')
    if size[0] == 1440 or any(w == size[0] for rows in (plan or {}).values() for (_, w, _) in rows):
        if plan is None:
            if size[0] == 1440:
                sess.rec(G, 'plan-dominant', 'skip', 'no 00 brief/PLAN.md in the job', page, size, 'chromium')
            return
        rows = st.get('plan') or []
        if not rows:
            if size[0] == 1440:
                sess.rec(G, 'plan-dominant', 'skip', 'PLAN.md names no dominant thing for this page at this width',
                         page, size, 'chromium')
            return
        for k, v, top, ok in rows:
            evk = [shots['folds'][k - 1]] if k - 1 < len(shots['folds']) else []
            if isinstance(ok, str):
                sess.rec(G, 'plan-dominant', 'error', 'fold %d: %s' % (k, ok), page, size, 'chromium', evidence=evk)
                continue
            sess.rec(G, 'plan-dominant', 'pass' if ok else 'fail',
                     'fold %d: planned %s; largest is %s at %.0fpx' % (k, v[:80], top['d'], top['size']),
                     page, size, 'chromium', evidence=evk)
