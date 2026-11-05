"""CONTROLS , a real tap, then assert what OPENED.

Every visible interactive element, at 390 (touch) and 1440 (mouse): scrolled to the middle of the
screen, it must be the thing under its own centre (elementFromPoint, never .click(), which fires on a
covered element too), and at 390 it must be at least 44px (a link inside a sentence is exempt, a link
in a list or a nav is measured on its height, which is what a thumb needs).

Every job.json `flows` entry runs with a real touchscreen.tap (touch viewports) or mouse click, after
the same hit test, and asserts the RESULT each step names. Each menu or disclosure on each page is also
opened mid-page, not only at the top, asserted open by what appeared on screen, closed with its own
close control, and the page must come back where it was and still scroll.

Flow steps: {"tap": sel} {"click": sel} (add "navigates": true when it goes to a new page),
{"expect_visible": sel, "expect_min_height": px, "expect_min_width": px}, {"expect_hidden": sel},
{"expect_url": "part of the URL"}, {"expect_text": "words", "in": sel}, {"scroll_to": px | sel | "bottom"},
{"type": "text", "into": sel}, {"press": "Escape"}, {"wait": ms}, {"back": true}, {"goto": "page name"}.
A flow may name its starting "page" (a job.json page name); otherwise it starts on the first page.
"""
from common import register, safe_name

G = 'controls'
CHECKS = register(G, {
    'hit-testable': {
        'protects': 'every control is on top where it is drawn, so a press lands on it',
        'limit': '0 covered controls (elementFromPoint at the centre, scrolled to mid-screen)',
        'taught_by': 'the studio build notes: 955 an earlier job gates green while the phone menu never opened'},
    'target-size': {
        'protects': 'a thumb hits the control and not its neighbour',
        'limit': 'at least {target_px}px at 390 (height only for a link in a list or nav; a link in a sentence is exempt)',
        'taught_by': 'an earlier job site test.py: the 44px hit test at 390'},
    'flow': {
        'protects': 'what the job says a person can do, they can do: a real press, and what it opened is on screen',
        'limit': 'every step\'s expected result holds',
        'taught_by': 'the studio build notes: the an earlier job phone menu never opened while its gate was green'},
    'flows-listed': {
        'protects': 'the job names what a person must be able to do, so the kit can press it',
        'limit': 'job.json lists at least one flow',
        'taught_by': 'the build system, 29 Sep: a flow nobody lists is a flow nobody presses'},
    'menu-opens-and-closes': {
        'protects': 'a menu or disclosure opened mid-page shows its panel, closes, and gives the page back',
        'limit': 'opens (panel on screen), closes, scroll within 4px of where it was, page still scrolls',
        'taught_by': 'an earlier job menu.py: open it mid-page, not just at the top'},
})

CONTROL_SEL = ('a[href], button, summary, input:not([type="hidden"]), select, textarea, [role="button"], '
               '[role="link"], [role="tab"], [role="menuitem"]')

PROBE_JS = r"""([sel, min, cap]) => {
  const L = __sc, covered = [], small = [], exempt = [], offscreen = [];
  let n = 0;
  const y0 = L.y();
  for (const el of document.querySelectorAll(sel)) {
    if (n >= cap) break;
    if (el.closest('[aria-hidden="true"], [inert]')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.pointerEvents === 'none') continue;
    if (!el.getClientRects().length) continue;
    let r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (L.effOpacity(el) <= 0.05) continue;
    n++;
    el.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'});
    r = el.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > L.vw()) { offscreen.push(L.desc(el)); continue; }
    const x = Math.min(r.right - 1, Math.max(r.left + 1, r.left + r.width / 2));
    const y = Math.min(r.bottom - 1, Math.max(r.top + 1, r.top + r.height / 2));
    if (x >= 0 && y >= 0 && x <= L.vw() && y <= innerHeight) {
      const top = document.elementFromPoint(x, y);
      const lab = top && top.closest && top.closest('label');
      const ok = top && (el.contains(top) || top.contains(el) || (lab && (lab.control === el || lab.contains(el))));
      if (!ok) covered.push(L.desc(el).slice(0, 60) + ' under ' + (top ? L.desc(top).slice(0, 40) : 'nothing'));
    }
    if (min) {
      const inline = cs.display === 'inline';
      const running = el.tagName === 'A' && inline && el.closest('p, dd, td, figcaption, blockquote');
      if (running) { exempt.push(L.desc(el)); continue; }
      const listy = el.tagName === 'A' && !!el.closest('li, nav');
      const w = el.offsetWidth || r.width, h = el.offsetHeight || r.height;
      if (listy ? h < min : (w < min || h < min)) small.push(L.desc(el).slice(0, 50) + ' ' + Math.round(w) + 'x' + Math.round(h));
    }
  }
  L.to(y0);
  return {n, covered, small, exempt: exempt.length, offscreen: offscreen.length};
}"""

