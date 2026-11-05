"""TYPE AND COLOUR , the real face renders, and every word can be read against what is behind it.

Fonts: every declared family (job.json `type.families`) that the page's text asks for must actually
render: a loaded face in document.fonts, and a measured width that differs from the fallbacks (a face
that never arrived renders in the fallback and measures the same). Checked per (family, weight,
style) the page really uses, at 390 and 1440.

Contrast: every visible text element against its first opaque ancestor, an earlier job's method: an ancestor's
painted ::before or ::after flood counts as the ground when it covers the box and is not clipped away;
translucent layers are composited down; the text's own effective opacity is applied. WCAG AA: 4.5:1,
or 3:1 at 24px and over (18.66px bold). Text sitting on a picture, a film or a gradient cannot be
measured from colours and is counted, not passed.
"""
import re

from common import register

G = 'type_colour'
CHECKS = register(G, {
    'fonts-render': {
        'protects': 'the job\'s typeface is what people see, never a fallback that happens to look close',
        'limit': 'every declared family the page uses is loaded and measures unlike the fallback',
        'taught_by': 'v1 PLAN.md: the Adobe Fonts kit only loads on 127.0.0.1 or localhost'},
    'contrast': {
        'protects': 'every word can be read against what is actually behind it',
        'limit': 'WCAG {contrast}: {contrast_normal}:1, {contrast_large}:1 at {large_text_px}px and over',
        'taught_by': 'v1 BUILD-LOG, 28 Sep: cream on paper at 1.1:1, grey on stone at 4.2:1'},
})

FONTS_JS = r"""(declared) => {
  const L = __sc, norm = s => (s || '').replace(/["']/g, '').trim().toLowerCase();
  const want = new Set(declared.map(norm));
  const used = {}, other = {};
  for (const el of L.textLeaves()) {
    const cs = getComputedStyle(el);
    const fam = norm(cs.fontFamily.split(',')[0]);
    const key = fam + '|' + cs.fontWeight + '|' + cs.fontStyle;
    const n = L.ownText(el).length;
    if (want.has(fam)) used[key] = (used[key] || 0) + n; else other[fam] = (other[fam] || 0) + n;
  }
  const faces = [...document.fonts].map(f => ({family: norm(f.family), status: f.status, weight: f.weight, style: f.style}));
  const cv = document.createElement('canvas').getContext('2d');
  const sample = 'Hamburgefonstiv 0123456789 Qqg';
  const width = f => { cv.font = f; return cv.measureText(sample).width; };
  const rows = Object.entries(used).map(([key, chars]) => {
    const [fam, weight, style] = key.split('|');
    const st = style === 'normal' ? '' : style + ' ';
    const renders = ['monospace', 'serif', 'sans-serif'].every(fb =>
      Math.abs(width(st + weight + ' 48px "' + fam + '", ' + fb) - width(st + weight + ' 48px ' + fb)) > 0.5);
    const loaded = faces.filter(f => f.family === fam && f.status === 'loaded').length;
    const known = faces.filter(f => f.family === fam).length;
    return {fam, weight, style, chars, renders, loaded, known};
  });
  return {rows, other, declared: [...want]};
}"""

CONTRAST_JS = r"""([paper]) => {
  const L = __sc, out = [];
  const rgba = c => { const m = (c || '').match(/[\d.]+/g); if (!m || m.length < 3) return null; return [+m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1]; };
  const flood = n => {
    for (const which of ['::before', '::after']) {
      const p = getComputedStyle(n, which);
      if (!p || p.content === 'none' || p.position === 'static' || p.display === 'none' || p.visibility === 'hidden') continue;
      const pa = parseFloat(p.opacity); if (pa === 0) continue;
      const cp = p.clipPath;
      if (cp && cp !== 'none') { const ins = cp.match(/^inset\(([^)]*)\)$/); if (!ins || !ins[1].trim().split(/\s+/).every(v => parseFloat(v) === 0)) continue; }
      const c = rgba(p.backgroundColor); if (!c) continue;
      const a = c[3] * (isNaN(pa) ? 1 : pa); if (a <= 0) continue;
      const covers = ['top', 'right', 'bottom', 'left'].every(s => p[s] === '0px') || (p.width === '100%' && p.height === '100%');
      if (!covers) continue;
      return [c[0], c[1], c[2], a];
    }
    return null;
  };
  for (const el of L.textLeaves()) {
    const rr = L.rangeRect(el);
    if (!L.inView(rr)) continue;
    const cs = getComputedStyle(el);
    const fg = rgba(cs.color); if (!fg) continue;
    let layers = [], solid = null, unmeasurable = null;
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.backgroundImage && s.backgroundImage !== 'none') { unmeasurable = 'on ' + (s.backgroundImage.startsWith('url') ? 'a picture' : 'a gradient'); break; }
      const own = rgba(s.backgroundColor);
      const cands = [flood(n), own && own[3] > 0 ? own : null].filter(Boolean);
      let stop = false;
      for (const c of cands) { if (c[3] >= 1) { solid = c.slice(0, 3); stop = true; break; } layers.push(c); }
      if (stop) break;
    }
    if (!unmeasurable) {
      // a picture, film or canvas painted under the words, and not one of their ancestors
      const cx = Math.min(Math.max(rr.left + rr.width / 2, 1), innerWidth - 1), cy = Math.min(Math.max(rr.top + rr.height / 2, 1), innerHeight - 1);
      for (const u of document.elementsFromPoint(cx, cy)) {
        if (u === el || el.contains(u)) continue;
        if (u.contains(el)) break;
        if (u.matches('img, video, canvas, picture, iframe') && L.vis(u)) { unmeasurable = 'over ' + u.tagName.toLowerCase(); break; }
      }
    }
    let bg = solid || paper;
    for (let i = layers.length - 1; i >= 0; i--) { const [r, g, b, a] = layers[i]; bg = [r * a + bg[0] * (1 - a), g * a + bg[1] * (1 - a), b * a + bg[2] * (1 - a)]; }
    const a = fg[3] * L.effOpacity(el);
    const col = [fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a)];
    out.push({k: L.key(el), d: L.desc(el), fg: col.map(Math.round), bg: bg.map(Math.round), size: parseFloat(cs.fontSize),
              weight: parseInt(cs.fontWeight) || 400, un: unmeasurable});
  }
  return out;
}"""


