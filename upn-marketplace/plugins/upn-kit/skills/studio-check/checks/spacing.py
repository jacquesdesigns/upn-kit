"""SPACING , the part of a layout that is invisible until it is wrong.

Generalised from an earlier job `08 site/checks/spacing.py`. A fold 24px off the scale reads as "slightly
cheap" and nobody can say why, so five measurements, per page, per width:

  1. fold padding (top and bottom) is a step of the space scale (0 is a legal step)
  2. one gutter per width, and it is the gutter token or a step of the scale, the same both sides
  3. heading to body and body to action gaps are steps of the scale
  4. no orphan: no gap between neighbours in a fold larger than the largest step
  5. one start axis per fold: blocks stacked in a fold start on one line within 2px (centred blocks
     sit on the centre line instead; blocks side by side are columns, not a misalignment)

The scale is job.json `space_scale`; when that is empty it is read off the page's own tokens
(--s1.., --s-1.., --space-1..), never restated. Folds are `limits.section_selector` when set, or the
children of <main> (or of <body>), descending through a single wrapper.
"""
from common import register

G = 'spacing'
_T = 'an earlier job spacing.py: its negative control, 60px fold padding, a 19px inset, a heading 5px off its paragraph'
CHECKS = register(G, {
    'fold-padding': {
        'protects': 'every fold breathes by the same scale, so the rhythm reads as designed',
        'limit': '{spacing_off_scale} paddings off the scale (within {spacing_tolerance_px}px)',
        'taught_by': _T},
    'one-gutter': {
        'protects': 'one side margin per width, the same on both sides',
        'limit': 'one gutter per width, equal left and right, on the gutter token or the scale',
        'taught_by': _T},
    'rhythm': {
        'protects': 'heading to body and body to action gaps come from the scale',
        'limit': '{spacing_off_scale} gaps off the scale (within {spacing_tolerance_px}px)',
        'taught_by': _T},
    'no-orphan': {
        'protects': 'nothing floats away from what it belongs to',
        'limit': 'no gap between neighbours larger than the largest step',
        'taught_by': _T},
    'start-axis': {
        'protects': 'a fold\'s content starts on one line, so the eye has one edge to follow',
        'limit': 'stacked blocks start within {align_tolerance_px}px of one axis',
        'taught_by': _T},
})

