"""MOTION , what a still can never show: the scroll itself.

- Films: each page scrolled by a real browser gesture (Input.synthesizeScrollGesture: wheel ticks on
  desktop, a finger on the phone) and filmed off the compositor over CDP (Page.startScreencast, each
  frame with its own swap time), resampled to an exact 30fps and encoded H.264. Never
  record_video_dir, which smears flat colour and repeats frames. A frame strip per film goes in
  sheets/ for looking. Method: v1 `tools/record_scroll.py`, an earlier job `02 identity/deck/film.py`.
- Frame times: a rAF loop records every frame while a scripted scroll runs under a 4x CPU throttle
  (CDP Emulation.setCPUThrottlingRate). The share of frames over 20ms and the longest frame. A loaded
  machine invents slow frames, so above the load ceiling the result is a skip, never a pass or a fail.
- Pins: every ScrollTrigger pin's start equals where its spacer puts it (the spacer top for a "top
  top" pin), within 2px, read at rest after load and again after a scroll to the foot and back.
- Reduced motion: with prefers-reduced-motion: reduce, every piece of text the default page shows
  while scrolled through is still shown (not at opacity 0, not clipped away, not off screen).
- GSAP blocked: with every GSAP script refused, the page still shows every piece of text.
"""
import base64
import os
import re
import shutil
import subprocess
import time

from common import register, safe_name, wait_for_quiet_machine, have

G = 'motion'
CHECKS = register(G, {
    'film': {
        'protects': 'the scroll can be judged as it moves, at an exact cadence that compares with the references',
        'limit': 'a film at an exact {film_fps}fps from the compositor, and its frame strip',
        'taught_by': 'v1 BUILD-LOG, 27 Sep: record_video_dir smeared, so films come off the compositor'},
    'frame-times': {
        'protects': 'the scroll stays smooth on a slower machine than ours',
        'limit': 'under {frames_over_slow_pct}% of frames over {slow_frame_ms}ms and none over {max_frame_ms}ms at {cpu_throttle}x CPU throttle',
        'taught_by': 'the studio build notes: the 133ms frame'},
    'pin-start': {
        'protects': 'a pinned section engages where it sits, so it never jumps',
        'limit': 'every pin\'s start within {pin_drift_px}px of its spacer, at rest and after a scroll through',
        'taught_by': 'the studio build notes: "clean film" claimed while three of four pins fired early'},
    'reduced-motion': {
        'protects': 'a person who asks for less motion still gets every piece of information, as a still',
        'limit': '{motion_missing_words} text blocks the default shows but reduced motion hides',
        'taught_by': 'v1 PLAN.md: reduced motion shows every piece of information as a still'},
    'without-gsap': {
        'protects': 'if the animation library fails to arrive, the page still says everything',
        'limit': '{motion_missing_words} text blocks lost with GSAP blocked',
        'taught_by': 'an earlier job deck test.py: with GSAP blocked every section must still show its text'},
})

# every block of visible words at this scroll position, whitespace and punctuation removed, so a split
# heading and an unsplit one compare equal
WORDS_JS = r"""() => {
  const L = __sc, blocks = new Map();
  const blockOf = el => { for (let a = el; a && a !== document.body; a = a.parentElement) if (L.isBlock(a)) return a; return document.body; };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let t;
  while ((t = walker.nextNode())) {
    if (!t.textContent.trim()) continue;
    const el = t.parentElement;
    if (!el || L.hiddenTree(el)) continue;
    if (getComputedStyle(el).visibility !== 'visible') continue;
    if (L.effOpacity(el) < 0.5 || L.clipHidden(el)) continue;
    const rg = document.createRange(); rg.selectNodeContents(t);
    const r = rg.getBoundingClientRect();
    if (r.width < 1 || r.height < 1 || !L.inView(r)) continue;
    const b = blockOf(el);
    blocks.set(b, (blocks.get(b) || '') + t.textContent);
  }
  return [...blocks.values()].map(s => s.toLowerCase().replace(/[\s .,;:!?'"()\[\]{}‘’“”·|\/\\-]+/g, '')).filter(s => s.length >= 3);
}"""

FT_INIT = r"""() => {
  window.__ft = {on: false, t: [], last: 0};
  const loop = ts => { const f = window.__ft; if (f.on) { if (f.last) f.t.push(ts - f.last); f.last = ts; } else f.last = 0; requestAnimationFrame(loop); };
  requestAnimationFrame(loop);
}"""

