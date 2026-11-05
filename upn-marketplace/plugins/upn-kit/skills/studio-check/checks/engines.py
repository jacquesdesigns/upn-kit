"""ENGINES , Chromium, WebKit and Firefox, scrolled the way people scroll.

- Small wheel steps: 24px every 16ms (a trackpad, not a mouse wheel's big notch) through the whole
  page. It must reach the foot, and never move backwards more than twice in a row: the WebKit trap,
  where scroll-behavior: smooth and a scroll-fired ScrollTrigger.refresh() hold Safari at the top
  while Chrome passes.
- Touch scroll (Chromium, CDP touch events): a finger drag moves the page, and drags reach the foot.
- The address bar: a 390x844 page resized to 390x780, as a phone's bar shows and hides. Full-height
  sections must all follow the same rule (all track the new height, or all keep the old one) and every
  pin must still start where its spacer is.

An engine that is not installed is reported as a skip with the reason, never a pass.
"""
from common import register, shot_name
from motion import PINS_JS

G = 'engines'
CHECKS = register(G, {
    'wheel-steps': {
        'protects': 'a trackpad scroll reaches the whole page in every engine',
        'limit': 'reaches the foot; never more than {backward_runs} backward steps in a row ({wheel_step_px}px every {wheel_interval_ms}ms)',
        'taught_by': 'the studio build notes: the WebKit smooth-scroll trap on an older MacBook in Safari'},
    'touch-scroll': {
        'protects': 'a finger drag moves the page and reaches the foot',
        'limit': 'the first drag moves the page by at least a quarter of the drag; drags reach the foot; no backward run over {backward_runs}',
        'taught_by': 'the build system, 29 Sep: nothing had dragged a finger through a page before'},
    'address-bar-resize': {
        'protects': 'when a phone\'s address bar hides or shows, full-height sections and pins stay consistent',
        'limit': 'full-height sections all track or all hold; pins within {pin_drift_px}px; no sideways pan',
        'taught_by': 'an earlier iOS job, its full-bleed rules: 100dvh and the plate that blued the live grid'},
})

FULL_JS = r"""() => {
  const L = __sc, vh = innerHeight, out = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (L.hiddenTree(el) || !L.vis(el)) continue;
    const p = getComputedStyle(el).position;
    if (p === 'fixed') continue;
    const h = el.getBoundingClientRect().height;
    if (Math.abs(h - vh) > 2) continue;
    if (out.some(o => o.el.contains(el))) continue;
    out.push({el, k: L.key(el), d: L.desc(el).slice(0, 50), h: Math.round(h)});
  }
  return out.map(({k, d, h}) => ({k, d, h}));
}"""

HEIGHTS_JS = r"""(keys) => {
  const L = __sc, want = new Set(keys), out = {};
  for (const el of document.body.querySelectorAll('*')) { const k = L.key(el); if (want.has(k)) out[k] = Math.round(el.getBoundingClientRect().height); }
  const se = document.scrollingElement || document.documentElement;
  return {h: out, vh: innerHeight, pan: se.scrollWidth - L.vw()};
}"""


def _runs(ys):
    worst = run = 0
    for a, b in zip(ys, ys[1:]):
        if b < a - 0.5:
            run += 1
            worst = max(worst, run)
        else:
            run = 0
    return worst


def wheel(sess, page, engine):
    size = (1440, 900)
    ctx, why = sess.context(engine, size, touch=False)
    if not ctx:
        sess.rec(G, 'wheel-steps', 'skip', why, page, size, engine)
        return
    try:
        pg = sess.open(ctx, page)
        if engine != 'chromium':
            p = sess.shots / shot_name(page.get('name') or 'page', size[0], size[1], engine)
            try:
                pg.screenshot(path=str(p), full_page=True)
            except Exception:
                pass
        maxy = pg.evaluate('() => __sc.maxY()')
        if maxy < 24:
            sess.rec(G, 'wheel-steps', 'skip', 'the page does not scroll (%dpx)' % maxy, page, size, engine)
            return
        pg.mouse.move(size[0] * 0.5, size[1] * 0.5)
        step, gap = sess.L['wheel_step_px'], sess.L['wheel_interval_ms']
        cap = min(4000, int(maxy / step * 2.5) + 80)
        ys, at_foot, n = [pg.evaluate('() => __sc.y()')], 0, 0
        while n < cap:
            pg.mouse.wheel(0, step)
            pg.wait_for_timeout(gap)
            y = pg.evaluate('() => __sc.y()')
            ys.append(y)
            n += 1
            if n % 25 == 0:
                maxy = pg.evaluate('() => __sc.maxY()')
            if y >= maxy - 2:
                at_foot += 1
                if at_foot >= 8:
                    break
        pg.wait_for_timeout(1200)
        final, maxy = pg.evaluate('() => [__sc.y(), __sc.maxY()]')
    finally:
        ctx.close()
    back = _runs(ys)
    reached = final >= maxy - 2
    ok = reached and back <= sess.L['backward_runs']
    sess.rec(G, 'wheel-steps', 'pass' if ok else 'fail',
             '%d steps; %s (at %d of %d); longest backward run %d' % (
                 n, 'reached the foot' if reached else 'did NOT reach the foot', final, maxy, back),
             page, size, engine)


