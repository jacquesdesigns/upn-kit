"""LAYOUT , what breaks between the test viewports.

Seventeen widths at 900 tall, two short laptop heights and a phone on its side. At each, per page: the
page cannot pan sideways, nothing is painted past the screen, and fold by fold (each viewport-height
screen, filmed as a person would reach it) no glyphs sit on other glyphs and no words are cut off by a
box that hides its overflow. Glyphs are measured by Range rects over the text nodes, never by element
boxes: two boxes overlapping is common and harmless, two sets of glyphs overlapping is always a defect.

Methods from v1 `checks/sweep.py` and an earlier job `08 site/test.py` (the Range rect, the clipping-ancestor
intersection that starts at the element itself, fixed chrome left to the controls group).
"""
from common import register

G = 'layout'
CHECKS = register(G, {
    'no-sideways-pan': {
        'protects': 'the page never moves sideways under a thumb or a trackpad',
        'limit': 'scrollWidth <= innerWidth and a sideways scroll moves {pan}px',
        'taught_by': 'an earlier job site test.py: html overflow-x clip hid a page 536px wide at 390'},
    'nothing-painted-past': {
        'protects': 'nothing is drawn outside the screen, even where overflow is clipped',
        'limit': '{painted_past} elements past the viewport edge',
        'taught_by': 'an earlier job site test.py: the pan test passed while the layout was 536px wide'},
    'text-overlap': {
        'protects': 'two things that should both be readable are both readable',
        'limit': '{overlap} glyph overlaps (Range rects, over {overlap_min_area_px2}px2)',
        'taught_by': 'the studio build notes: 955 green an earlier job gates, overlaps at 960, 1100, 1680 and 2560'},
    'text-clipped': {
        'protects': 'no word is cut off by a box that hides its overflow',
        'limit': '{clipped} clipped text runs',
        'taught_by': 'the studio build notes: "0 overflows" reported on a page with overlapping text'},
})

PAN_JS = r"""() => {
  const L = __sc, se = document.scrollingElement || document.documentElement;
  const vw = L.vw(), x0 = scrollX, y0 = scrollY;
  window.scrollTo(99999, y0);
  const panned = scrollX;
  window.scrollTo(x0, y0);
  return {vw, sw: se.scrollWidth, panned: Math.round(panned)};
}"""

PAST_JS = r"""() => {
  // aria-hidden decoration is still painted, so it counts; inside an <svg> only the <svg> is scored
  const L = __sc, vw = L.vw(), bad = [], offenders = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (el.ownerSVGElement) continue;
    if (offenders.some(o => o.contains(el))) continue;
    if (!L.vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right <= vw + 1 && r.left >= -1) continue;
    const pos = getComputedStyle(el).position;
    // an off-canvas panel parked wholly outside the screen is not painted anywhere a person sees
    if ((pos === 'fixed' || pos === 'absolute') && (r.left >= vw - 1 || r.right <= 1)) continue;
    // a deliberate window (a marquee run, a scroller): its own clipping ancestor decides
    let n = el.parentElement, inside = false;
    while (n && n !== document.documentElement) {
      const c = getComputedStyle(n);
      if (c.overflowX !== 'visible' || (c.clipPath && c.clipPath !== 'none')) {
        const nr = n.getBoundingClientRect();
        if (nr.right <= vw + 1 && nr.left >= -1) inside = true;
        break;
      }
      n = n.parentElement;
    }
    // the outermost offender only: a child of an escaping box escapes with it
    if (!inside) { offenders.push(el); bad.push(L.desc(el) + ' @' + Math.round(r.left) + '..' + Math.round(r.right)); }
  }
  return bad.slice(0, 40);
}"""