PINS_JS = r"""() => {
  if (!window.ScrollTrigger || !ScrollTrigger.getAll) return null;
  const L = __sc, out = [], vh = innerHeight;
  const frac = (tok, size) => {
    const m = String(tok).trim().match(/^(top|center|bottom|left|right|-?[\d.]+%|-?[\d.]+(px)?)([+-]=-?[\d.]+(px)?)?$/);
    if (!m) return null;
    let v = m[1] === 'top' || m[1] === 'left' ? 0 : m[1] === 'center' ? size / 2 : m[1] === 'bottom' || m[1] === 'right' ? size
          : m[1].endsWith('%') ? size * parseFloat(m[1]) / 100 : parseFloat(m[1]);
    if (m[3]) v += (m[3][0] === '-' ? -1 : 1) * parseFloat(m[3].slice(2));
    return v;
  };
  for (const st of ScrollTrigger.getAll()) {
    if (!st.pin) continue;
    const pin = st.pin, d = L.desc(pin).slice(0, 50);
    if (st.scroller && st.scroller !== window && st.scroller !== document.documentElement && st.scroller !== document.body) {
      out.push({d, skip: 'pins inside a custom scroller are not measured'}); continue;
    }
    const spacer = st.spacer || (pin.parentNode && pin.parentNode.classList && pin.parentNode.classList.contains('pin-spacer') ? pin.parentNode : null);
    if (!spacer) { out.push({d, skip: 'no pin spacer found'}); continue; }
    const vs = st.vars && st.vars.start;
    const startStr = vs === undefined ? 'top top' : (typeof vs === 'string' ? vs : null);
    if (startStr === null) { out.push({d, skip: 'start is a function or a number; cannot derive where it should be'}); continue; }
    const parts = startStr.trim().split(/\s+/);
    const trig = st.trigger || pin;
    const useSpacer = trig === pin || trig === spacer;
    const tr = (useSpacer ? spacer : trig).getBoundingClientRect();
    const h = useSpacer ? pin.offsetHeight : tr.height;
    const a = frac(parts[0] || 'top', h), b = frac(parts[1] || 'bottom', vh);
    if (a === null || b === null) { out.push({d, skip: 'cannot read start "' + startStr + '"'}); continue; }
    const top = tr.top + L.y();
    const expected = top + a - b;
    out.push({d, start: Math.round(st.start * 10) / 10, spacerTop: Math.round(top * 10) / 10, expected: Math.round(expected * 10) / 10,
              drift: Math.round(Math.abs(st.start - expected) * 10) / 10, startStr});
  }
  return out;
}"""


# ==== helpers
def _walk_words(sess, pg):
    seen = set()
    step = 0.8
    settle = sess.settle_ms()
    maxy = pg.evaluate('() => __sc.maxY()')
    vh = pg.evaluate('innerHeight')
    y = 0
    guard = 0
    while guard < 200:
        pg.evaluate('(y) => __sc.to(y)', y)
        pg.wait_for_timeout(settle)
        seen.update(pg.evaluate(WORDS_JS))
        maxy = pg.evaluate('() => __sc.maxY()')
        if y >= maxy:
            break
        y = min(maxy, y + int(vh * step))
        guard += 1
    return seen


def _missing(default, other):
    flat = '\u0001'.join(sorted(other))
    return sorted(s for s in default if s not in flat)


def _gsap_rx(sess):
    return re.compile('|'.join(sess.job.lists['gsap_scripts']), re.I)


def _gesture(cdp, size, phone, dy, speed):
    x, y = (size[0] * 0.85, size[1] * 0.8) if phone else (size[0] - 36, size[1] * 0.5)
    cdp.send('Input.synthesizeScrollGesture', {'x': x, 'y': y, 'yDistance': -int(dy), 'speed': int(speed),
                                                'gestureSourceType': 'touch' if phone else 'mouse',
                                                'preventFling': True})