MEASURE_JS = r"""([scale, tol, alignTol, sel, gutterVar]) => {
  const L = __sc, num = v => parseFloat(v) || 0;
  const onScale = v => Math.abs(v) <= tol || scale.some(t => Math.abs(v - t) <= tol);
  const maxStep = Math.max(...scale);
  const probe = v => {
    const bs = getComputedStyle(document.body);
    if (!v || !(bs.getPropertyValue(v) || '').trim()) return null;
    const d = document.createElement('div');
    d.style.cssText = 'position:absolute;left:0;top:0;height:1px;visibility:hidden;width:var(' + v + ')';
    document.body.appendChild(d); const w = d.getBoundingClientRect().width; d.remove(); return w;
  };
  const gutter = probe(gutterVar);
  const skipTag = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'LINK', 'META']);
  const inFlow = el => { const p = getComputedStyle(el).position; return p !== 'absolute' && p !== 'fixed'; };
  const kidsOf = el => [...el.children].filter(c => !skipTag.has(c.tagName) && L.vis(c) && inFlow(c));
  let folds;
  if (sel) folds = [...document.querySelectorAll(sel)];
  else {
    const main = document.querySelector('main');
    folds = main ? [...document.querySelectorAll('body > header, body > footer')].concat([...main.children])
                 : [...document.body.children];
  }
  folds = folds.filter(f => !skipTag.has(f.tagName) && L.vis(f) && inFlow(f) && f.getBoundingClientRect().height >= 40);
  for (let i = 0; i < 3 && !sel; i++) {
    const main = folds.filter(f => f.tagName !== 'HEADER' && f.tagName !== 'FOOTER');
    if (main.length === 1 && kidsOf(main[0]).length >= 2) folds = folds.filter(f => f !== main[0]).concat(kidsOf(main[0]));
    else break;
  }
  folds.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
  const name = (f, i) => (f.id ? '#' + f.id : L.desc(f).split(' ')[0]) + ' (fold ' + (i + 1) + ')';
  const inner = f => { let n = f; for (let d = 0; d < 3; d++) { const k = kidsOf(n); if (k.length === 1 && k[0].getBoundingClientRect().height > n.getBoundingClientRect().height * 0.5) n = k[0]; else break; } return n; };
  const pad = [], gut = [], rhythm = [], orphan = [], axis = [], gutters = new Set();
  folds.forEach((f, i) => {
    const nm = name(f, i), inn = inner(f);
    // 1. padding: the fold's own, or its wrapper's when the fold has none
    let cs = getComputedStyle(f);
    if (!num(cs.paddingTop) && !num(cs.paddingBottom) && inn !== f) cs = getComputedStyle(inn);
    for (const [side, v] of [['top', num(cs.paddingTop)], ['bottom', num(cs.paddingBottom)]])
      if (!onScale(v)) pad.push(nm + ' padding-' + side + ' ' + Math.round(v));
    // 2. the gutter is on whichever box holds it
    let holder = null;
    for (let n = f, d = 0; n && d < 4; d++) {
      if (num(getComputedStyle(n).paddingLeft) || num(getComputedStyle(n).paddingRight)) { holder = n; break; }
      const k = kidsOf(n); n = k.length === 1 ? k[0] : null;
    }
    if (holder) {
      const hs = getComputedStyle(holder), pl = num(hs.paddingLeft), pr = num(hs.paddingRight);
      gutters.add(Math.round(pl));
      if (Math.abs(pl - pr) > tol) gut.push(nm + ' left ' + Math.round(pl) + ' vs right ' + Math.round(pr));
      else if (!(gutter !== null && Math.abs(pl - gutter) <= tol) && !onScale(pl))
        gut.push(nm + ' inline ' + Math.round(pl) + ' is neither the gutter (' + (gutter === null ? 'no token' : Math.round(gutter)) + ') nor a step');
    }
    // 3. heading to what follows it, and body to action
    for (const h of f.querySelectorAll('h1, h2, h3, h4, h5, h6, [role="heading"]')) {
      if (!L.vis(h) || !inFlow(h)) continue;
      let n = h.nextElementSibling;
      while (n && (!L.vis(n) || !inFlow(n))) n = n.nextElementSibling;
      if (!n) continue;
      const g = n.getBoundingClientRect().top - h.getBoundingClientRect().bottom;
      if (g > tol && !onScale(g)) rhythm.push(nm + ' heading "' + (h.textContent || '').trim().slice(0, 20) + '" to next ' + Math.round(g));
    }
    for (const a of f.querySelectorAll('button, [role="button"], input[type="submit"], a')) {
      if (!L.vis(a) || a.closest('p, li, dd, td, figcaption, nav, header')) continue;
      const d = getComputedStyle(a).display;
      if (a.tagName === 'A' && d === 'inline') continue;
      let blk = a;
      while (blk.parentElement && blk.parentElement !== f && !blk.previousElementSibling) blk = blk.parentElement;
      let prev = blk.previousElementSibling;
      while (prev && (!L.vis(prev) || !inFlow(prev))) prev = prev.previousElementSibling;
      if (!prev) continue;
      const pr = prev.getBoundingClientRect(), br = blk.getBoundingClientRect();
      if (br.left >= pr.right - 1) continue;           // side by side, not stacked
      const g = br.top - pr.bottom;
      if (g > tol && !onScale(g)) rhythm.push(nm + ' body to action "' + (a.textContent || '').trim().slice(0, 16) + '" ' + Math.round(g));
    }
    // 4. orphans and 5. the start axis, over the fold's own children
    const kids = kidsOf(inn);
    for (let k = 1; k < kids.length; k++) {
      const g = kids[k].getBoundingClientRect().top - kids[k - 1].getBoundingClientRect().bottom;
      if (g > maxStep + tol) orphan.push(nm + ' gap ' + Math.round(g) + 'px before ' + L.desc(kids[k]).slice(0, 40));
    }
    const rects = kids.map(c => c.getBoundingClientRect());
    const ir = inn.getBoundingClientRect(), is = getComputedStyle(inn);
    const cl = ir.left + num(is.paddingLeft) + num(is.borderLeftWidth), cr = ir.right - num(is.paddingRight) - num(is.borderRightWidth);
    const stacked = kids.filter((c, a) => rects.every((r, b) => a === b || r.bottom <= rects[a].top + 1 || r.top >= rects[a].bottom - 1));
    const lefts = [];
    for (const c of stacked) {
      const r = c.getBoundingClientRect();
      const centred = Math.abs((r.left - cl) - (cr - r.right)) <= alignTol && r.width < (cr - cl) - 2 * alignTol;
      if (!centred) lefts.push([r.left, c]);
    }
    if (lefts.length > 1) {
      const counts = {};
      for (const [x] of lefts) { const kx = Math.round(x); counts[kx] = (counts[kx] || 0) + 1; }
      const mode = +Object.entries(counts).sort((p, q) => q[1] - p[1])[0][0];
      for (const [x, c] of lefts) if (Math.abs(x - mode) > alignTol)
        axis.push(nm + ' ' + L.desc(c).slice(0, 36) + ' starts ' + Math.round(x - mode) + 'px off the axis');
    }
  });
  return {n: folds.length, pad, gut, rhythm, orphan, axis, gutters: [...gutters], gutter};
}"""

