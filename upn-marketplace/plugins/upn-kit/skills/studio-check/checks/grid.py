"""GRID , does every block sit on the job's column grid?

The grid is DERIVED, never restated: at each width the gutter, the max width and the outer margin are
read off the page's own computed tokens (named in job.json `grid`), and the columns are laid out from
them. Then every block-level content element in view (a block with its own words, or a picture, a
film, a canvas, a frame) must have its left and right edges on a column edge or a gutter edge within
the tolerance, or on the screen's own edges (full bleed). Anything else is reported with its offset,
fold by fold.

job.json `grid`: `columns` (a number, a token name such as "--cols", or {"<min width>": n} for
breakpoints), `gutter_var`, `max_width_var`, and optionally `margin_var` (the outer margin; the gutter
when absent). Elements positioned absolute or fixed are placed on purpose and are not scored here; a
horizontal scroller and anything under limits.json `clip_ok` are windows, and not scored either.
"""
from common import register

G = 'grid'
CHECKS = register(G, {
    'on-grid': {
        'protects': 'every block sits on the job\'s columns, so the page reads as one designed grid',
        'limit': '{grid_misses} blocks off a column or gutter edge by more than {grid_tolerance_px}px',
        'taught_by': 'new with the build system, 29 Sep: nothing measured the grid before'},
})

TOKENS_JS = r"""([gv, xv, mv, cv]) => {
  const L = __sc, vw = L.vw();
  const bs = getComputedStyle(document.body), rs = getComputedStyle(document.documentElement);
  const raw = v => v ? ((bs.getPropertyValue(v) || rs.getPropertyValue(v)) || '').trim() : '';
  const probe = v => {
    if (!raw(v)) return null;
    const d = document.createElement('div');
    d.style.cssText = 'position:absolute;left:0;top:0;height:1px;visibility:hidden;pointer-events:none;width:var(' + v + ')';
    document.body.appendChild(d);
    const w = d.getBoundingClientRect().width; d.remove(); return w;
  };
  return {vw, gutter: probe(gv), max: probe(xv), margin: probe(mv), cols: cv ? parseFloat(raw(cv)) || null : null,
          raw: {gutter: raw(gv), max: raw(xv), margin: raw(mv)}};
}"""

FOLD_JS = r"""([edges, tol, clipOk]) => {
  const L = __sc, vw = L.vw(), out = [];
  const okSel = clipOk.join(',');
  const near = x => { let best = 1e9, at = null; for (const e of edges) { const d = x - e; if (Math.abs(d) < Math.abs(best)) { best = d; at = e; } } return [best, at]; };
  let checked = 0;
  for (const el of document.body.querySelectorAll('*')) {
    if (L.hiddenTree(el) && !(el.tagName.toLowerCase() === 'svg' && !el.parentElement.closest('svg, [aria-hidden="true"]'))) continue;
    const tag = el.tagName.toLowerCase();
    const media = el.matches('img, video, canvas, iframe, object, embed, svg');
    if (!media && !(L.isBlock(el) && L.ownText(el).length > 1)) continue;
    if (!L.vis(el)) continue;
    const pos = getComputedStyle(el).position;
    if (pos === 'absolute' || pos === 'fixed') continue;
    if ((okSel && el.closest(okSel)) || L.scrollerAncestor(el)) continue;
    const r = el.getBoundingClientRect();
    if (!L.inView(r) || (media && r.width < 24)) continue;
    checked++;
    const [dl] = near(r.left), [dr] = near(r.right);
    if (Math.abs(dl) > tol || Math.abs(dr) > tol) {
      out.push({k: L.key(el), d: L.desc(el), left: Math.round(r.left), right: Math.round(r.right),
                off: 'left ' + (Math.abs(dl) > tol ? (dl > 0 ? '+' : '') + Math.round(dl) : 'ok')
                   + ', right ' + (Math.abs(dr) > tol ? (dr > 0 ? '+' : '') + Math.round(dr) : 'ok')});
    }
  }
  return {checked, misses: out.slice(0, 200)};
}"""


def columns_at(spec, width, from_var):
    if isinstance(spec, dict):
        best = None
        for k, v in spec.items():
            try:
                if width >= float(k) and (best is None or float(k) >= best[0]):
                    best = (float(k), v)
            except ValueError:
                continue
        return int(best[1]) if best else None
    if isinstance(spec, str):
        return int(from_var) if from_var else None
    return int(spec) if spec else None


def before_walk(sess, pg, page, size, st):
    g = sess.job.get('grid')
    st['skip'] = None
    st['misses'], st['checked'] = {}, 0
    if not g or not g.get('columns'):
        st['skip'] = 'job.json has no grid (columns, gutter_var, max_width_var)'
        return
    cvar = g['columns'] if isinstance(g['columns'], str) else None
    t = pg.evaluate(TOKENS_JS, [g.get('gutter_var'), g.get('max_width_var'),
                               g.get('margin_var') or g.get('gutter_var'), cvar])
    n = columns_at(g['columns'], size[0], t['cols'])
    if not n or t['gutter'] is None:
        st['skip'] = 'cannot derive the grid: columns %s, %s = %r' % (n, g.get('gutter_var'), t['raw']['gutter'])
        return
    vw, gut = t['vw'], t['gutter']
    margin = t['margin'] if t['margin'] is not None else gut
    width = vw - 2 * margin
    if t['max']:
        width = min(width, t['max'])
    left = (vw - width) / 2
    col = (width - (n - 1) * gut) / n
    edges = {0.0, float(vw)}
    for i in range(n):
        s = left + i * (col + gut)
        edges.add(round(s, 2))
        edges.add(round(s + col, 2))
    st['edges'] = sorted(edges)
    st['grid'] = '%d columns of %.1fpx, gutter %.1f, margin %.1f, container %.1f at %.1f' % (
        n, col, gut, margin, width, left)


def at_fold(sess, pg, page, size, k, st):
    if st.get('skip'):
        return
    r = pg.evaluate(FOLD_JS, [st['edges'], sess.L['grid_tolerance_px'], sess.job.lists['clip_ok']])
    st['checked'] += r['checked']
    for m in r['misses']:
        st['misses'].setdefault(m['k'], (k, m))


def finish(sess, page, size, st, shots):
    if st.get('skip'):
        sess.rec(G, 'on-grid', 'skip', st['skip'], page, size, 'chromium')
        return
    items = sorted(st['misses'].values(), key=lambda x: x[0])
    per_fold = {}
    for k, m in items:
        per_fold.setdefault(k, []).append('%s (%s)' % (m['d'], m['off']))
    txt = ' | '.join('fold %d: %s' % (k, '; '.join(v[:4]) + (' +%d more' % (len(v) - 4) if len(v) > 4 else ''))
                     for k, v in sorted(per_fold.items()))
    ev = [shots['folds'][k - 1] for k in sorted(per_fold) if k - 1 < len(shots['folds'])][:6]
    status = 'pass' if len(items) <= sess.L['grid_misses'] else 'fail'
    sess.rec(G, 'on-grid', status,
             ('%d of the blocks in view miss the grid; %s. Grid: %s' % (len(items), txt, st['grid'])) if items
             else 'every block on the grid (%s)' % st['grid'],
             page, size, 'chromium', evidence=ev or shots['folds'][:1])