# ==== films
def film(sess, page, size):
    phone = sess.is_phone(size)
    dpr = 2 if phone else 1
    name = '%s__%dx%d__chromium' % (safe_name(page.get('name') or 'page'), size[0], size[1])
    ctx, why = sess.context('chromium', size, touch=phone, dpr=dpr)
    if not ctx:
        sess.rec(G, 'film', 'skip', why, page, size, 'chromium')
        return
    raw = sess.films / ('_raw_' + name)
    shutil.rmtree(raw, ignore_errors=True)
    raw.mkdir(parents=True)
    frames = []
    try:
        pg = sess.open(ctx, page)
        cdp = ctx.new_cdp_session(pg)

        def on(f):
            try:
                cdp.send('Page.screencastFrameAck', {'sessionId': f['sessionId']})
            except Exception:
                pass
            p = raw / ('%05d.jpg' % len(frames))
            p.write_bytes(base64.b64decode(f['data']))
            frames.append((f['metadata']['timestamp'], p))
        cdp.on('Page.screencastFrame', on)
        cdp.send('Page.startScreencast', {'format': 'jpeg', 'quality': 90, 'maxWidth': size[0] * dpr,
                                          'maxHeight': size[1] * dpr, 'everyNthFrame': 1})
        wall0 = time.time()
        pg.wait_for_timeout(900)
        maxy = pg.evaluate('() => __sc.maxY()')
        speed = max(sess.L['film_pace_px_s'], maxy / max(1.0, sess.L['film_max_seconds'] - 3))
        for _ in range(3):
            left = pg.evaluate('() => __sc.maxY() - __sc.y()')
            if left < 3:
                break
            _gesture(cdp, size, phone, left, speed)
            pg.wait_for_timeout(900)
        pg.wait_for_timeout(700)
        wall1 = time.time()
        cdp.send('Page.stopScreencast')
        pg.wait_for_timeout(200)
        reached = pg.evaluate('() => [__sc.y(), __sc.maxY()]')
    finally:
        ctx.close()
    if not frames:
        sess.rec(G, 'film', 'error', 'the compositor sent no frames', page, size, 'chromium')
        shutil.rmtree(raw, ignore_errors=True)
        return
    # the compositor sends a frame only when the screen changes, so a still stretch (or a page that
    # does not scroll at all) is held on its last frame, over the whole wall-clock take
    fps = sess.L['film_fps']
    s, e = min(frames[0][0], wall0), max(frames[-1][0], wall1)
    n = max(1, int(round((e - s) * fps)))
    picks, j = [], 0
    for k in range(n):
        t = s + k / float(fps)
        while j + 1 < len(frames) and frames[j + 1][0] <= t:
            j += 1
        picks.append(frames[j][1])
    # the frame strip, for looking: eight moments evenly through the film, nothing cropped
    from PIL import Image
    strip = [picks[min(len(picks) - 1, int(len(picks) * (i + 0.5) / 8))] for i in range(8)]
    ims = [Image.open(p).convert('RGB') for p in strip]
    cw = 360 if not phone else 180
    ims = [im.resize((cw, round(im.height * cw / im.width))) for im in ims]
    ch = max(im.height for im in ims)
    sheet = Image.new('RGB', (cw * 4 + 5 * 8, ch * 2 + 3 * 8), (30, 30, 30))
    for i, im in enumerate(ims):
        sheet.paste(im, (8 + (i % 4) * (cw + 8), 8 + (i // 4) * (ch + 8)))
    sheet_path = sess.sheets / (name + '__strip.png')
    sheet.save(sheet_path)
    ev = [sess.rel(sheet_path)]
    src_fps = len(frames) / max(1e-6, frames[-1][0] - frames[0][0]) if len(frames) > 1 else 0.0
    reach = ('the page does not scroll, a still film' if reached[1] < 3 else
             'reached the foot' if reached[0] >= reached[1] - 3 else 'stopped at %d of %d' % (reached[0], reached[1]))
    if not have('ffmpeg'):
        shutil.rmtree(raw, ignore_errors=True)
        sess.rec(G, 'film', 'skip', 'ffmpeg is not installed, so no mp4; %d compositor frames (%.0f a second) over %.1fs, frame strip written; %s'
                 % (len(frames), src_fps, e - s, reach), page, size, 'chromium', evidence=ev)
        return
    mp4 = sess.films / (name + '.mp4')
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'mjpeg', '-i', '-',
           '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos+accurate_rnd+full_chroma_int:in_range=pc:out_range=tv:'
                  'in_color_matrix=bt601:out_color_matrix=bt709,format=yuv420p',
           '-r', str(fps), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-colorspace', 'bt709',
           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-crf', '23', '-preset', 'medium',
           '-movflags', '+faststart', '-an', str(mp4)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for p in picks:
            pr.stdin.write(p.read_bytes())
        pr.stdin.close()
    except BrokenPipeError:
        pass
    err = pr.stderr.read().decode(errors='replace')[:200]
    pr.wait()
    shutil.rmtree(raw, ignore_errors=True)
    if pr.returncode != 0:
        sess.rec(G, 'film', 'error', 'ffmpeg failed: %s' % err, page, size, 'chromium', evidence=ev)
        return
    sess.rec(G, 'film', 'pass', '%d frames at exactly %dfps (%.1fs) from %d compositor frames (%.0f a second, %d distinct in the film); %s'
             % (n, fps, n / float(fps), len(frames), src_fps, len(set(picks)), reach),
             page, size, 'chromium', evidence=[sess.rel(mp4)] + ev)


# ==== frame times
def frame_times(sess, page, size):
    load, quiet = wait_for_quiet_machine(sess.L)
    phone = sess.is_phone(size)
    ctx, why = sess.context('chromium', size, touch=phone)
    if not ctx:
        sess.rec(G, 'frame-times', 'skip', why, page, size, 'chromium')
        return
    try:
        pg = sess.open(ctx, page)
        cdp = ctx.new_cdp_session(pg)
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': sess.L['cpu_throttle']})
        pg.evaluate(FT_INIT)
        pg.wait_for_timeout(500)
        maxy = pg.evaluate('() => __sc.maxY()')
        if maxy < 50:
            sess.rec(G, 'frame-times', 'skip', 'the page does not scroll (%dpx)' % maxy, page, size, 'chromium')
            return
        dist = min(maxy, 1200 * 18)
        speed = max(600, dist / 18.0)
        pg.evaluate('() => { window.__ft.on = true; }')
        _gesture(cdp, size, phone, dist, speed)
        pg.wait_for_timeout(800)
        t = pg.evaluate('() => { window.__ft.on = false; return window.__ft.t; }')
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
    finally:
        ctx.close()
    t = t[2:]
    if len(t) < 10:
        sess.rec(G, 'frame-times', 'error', 'only %d frames recorded during the scroll' % len(t), page, size, 'chromium')
        return
    slow = [x for x in t if x > sess.L['slow_frame_ms']]
    share = 100.0 * len(slow) / len(t)
    mx = max(t)
    p95 = sorted(t)[int(len(t) * 0.95) - 1]
    lt = 'load %.1f on %d cores' % (load, os.cpu_count() or 1) if load is not None else 'load unknown'
    txt = '%d frames over %dpx at %dx throttle: %.1f%% over %dms, longest %.0fms, p95 %.1fms; %s' % (
        len(t), dist, sess.L['cpu_throttle'], share, sess.L['slow_frame_ms'], mx, p95, lt)
    if not quiet:
        sess.rec(G, 'frame-times', 'skip', 'machine too busy for a timing result to mean anything; ' + txt, page, size, 'chromium')
        return
    ok = share < sess.L['frames_over_slow_pct'] and mx < sess.L['max_frame_ms']
    sess.rec(G, 'frame-times', 'pass' if ok else 'fail', txt, page, size, 'chromium')


# ==== pins
def pins(sess, page, size):
    ctx, why = sess.context('chromium', size)
    if not ctx:
        sess.rec(G, 'pin-start', 'skip', why, page, size, 'chromium')
        return
    try:
        pg = sess.open(ctx, page)
        first = pg.evaluate(PINS_JS)
        if first is None:
            sess.rec(G, 'pin-start', 'skip', 'no ScrollTrigger on the page', page, size, 'chromium')
            return
        if not first:
            sess.rec(G, 'pin-start', 'skip', 'ScrollTrigger present, no pins on the page', page, size, 'chromium')
            return
        _walk_words(sess, pg)
        pg.evaluate('() => __sc.to(0)')
        pg.wait_for_timeout(sess.settle_ms() + 400)
        second = pg.evaluate(PINS_JS) or []
    finally:
        ctx.close()
    lim = sess.L['pin_drift_px']
    for label, rows in (('at rest', first), ('after a scroll through', second)):
        bad = [r for r in rows if 'drift' in r and r['drift'] > lim]
        skipped = [r for r in rows if 'skip' in r]
        good = [r for r in rows if 'drift' in r and r['drift'] <= lim]
        if not bad and not good:
            sess.rec(G, 'pin-start', 'skip', '%s: %s' % (label, '; '.join('%s: %s' % (r['d'], r['skip']) for r in skipped[:4])),
                     page, size, 'chromium')
            continue
        txt = '; '.join('%s start %s vs %s (drift %spx, "%s")' % (r['d'], r['start'], r['expected'], r['drift'], r['startStr'])
                        for r in (bad or good)[:5])
        if skipped:
            txt += '; not measured: %d' % len(skipped)
        sess.rec(G, 'pin-start', 'fail' if bad else 'pass', '%s, %d pins: %s' % (label, len(bad) + len(good), txt),
                 page, size, 'chromium')


# ==== reduced motion and GSAP blocked
def shown_default(sess, page, size):
    key = ('words', page.get('name'), size)
    if key in sess.cache:
        return sess.cache[key]
    ctx, why = sess.context('chromium', size)
    if not ctx:
        return None, why
    try:
        pg = sess.open(ctx, page)
        has_gsap = pg.evaluate('() => !!(window.gsap || window.ScrollTrigger)')
        words = _walk_words(sess, pg)
    finally:
        ctx.close()
    sess.cache[key] = ((words, has_gsap), None)
    return sess.cache[key]


def reduced(sess, page, size):
    got, why = shown_default(sess, page, size)
    if not got:
        sess.rec(G, 'reduced-motion', 'skip', why, page, size, 'chromium')
        return
    default, _ = got
    ctx, why = sess.context('chromium', size, reduced_motion='reduce')
    if not ctx:
        sess.rec(G, 'reduced-motion', 'skip', why, page, size, 'chromium')
        return
    try:
        pg = sess.open(ctx, page)
        rm = _walk_words(sess, pg)
    finally:
        ctx.close()
    miss = _missing(default, rm)
    lim = sess.L['motion_missing_words']
    sess.rec(G, 'reduced-motion', 'pass' if len(miss) <= lim else 'fail',
             ('%d of %d text blocks the default shows are hidden, clipped or off screen: %s' % (len(miss), len(default), '; '.join('"%s"' % m[:40] for m in miss[:6])))
             if miss else 'all %d text blocks the default shows are shown' % len(default), page, size, 'chromium')


def without_gsap(sess, page, size):
    got, why = shown_default(sess, page, size)
    if not got:
        sess.rec(G, 'without-gsap', 'skip', why, page, size, 'chromium')
        return
    default, has_gsap = got
    if not has_gsap:
        sess.rec(G, 'without-gsap', 'skip', 'the page does not use GSAP', page, size, 'chromium')
        return
    rx = _gsap_rx(sess)
    blocked = []
    ctx, why = sess.context('chromium', size)
    if not ctx:
        sess.rec(G, 'without-gsap', 'skip', why, page, size, 'chromium')
        return

    def refuse(route):
        req = route.request
        if req.resource_type == 'script' and rx.search(req.url.rsplit('/', 1)[-1].split('?')[0]):
            blocked.append(req.url.rsplit('/', 1)[-1])
            return route.abort()
        return route.continue_()
    try:
        ctx.route('**/*', refuse)
        pg = sess.open(ctx, page)
        still = pg.evaluate('() => !!window.gsap')
        words = _walk_words(sess, pg)
    finally:
        ctx.close()
    if still:
        sess.rec(G, 'without-gsap', 'skip', 'GSAP is bundled into the page\'s own script (blocked %d files, window.gsap still defined); cannot refuse it'
                 % len(blocked), page, size, 'chromium')
        return
    miss = _missing(default, words)
    lim = sess.L['motion_missing_words']
    sess.rec(G, 'without-gsap', 'pass' if len(miss) <= lim else 'fail',
             ('%d of %d text blocks lost with %s refused: %s' % (len(miss), len(default), ', '.join(sorted(set(blocked)))[:120],
                                                            '; '.join('"%s"' % m[:40] for m in miss[:6])))
             if miss else 'all %d text blocks shown with %s refused' % (len(default), ', '.join(sorted(set(blocked)))[:160]),
             page, size, 'chromium')


def run(sess):
    for size in sess.size_set('motion'):
        for page in sess.pages:
            nm = page.get('name')
            if sess.quick:
                sess.rec(G, 'film', 'skip', 'quick run: films are made in the full run only', page, size, 'chromium')
            else:
                sess.guard(G, 'film', lambda: film(sess, page, size), page=nm, size=size, engine='chromium')
                for left in sess.films.glob('_raw_*'):
                    shutil.rmtree(left, ignore_errors=True)
            sess.guard(G, 'frame-times', lambda: frame_times(sess, page, size), page=nm, size=size, engine='chromium')
            sess.guard(G, 'pin-start', lambda: pins(sess, page, size), page=nm, size=size, engine='chromium')
            sess.guard(G, 'reduced-motion', lambda: reduced(sess, page, size), page=nm, size=size, engine='chromium')
            sess.guard(G, 'without-gsap', lambda: without_gsap(sess, page, size), page=nm, size=size, engine='chromium')