TOKEN_SCALE_JS = r"""() => {
  const rs = getComputedStyle(document.documentElement), out = [];
  const probe = v => { const d = document.createElement('div'); d.style.cssText = 'position:absolute;visibility:hidden;height:1px;width:var(' + v + ')'; document.body.appendChild(d); const w = d.getBoundingClientRect().width; d.remove(); return w; };
  for (const pre of ['--s', '--s-', '--space-', '--sp-', '--space']) for (let i = 0; i <= 14; i++) {
    const v = pre + i; if ((rs.getPropertyValue(v) || '').trim()) { const w = probe(v); if (w > 0) out.push(Math.round(w * 100) / 100); }
  }
  return [...new Set(out)].sort((a, b) => a - b);
}"""


def after_walk(sess, pg, page, size, st):
    scale = [float(x) for x in (sess.job.get('space_scale', default=[]) or [])]
    src = 'job.json space_scale'
    if not scale:
        scale = pg.evaluate(TOKEN_SCALE_JS)
        src = 'the page\'s space tokens'
    if not scale:
        st['skip'] = 'no space scale: job.json space_scale is empty and the page has no --s1.. or --space-.. tokens'
        return
    st['scale'] = scale
    st['src'] = src
    gv = (sess.job.get('grid') or {}).get('gutter_var')
    st['m'] = pg.evaluate(MEASURE_JS, [scale, sess.L['spacing_tolerance_px'], sess.L['align_tolerance_px'],
                                       sess.L.get('section_selector'), gv])


def finish(sess, page, size, st, shots):
    ev = shots['full']
    if st.get('skip'):
        for c in CHECKS:
            sess.rec(G, c, 'skip', st['skip'], page, size, 'chromium')
        return
    m = st['m']
    lim = sess.L['spacing_off_scale']
    base = '%d folds, scale %s from %s' % (m['n'], [round(x, 1) for x in st['scale']], st['src'])

    def out(check, bad, ok_text, limit_n=lim):
        sess.rec(G, check, 'pass' if len(bad) <= limit_n else 'fail',
                 ('%d: %s' % (len(bad), '; '.join(bad[:6]))) if bad else ok_text, page, size, 'chromium', evidence=ev)

    if m['n'] == 0:
        for c in CHECKS:
            sess.rec(G, c, 'skip', 'no folds found (set limits.section_selector in job.json)', page, size, 'chromium')
        return
    out('fold-padding', m['pad'], 'every fold padding on the scale; ' + base)
    gbad = list(m['gut'])
    if len(m['gutters']) > 1:
        gbad.insert(0, 'more than one gutter at this width: %s' % sorted(m['gutters']))
    out('one-gutter', gbad, 'one gutter %s (token %s)' % (m['gutters'] or 'none held by padding',
                                                          None if m['gutter'] is None else round(m['gutter'], 1)), 0)
    out('rhythm', m['rhythm'], 'heading to body and body to action on the scale')
    out('no-orphan', m['orphan'], 'no gap over the largest step (%s)' % max(st['scale']), 0)
    out('start-axis', m['axis'], 'every fold starts on one axis', 0)