FOLD_JS = r"""([minArea, clipOk]) => {
  const L = __sc, out = {overlaps: [], clipped: []};
  const okSel = clipOk.join(',');
  const leaves = L.textLeaves().filter(el => !L.chrome(el));
  const boxes = [];
  for (const el of leaves) {
    const f = L.rangeRect(el);
    if (!L.inView(f)) continue;
    const c = L.clipTo(el, f);
    const fw = f.right - f.left, fh = f.bottom - f.top;
    const cw = Math.max(0, c.right - c.left), ch = Math.max(0, c.bottom - c.top);
    const ok = okSel && el.closest(okSel);
    if (!ok && !L.scrollerAncestor(el) && fw >= 4 && fh >= 4 && cw >= 2 && ch >= 2
        && (cw < fw * 0.94 || ch < fh * 0.8)) {
      out.clipped.push({k: L.key(el), d: L.desc(el), shows: Math.round(cw) + 'x' + Math.round(ch),
                        of: Math.round(fw) + 'x' + Math.round(fh)});
    }
    if (cw > 2 && ch > 2 && !ok) boxes.push({el, r: c});
  }
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i], b = boxes[j];
    if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
    const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
    const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    // an earlier job quick.py's proven floor: line boxes touching by a few pixels are not glyphs over glyphs.
    if (w > 4 && h > 6 && w * h > minArea) {
      const ka = L.key(a.el), kb = L.key(b.el);
      out.overlaps.push({k: Math.min(ka, kb) + ':' + Math.max(ka, kb),
                         d: L.desc(a.el) + ' x ' + L.desc(b.el), area: Math.round(w) + 'x' + Math.round(h)});
    }
  }
  out.overlaps = out.overlaps.slice(0, 60);
  out.clipped = out.clipped.slice(0, 60);
  return out;
}"""


def before_walk(sess, pg, page, size, st):
    st['pan'] = pg.evaluate(PAN_JS)
    st['past'] = pg.evaluate(PAST_JS)
    st['overlaps'], st['clipped'] = {}, {}


def at_fold(sess, pg, page, size, k, st):
    r = pg.evaluate(FOLD_JS, [sess.L['overlap_min_area_px2'], sess.job.lists['clip_ok']])
    for o in r['overlaps']:
        st['overlaps'].setdefault(o['k'], (k, o))
    for c in r['clipped']:
        st['clipped'].setdefault(c['k'], (k, c))


def finish(sess, page, size, st, shots):
    L = sess.L
    p = st['pan']
    over = max(0, p['sw'] - p['vw'])
    ok = over <= L['pan'] and p['panned'] <= L['pan']
    sess.rec(G, 'no-sideways-pan', 'pass' if ok else 'fail',
             'scrollWidth %d vs innerWidth %d; a sideways scroll moved %dpx' % (p['sw'], p['vw'], p['panned']),
             page, size, 'chromium', evidence=shots['full'])
    past = st['past']
    sess.rec(G, 'nothing-painted-past', 'pass' if len(past) <= L['painted_past'] else 'fail',
             ('%d past the edge: %s' % (len(past), '; '.join(past[:6]))) if past else '0 past the edge',
             page, size, 'chromium', evidence=shots['full'])

    def fold_list(d, fmt):
        items = sorted(d.values(), key=lambda x: x[0])
        return items, '; '.join('fold %d %s' % (k, fmt(o)) for k, o in items[:8])

    items, txt = fold_list(st['overlaps'], lambda o: '%s (%s)' % (o['d'], o['area']))
    ev = sorted({shots['folds'][k - 1] for k, _ in items if k - 1 < len(shots['folds'])})[:6]
    sess.rec(G, 'text-overlap', 'pass' if len(items) <= L['overlap'] else 'fail',
             ('%d overlaps: %s' % (len(items), txt)) if items else '0 overlaps in %d folds' % len(shots['folds']),
             page, size, 'chromium', evidence=ev or shots['folds'][:1])
    items, txt = fold_list(st['clipped'], lambda o: '%s shows %s of %s' % (o['d'], o['shows'], o['of']))
    ev = sorted({shots['folds'][k - 1] for k, _ in items if k - 1 < len(shots['folds'])})[:6]
    sess.rec(G, 'text-clipped', 'pass' if len(items) <= L['clipped'] else 'fail',
             ('%d clipped: %s' % (len(items), txt)) if items else '0 clipped in %d folds' % len(shots['folds']),
             page, size, 'chromium', evidence=ev or shots['folds'][:1])