HIT_JS = r"""(sel) => {
  const L = __sc;
  const el = [...document.querySelectorAll(sel)].find(e => L.vis(e)) || document.querySelector(sel);
  if (!el) return {err: 'nothing matches ' + sel};
  const s = getComputedStyle(el);
  if (s.position !== 'fixed') {
    const r0 = el.getBoundingClientRect();
    if (r0.top < 0 || r0.bottom > innerHeight) el.scrollIntoView({block: 'center', behavior: 'instant'});
  }
  const r = el.getBoundingClientRect();
  if (r.width < 1 || r.height < 1) return {err: sel + ' has no size on screen'};
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  const top = document.elementFromPoint(x, y);
  const ok = top && (el.contains(top) || top.contains(el));
  return {x, y, ok, top: top ? L.desc(top) : 'nothing', me: L.desc(el)};
}"""

SHOWN_JS = r"""(sel) => {
  const L = __sc;
  const els = [...document.querySelectorAll(sel)];
  if (!els.length) return {found: false};
  for (const el of els) {
    if (!L.vis(el) || L.clipHidden(el)) continue;
    const r = el.getBoundingClientRect();
    const vx0 = Math.max(0, r.left), vx1 = Math.min(L.vw(), r.right), vy0 = Math.max(0, r.top), vy1 = Math.min(innerHeight, r.bottom);
    if (vx1 - vx0 < 2 || vy1 - vy0 < 2) continue;
    const top = document.elementFromPoint((vx0 + vx1) / 2, (vy0 + vy1) / 2);
    const onTop = !!(top && (el.contains(top) || top.contains(el)));
    return {found: true, shown: true, onTop, w: Math.round(r.width), h: Math.round(r.height), vh: Math.round(vy1 - vy0)};
  }
  return {found: true, shown: false};
}"""

TOGGLES_JS = r"""(cap) => {
  const L = __sc, out = [];
  const cands = document.querySelectorAll('[aria-expanded], button[aria-controls], [data-menu-button], summary');
  for (const el of cands) {
    if (out.length >= cap) break;
    if (el.closest('[aria-hidden="true"], [inert]')) continue;
    if (!L.vis(el)) continue;
    if (el.getAttribute('aria-expanded') === 'true' || (el.tagName === 'SUMMARY' && el.parentElement.open)) continue;
    el.setAttribute('data-sc-toggle', String(out.length));
    out.push({i: out.length, d: L.desc(el), fixed: L.chrome(el)});
  }
  return out;
}"""