def touch(sess, page):
    size = (390, 844)
    ctx, why = sess.context('chromium', size, touch=True)
    if not ctx:
        sess.rec(G, 'touch-scroll', 'skip', why, page, size, 'chromium')
        return
    try:
        pg = sess.open(ctx, page)
        cdp = ctx.new_cdp_session(pg)
        maxy = pg.evaluate('() => __sc.maxY()')
        if maxy < 24:
            sess.rec(G, 'touch-scroll', 'skip', 'the page does not scroll (%dpx)' % maxy, page, size, 'chromium')
            return
        drag = sess.L['touch_drag_px']
        x, y0 = size[0] * 0.85, size[1] * 0.75
        ys = [pg.evaluate('() => __sc.y()')]
        first = None
        cap = min(120, int(maxy / (drag * 0.5)) + 6)
        for i in range(cap):
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y0}]})
            for k in range(1, 13):
                cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x, 'y': y0 - drag * k / 12.0}]})
                pg.wait_for_timeout(16)
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
            pg.wait_for_timeout(450)
            y = pg.evaluate('() => __sc.y()')
            ys.append(y)
            if first is None:
                first = y - ys[0]
            maxy = pg.evaluate('() => __sc.maxY()')
            if y >= maxy - 2:
                break
        final, maxy = pg.evaluate('() => [__sc.y(), __sc.maxY()]')
    finally:
        ctx.close()
    back = _runs(ys)
    moved = first is not None and first >= drag * 0.25
    reached = final >= maxy - 2
    ok = moved and reached and back <= sess.L['backward_runs']
    sess.rec(G, 'touch-scroll', 'pass' if ok else 'fail',
             'first %dpx drag moved the page %dpx; %d drags; %s (at %d of %d); longest backward run %d' % (
                 drag, first or 0, len(ys) - 1, 'reached the foot' if reached else 'did NOT reach the foot', final, maxy, back),
             page, size, 'chromium')


def address_bar(sess, page, engine):
    size = (390, 844)
    short = sess.L['address_bar_height']
    ctx, why = sess.context(engine, size, touch=True)
    if not ctx:
        sess.rec(G, 'address-bar-resize', 'skip', why, page, size, engine)
        return
    try:
        pg = sess.open(ctx, page)
        if engine != 'chromium':
            p = sess.shots / shot_name(page.get('name') or 'page', size[0], size[1], engine)
            try:
                pg.screenshot(path=str(p), full_page=True)
            except Exception:
                pass
        full = pg.evaluate(FULL_JS)
        pins0 = pg.evaluate(PINS_JS) or []
        pg.set_viewport_size({'width': size[0], 'height': short})
        pg.wait_for_timeout(900)
        after = pg.evaluate(HEIGHTS_JS, [f['k'] for f in full])
        pins1 = pg.evaluate(PINS_JS) or []
    finally:
        ctx.close()
    problems, kinds = [], set()
    for f in full:
        h = after['h'].get(str(f['k']), after['h'].get(f['k']))
        if h is None:
            problems.append('%s is gone after the resize' % f['d'])
            continue
        if abs(h - short) <= 2:
            kinds.add('tracks')
        elif abs(h - size[1]) <= 2:
            kinds.add('holds')
        else:
            kinds.add('other')
            problems.append('%s became %dpx (neither %d nor %d)' % (f['d'], h, short, size[1]))
    if len(kinds - {'other'}) > 1:
        problems.append('full-height sections disagree: some track the bar, some hold (%s)' % ', '.join(sorted(kinds)))
    lim = sess.L['pin_drift_px']
    for r in pins1:
        if 'drift' in r and r['drift'] > lim:
            problems.append('pin %s starts %spx from its spacer after the resize' % (r['d'], r['drift']))
    if after['pan'] > 0:
        problems.append('the page pans %dpx sideways after the resize' % after['pan'])
    measured_pins = [r for r in pins1 if 'drift' in r]
    if not full and not measured_pins and not problems:
        sess.rec(G, 'address-bar-resize', 'skip', 'no full-height sections and no pins: nothing here depends on the bar',
                 page, size, engine)
        return
    sess.rec(G, 'address-bar-resize', 'fail' if problems else 'pass',
             '; '.join(problems[:6]) if problems else '%d full-height sections (%s), %d pins within %dpx, 844 to %d' % (
                 len(full), ', '.join(sorted(kinds)) or 'none', len(measured_pins), lim, short),
             page, size, engine)


def run(sess):
    engines = sess.engines()
    for page in sess.pages:
        nm = page.get('name')
        for engine in ['chromium', 'webkit', 'firefox']:
            if engine not in engines:
                for c in ('wheel-steps', 'address-bar-resize'):
                    sess.rec(G, c, 'skip', 'quick run is Chromium only; %s runs in the full run' % engine,
                             page, (1440, 900) if c == 'wheel-steps' else (390, 844), engine)
                continue
            sess.guard(G, 'wheel-steps', lambda: wheel(sess, page, engine), page=nm, size=(1440, 900), engine=engine)
            sess.guard(G, 'address-bar-resize', lambda: address_bar(sess, page, engine), page=nm, size=(390, 844), engine=engine)
        sess.guard(G, 'touch-scroll', lambda: touch(sess, page), page=nm, size=(390, 844), engine='chromium')