def _lum(c):
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def before_walk(sess, pg, page, size, st):
    st['contrast'] = {}
    st['fonts'] = None
    if size[0] in sess.job.sizes['type_colour_fonts'] or sess.quick:
        fams = (sess.job.get('type') or {}).get('families') or []
        st['fonts'] = ('skip', 'job.json declares no type.families') if not fams else ('run', fams)


def at_fold(sess, pg, page, size, k, st):
    for r in pg.evaluate(CONTRAST_JS, [[255, 255, 255]]):
        st['contrast'].setdefault(r['k'], (k, r))


def after_walk(sess, pg, page, size, st):
    if st['fonts'] and st['fonts'][0] == 'run':
        st['fonts'] = ('done', pg.evaluate(FONTS_JS, st['fonts'][1]))


def finish(sess, page, size, st, shots):
    L = sess.L
    f = st['fonts']
    if f:
        if f[0] == 'skip':
            sess.rec(G, 'fonts-render', 'skip', f[1], page, size, 'chromium')
        else:
            res = f[1]
            rows = res['rows']
            bad = [r for r in rows if not r['renders'] or not r['loaded']]
            if not rows:
                others = ', '.join('%s (%d chars)' % (k or 'unnamed', v) for k, v in sorted(res['other'].items(), key=lambda x: -x[1])[:4])
                sess.rec(G, 'fonts-render', 'fail', 'no text on the page asks for %s; it renders %s' % (res['declared'], others or 'nothing'),
                         page, size, 'chromium', evidence=shots['folds'][:1])
            else:
                txt = '; '.join('%s %s %s: %s' % (r['fam'], r['weight'], r['style'],
                                                  'renders' if r['renders'] and r['loaded'] else
                                                  ('falls back (%d faces known, %d loaded)' % (r['known'], r['loaded'])))
                                for r in rows[:8])
                sess.rec(G, 'fonts-render', 'fail' if bad else 'pass', txt, page, size, 'chromium',
                         evidence=shots['folds'][:1])
    items = list(st['contrast'].values())
    if not items:
        sess.rec(G, 'contrast', 'skip', 'no visible text to measure', page, size, 'chromium')
        return
    fails, unm, worst = [], 0, None
    for k, r in items:
        if r['un']:
            unm += 1
            continue
        c = ratio(r['fg'], r['bg'])
        large = r['size'] >= L['large_text_px'] or (r['size'] >= L['large_bold_px'] and r['weight'] >= 700)
        need = L['contrast_large'] if large else L['contrast_normal']
        if worst is None or c - need < worst[0]:
            worst = (c - need, c, need, r)
        if c + 1e-6 < need:
            fails.append((k, c, need, r))
    note = '; %d over a picture or gradient, not measurable' % unm if unm else ''
    if fails:
        fails.sort(key=lambda x: x[1] - x[2])
        txt = '; '.join('fold %d %s %.2f:1 (needs %.1f) rgb%s on rgb%s' % (k, r['d'], c, need, tuple(r['fg']), tuple(r['bg']))
                        for k, c, need, r in fails[:5])
        ev = sorted({shots['folds'][k - 1] for k, _, _, _ in fails if k - 1 < len(shots['folds'])})[:6]
        sess.rec(G, 'contrast', 'fail', '%d below AA: %s%s' % (len(fails), txt, note), page, size, 'chromium', evidence=ev)
    elif worst:
        sess.rec(G, 'contrast', 'pass', 'worst %.2f:1 (needs %.1f) on %s%s' % (worst[1], worst[2], worst[3]['d'], note),
                 page, size, 'chromium', evidence=shots['folds'][:1])
    else:
        sess.rec(G, 'contrast', 'skip', 'all %d text elements sit over pictures or gradients%s' % (unm, note), page, size, 'chromium')