STATE_JS = r"""(i) => {
  const L = __sc, el = document.querySelector('[data-sc-toggle="' + i + '"]');
  if (!el) return {gone: true};
  let target = null;
  const ids = (el.getAttribute('aria-controls') || '').trim().split(/\s+/).filter(Boolean);
  if (ids.length) target = document.getElementById(ids[0]);
  if (!target && el.tagName === 'SUMMARY') target = el.parentElement;
  if (target) target.setAttribute('data-sc-target', String(i));
  let shown = false, onTop = false, h = 0;
  if (target && L.vis(target) && !L.clipHidden(target)) {
    const r = target.getBoundingClientRect();
    const vx0 = Math.max(0, r.left), vx1 = Math.min(L.vw(), r.right), vy0 = Math.max(0, r.top), vy1 = Math.min(innerHeight, r.bottom);
    if (vx1 - vx0 > 2 && vy1 - vy0 > 2) {
      shown = true; h = Math.round(vy1 - vy0);
      const t = document.elementFromPoint((vx0 + vx1) / 2, (vy0 + vy1) / 2);
      onTop = !!(t && (target.contains(t) || t.contains(target) || el.contains(t)));
    }
  }
  const tv = L.vis(el);
  return {expanded: el.getAttribute('aria-expanded'), open: el.tagName === 'SUMMARY' ? el.parentElement.open : null,
          hasTarget: !!target, shown, onTop, h, y: L.y(), toggleVisible: tv};
}"""

CLOSE_JS = r"""(i) => {
  const L = __sc, t = document.querySelector('[data-sc-target="' + i + '"]');
  const pick = [];
  if (t) for (const c of t.querySelectorAll('button, [role="button"], a, [data-close]')) {
    const lab = ((c.getAttribute('aria-label') || '') + ' ' + (c.textContent || '')).trim();
    if ((c.hasAttribute('data-close') || /close|dismiss|×|✕|✖/i.test(lab)) && L.vis(c)) pick.push(c);
  }
  for (const c of document.querySelectorAll('[aria-label*="close" i], [data-close]')) if (L.vis(c) && !pick.includes(c)) pick.push(c);
  const el = pick[0] || document.querySelector('[data-sc-toggle="' + i + '"]');
  if (!el || !L.vis(el)) return null;
  el.setAttribute('data-sc-close', String(i));
  return {sel: '[data-sc-close="' + i + '"]', d: L.desc(el), own: !pick.length};
}"""


def _press(pg, sel, touch, navigates=False):
    h = pg.evaluate(HIT_JS, sel)
    if h.get('err'):
        return h['err']
    if not h['ok']:
        return 'covered: %s is under %s at its centre' % (h['me'][:50], h['top'][:50])

    def go():
        if touch:
            pg.touchscreen.tap(h['x'], h['y'])
        else:
            pg.mouse.move(h['x'], h['y'])
            pg.mouse.click(h['x'], h['y'])
    if navigates:
        with pg.expect_navigation(timeout=15000):
            go()
        try:
            pg.wait_for_load_state('load', timeout=15000)
        except Exception:
            pass
    else:
        go()
    return None


def _wait_for(pg, fn, timeout=2500, step=100):
    t = 0
    last = None
    while t <= timeout:
        last = fn()
        if last[0]:
            return last
        pg.wait_for_timeout(step)
        t += step
    return last


def run_flow(sess, flow, engine):
    name = flow.get('name') or 'unnamed'
    check = 'flow: %s' % name
    size = tuple(flow.get('viewport') or [390, 844])
    touch = sess.is_phone(size)
    ctx, why = sess.context(engine, size, touch=touch)
    if not ctx:
        sess.rec(G, check, 'skip', why, flow.get('page'), size, engine)
        return
    pages = {p.get('name'): p for p in sess.job.get('pages', default=[]) or []}
    start = pages.get(flow.get('page')) or (sess.pages[0] if sess.pages else {'name': 'entry', 'path': sess.job.get('serve', 'entry', default='/')})
    shot = sess.shots / ('flow__%s__%dx%d__%s.png' % (safe_name(name), size[0], size[1], engine))
    pg = None
    try:
        pg = sess.open(ctx, start)
        done, fail = [], None
        steps = flow.get('steps') or []
        if not steps:
            fail = 'the flow has no steps'
        for i, s in enumerate(steps, 1):
            tag = 'step %d' % i
            if 'tap' in s or 'click' in s:
                sel = s.get('tap') or s.get('click')
                err = _press(pg, sel, touch and 'tap' in s, bool(s.get('navigates')))
                if err:
                    fail = '%s %s: %s' % (tag, 'tap' if 'tap' in s else 'click', err)
                    break
                pg.wait_for_timeout(int(s.get('settle', 700)))
                done.append('%s pressed' % sel)
            if 'expect_visible' in s:
                sel = s['expect_visible']
                r = _wait_for(pg, lambda: (lambda x: (x.get('shown') and x.get('onTop'), x))(pg.evaluate(SHOWN_JS, sel)), int(s.get('timeout', 2500)))[1]
                if not r.get('found'):
                    fail = '%s: nothing matches %s' % (tag, sel)
                elif not r.get('shown'):
                    fail = '%s: %s exists but is not on screen' % (tag, sel)
                elif not r.get('onTop'):
                    fail = '%s: %s is on screen but covered at its centre' % (tag, sel)
                elif s.get('expect_min_height') and r['vh'] < s['expect_min_height']:
                    fail = '%s: %s shows %dpx tall on screen, expected at least %d' % (tag, sel, r['vh'], s['expect_min_height'])
                elif s.get('expect_min_width') and r['w'] < s['expect_min_width']:
                    fail = '%s: %s is %dpx wide, expected at least %d' % (tag, sel, r['w'], s['expect_min_width'])
                if fail:
                    break
                done.append('%s visible %dx%d' % (sel, r['w'], r['vh']))
            if 'expect_hidden' in s:
                sel = s['expect_hidden']
                r = _wait_for(pg, lambda: (lambda x: (not x.get('shown'), x))(pg.evaluate(SHOWN_JS, sel)), int(s.get('timeout', 2500)))[1]
                if r.get('shown'):
                    fail = '%s: %s is still on screen' % (tag, sel)
                    break
                done.append('%s hidden' % sel)
            if 'expect_url' in s:
                part = s['expect_url']
                ok = _wait_for(pg, lambda: (part in pg.url, pg.url), 5000)
                if not ok[0]:
                    fail = '%s: URL is %s, expected it to contain %s' % (tag, pg.url, part)
                    break
                done.append('at %s' % part)
            if 'expect_text' in s:
                where = s.get('in') or 'body'
                words = s['expect_text']
                ok = _wait_for(pg, lambda: (words.lower() in (pg.evaluate('(s) => { const e = document.querySelector(s); return e ? e.innerText : ""; }', where) or '').lower(), None), 2500)
                if not ok[0]:
                    fail = '%s: "%s" is not shown in %s' % (tag, words, where)
                    break
                done.append('"%s" shown' % words[:20])
            if 'scroll_to' in s:
                v = s['scroll_to']
                if v == 'bottom':
                    pg.evaluate('() => __sc.to(__sc.maxY())')
                elif isinstance(v, (int, float)):
                    pg.evaluate('(y) => __sc.to(y)', v)
                else:
                    pg.evaluate("(s) => { const e = document.querySelector(s); if (e) e.scrollIntoView({block: 'center', behavior: 'instant'}); }", v)
                pg.wait_for_timeout(500)
            if 'type' in s:
                sel = s.get('into')
                if sel:
                    err = _press(pg, sel, touch)
                    if err:
                        fail = '%s type: %s' % (tag, err)
                        break
                pg.keyboard.type(str(s['type']), delay=20)
            if 'press' in s:
                pg.keyboard.press(s['press'])
                pg.wait_for_timeout(500)
            if 'wait' in s:
                pg.wait_for_timeout(int(s['wait']))
            if s.get('back'):
                with pg.expect_navigation(timeout=15000):
                    pg.go_back()
                pg.wait_for_timeout(500)
            if 'goto' in s:
                target = pages.get(s['goto']) or {'path': s['goto']}
                pg.goto(sess.url(target), wait_until='load')
                pg.wait_for_timeout(800)
        pg.screenshot(path=str(shot))
        sess.rec(G, check, 'fail' if fail else 'pass',
                 fail or ('%d steps held: %s' % (len(steps), '; '.join(done[:8]))),
                 start.get('name'), size, engine, evidence=[sess.rel(shot)])
    except Exception as e:
        try:
            if pg:
                pg.screenshot(path=str(shot))
        except Exception:
            pass
        sess.rec(G, check, 'fail', 'the flow broke: %s: %s' % (type(e).__name__, str(e).splitlines()[0][:200] if str(e) else ''),
                 start.get('name'), size, engine, evidence=[sess.rel(shot)] if shot.exists() else [])
    finally:
        ctx.close()


def disclosures(sess, page, size):
    touch = sess.is_phone(size)
    ctx, why = sess.context('chromium', size, touch=touch)
    if not ctx:
        sess.rec(G, 'menu-opens-and-closes', 'skip', why, page, size, 'chromium')
        return
    try:
        pg = sess.open(ctx, page)
        toggles = pg.evaluate(TOGGLES_JS, sess.L['max_disclosures_per_page'])
        if not toggles:
            sess.rec(G, 'menu-opens-and-closes', 'skip', 'no menu or disclosure toggles on this page (aria-expanded, aria-controls, summary)',
                     page, size, 'chromium')
            return
        for t in toggles:
            i = t['i']
            label = t['d'][:50]
            ev = sess.shots / ('menu__%s__%d__%dx%d__chromium.png' % (safe_name(page.get('name') or 'page'), i, size[0], size[1]))
            # mid-page, not just the top
            pg.evaluate('() => __sc.to(Math.round(__sc.maxY() / 2))')
            pg.wait_for_timeout(500)
            before = pg.evaluate(STATE_JS, i)
            if before.get('gone'):
                continue
            if before['expanded'] is None and before['open'] is None and not before['hasTarget']:
                sess.rec(G, 'menu-opens-and-closes', 'skip', '%s: cannot tell what it opens (no aria-expanded, no aria-controls); '
                         'name it in job.json flows' % label, page, size, 'chromium')
                continue
            # bring an in-page toggle to the middle of the screen; a fixed one is pressed where it is
            pg.evaluate("""(i) => { const e = document.querySelector('[data-sc-toggle="' + i + '"]'); const r = e.getBoundingClientRect();
                if (r.top < 0 || r.bottom > innerHeight) e.scrollIntoView({block: 'center', behavior: 'instant'}); }""", i)
            pg.wait_for_timeout(300)
            y0 = pg.evaluate('() => __sc.y()')
            err = _press(pg, '[data-sc-toggle="%d"]' % i, touch)
            if err:
                sess.rec(G, 'menu-opens-and-closes', 'fail', '%s: cannot press it: %s' % (label, err), page, size, 'chromium')
                continue
            def is_open_(s):
                flag = s['expanded'] == 'true' or s['open'] is True or (s['expanded'] is None and s['open'] is None)
                return flag and (not s['hasTarget'] or (s['shown'] and s['onTop']))
            opened = _wait_for(pg, lambda: (lambda s: (is_open_(s), s))(pg.evaluate(STATE_JS, i)), 2000)[1]
            pg.screenshot(path=str(ev))
            is_open = is_open_(opened)
            if not is_open:
                why = []
                if opened['expanded'] not in ('true', None) or opened['open'] is False:
                    why.append('aria-expanded stayed %r' % opened['expanded'])
                if opened['hasTarget'] and not opened['shown']:
                    why.append('its panel is not on screen')
                elif opened['hasTarget'] and not opened['onTop']:
                    why.append('its panel is on screen but covered')
                sess.rec(G, 'menu-opens-and-closes', 'fail', '%s did not open: %s' % (label, ', '.join(why) or 'nothing changed'),
                         page, size, 'chromium', evidence=[sess.rel(ev)])
                pg.reload(wait_until='load')
                pg.wait_for_timeout(800)
                continue
            close = pg.evaluate(CLOSE_JS, i)
            how = 'Escape'
            if close:
                err = _press(pg, close['sel'], touch)
                how = ('its own button' if close['own'] else close['d'][:30])
                if err:
                    pg.keyboard.press('Escape')
                    how = 'Escape (the close control was covered: %s)' % err[:60]
            else:
                pg.keyboard.press('Escape')
            closed = _wait_for(pg, lambda: (lambda s: (s['expanded'] != 'true' and s['open'] is not True and not (s['hasTarget'] and s['shown'] and s['onTop']), s))(pg.evaluate(STATE_JS, i)), 2000)[1]
            ok_closed = closed['expanded'] != 'true' and closed['open'] is not True and not (closed['hasTarget'] and closed['shown'] and closed['onTop'])
            drift = abs(closed['y'] - y0)
            moved = pg.evaluate('(y) => { const a = __sc.y(); __sc.to(a + 60); const b = __sc.y(); __sc.to(a); return Math.abs(b - a) > 1 || __sc.maxY() < 2; }', 0)
            problems = []
            if not ok_closed:
                problems.append('it did not close with %s' % how)
            if ok_closed and drift > 4:
                problems.append('the page came back %dpx from where it was' % drift)
            if ok_closed and not moved:
                problems.append('the page no longer scrolls after closing')
            sess.rec(G, 'menu-opens-and-closes', 'fail' if problems else 'pass',
                     ('%s: ' % label) + ('; '.join(problems) if problems else 'opened mid-page (panel %dpx on screen), closed with %s, page back within %dpx'
                                           % (opened['h'], how, drift)),
                     page, size, 'chromium', evidence=[sess.rel(ev)])
            if problems:
                pg.reload(wait_until='load')
                pg.wait_for_timeout(800)
    finally:
        ctx.close()


def probe(sess, page, size):
    ctx, why = sess.context('chromium', size)
    if not ctx:
        sess.rec(G, 'hit-testable', 'skip', why, page, size, 'chromium')
        return
    try:
        pg = sess.open(ctx, page)
        # walk once so arrivals have run before hit-testing
        pg.evaluate('async () => { const m = __sc.maxY(); for (let y = 0; y <= m; y += innerHeight * 0.8) { __sc.to(y); await new Promise(r => setTimeout(r, 120)); } __sc.to(0); }')
        pg.wait_for_timeout(400)
        phone = sess.is_phone(size)
        r = pg.evaluate(PROBE_JS, [CONTROL_SEL, sess.L['target_px'] if phone else 0, sess.L['max_controls_per_page']])
        sess.rec(G, 'hit-testable', 'fail' if r['covered'] else 'pass',
                 ('%d of %d covered: %s' % (len(r['covered']), r['n'], '; '.join(r['covered'][:5]))) if r['covered']
                 else '%d controls on top at their centres (%d parked off screen)' % (r['n'], r['offscreen']),
                 page, size, 'chromium')
        if phone:
            sess.rec(G, 'target-size', 'fail' if r['small'] else 'pass',
                     ('%d under %dpx: %s' % (len(r['small']), sess.L['target_px'], '; '.join(r['small'][:6]))) if r['small']
                     else 'every target at least %dpx (%d links in sentences exempt)' % (sess.L['target_px'], r['exempt']),
                     page, size, 'chromium')
    finally:
        ctx.close()


def run(sess):
    for size in sess.size_set('controls'):
        for page in sess.pages:
            sess.guard(G, 'hit-testable', lambda: probe(sess, page, size), page=page.get('name'), size=size, engine='chromium')
            sess.guard(G, 'menu-opens-and-closes', lambda: disclosures(sess, page, size), page=page.get('name'), size=size, engine='chromium')
    flows = sess.job.get('flows', default=[]) or []
    if not flows:
        sess.rec(G, 'flows-listed', 'skip', 'job.json lists no flows; every job with a menu, a form or a sale should name them')
        return
    for flow in flows:
        for engine in sess.engines():
            sess.guard(G, 'flow: %s' % (flow.get('name') or 'unnamed'), lambda: run_flow(sess, flow, engine),
                       size=tuple(flow.get('viewport') or [390, 844]), engine=engine)
