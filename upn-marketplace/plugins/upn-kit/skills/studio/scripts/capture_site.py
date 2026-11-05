#!/usr/bin/env python3
"""Capture one website reference, headless.

  capture_site.py URL OUTDIR [--feel] [--remove '.splash']

Always: desktop screens at 1440x900 taken while scrolling (scroll-animated sites show their real state,
unlike one full-page screenshot), a phone fold at 390x844, and measure.json (fonts and sizes, colours,
transition and animation timings, libraries, pinned sections, page length in screens, sticky and fixed
elements, phone overflow).
--feel adds: a screen recording of a slow wheel-scroll through the page (feel.webm), frames from it
every second (frames/), and scroll timing (how long pins hold, whether scroll is smoothed).
"""
import argparse, json, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright

MEASURE_JS = r"""
() => {
  const vh = innerHeight, H = document.documentElement.scrollHeight;
  const txt = [...document.querySelectorAll('body *')].filter(e => {
    if (!e.offsetParent && getComputedStyle(e).position !== 'fixed') return false;
    return [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
  });
  const fonts = {}, sizes = {}, colours = {}, bgs = {};
  for (const e of txt) {
    const s = getComputedStyle(e);
    const fam = s.fontFamily.split(',')[0].replace(/["']/g,'').trim();
    const k = `${fam} ${s.fontWeight}`; fonts[k] = (fonts[k]||0)+1;
    sizes[s.fontSize] = (sizes[s.fontSize]||0)+1;
    colours[s.color] = (colours[s.color]||0)+1;
  }
  for (const e of document.querySelectorAll('body, body *')) {
    const b = getComputedStyle(e).backgroundColor;
    if (b && b !== 'rgba(0, 0, 0, 0)') bgs[b] = (bgs[b]||0)+1;
  }
  const top = (o, n) => Object.entries(o).sort((a,b)=>b[1]-a[1]).slice(0,n);
  const trans = {}, eases = {};
  for (const e of document.querySelectorAll('body *')) {
    const s = getComputedStyle(e);
    for (const d of s.transitionDuration.split(',')) { const t = d.trim(); if (t && t !== '0s') trans[t]=(trans[t]||0)+1; }
    if (s.transitionDuration !== '0s') for (const f of s.transitionTimingFunction.split(/,(?![^(]*\))/)) { const t=f.trim(); eases[t]=(eases[t]||0)+1; }
  }
  const anims = document.getAnimations ? document.getAnimations().map(a => {
    const t = a.effect && a.effect.getTiming ? a.effect.getTiming() : {};
    return {name: a.animationName || a.constructor.name, duration: t.duration, easing: t.easing, iterations: t.iterations};
  }).slice(0,40) : [];
  const libs = {
    gsap: !!window.gsap, ScrollTrigger: !!window.ScrollTrigger,
    lenis: !!window.lenis || document.documentElement.classList.contains('lenis'),
    locomotive: !!document.querySelector('[data-scroll-container]'),
    three: !!window.THREE || !!document.querySelector('canvas[data-engine], canvas'),
    webgl: [...document.querySelectorAll('canvas')].some(c => { try { return !!(c.getContext('webgl2')||c.getContext('webgl')); } catch(e) { return false; } }),
    barba: !!window.barba, swiper: !!document.querySelector('.swiper'),
  };
  const scripts = [...document.scripts].map(s => (s.src||'').split('/').pop()).filter(Boolean).slice(0,40);
  const pins = [...document.querySelectorAll('.pin-spacer')].map(p => {
    const c = p.firstElementChild; const extra = p.offsetHeight - (c ? c.offsetHeight : 0);
    return +(extra / vh).toFixed(2);
  });
  const fixed = [...document.querySelectorAll('body *')].filter(e => ['fixed','sticky'].includes(getComputedStyle(e).position)).length;
  const hs = ['h1','h2','h3'].map(t => [...document.querySelectorAll(t)].slice(0,3).map(e => getComputedStyle(e).fontSize));
  return {
    title: document.title, url: location.href, viewport: [innerWidth, vh], pageHeight: H,
    screens: +(H / vh).toFixed(1), fonts: top(fonts,10), fontSizes: top(sizes,15),
    distinctFontSizes: Object.keys(sizes).length, headingSizes: {h1: hs[0], h2: hs[1], h3: hs[2]},
    textColours: top(colours,8), backgrounds: top(bgs,8),
    transitionDurations: top(trans,10), easings: top(eases,8), animations: anims,
    libraries: libs, scripts, pinnedSections_screens: pins, fixedOrSticky: fixed,
    images: document.images.length, videos: document.querySelectorAll('video').length,
  };
}
"""

IMAGES_READY_JS = r"""() => [...document.images].filter(i => {
  const r = i.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight && r.width > 40;
}).every(i => i.complete && i.naturalWidth > 0)"""

# Exact consent labels only. Never partial matches: a capture must not click a site's real buttons.
COOKIE_WORDS = ['Accept all', 'Accept All', 'Accept all cookies', 'Accept All Cookies', 'Accept', 'Allow all',
                'I agree', 'Agree', 'Got it', 'OK', 'Ok']


def dismiss_banners(page):
    for w in COOKIE_WORDS:
        try:
            b = page.get_by_role('button', name=w, exact=True).first
            if b.is_visible(timeout=500):
                b.click(timeout=1000)
                page.wait_for_timeout(500)
                return w
        except Exception:
            pass
    return None


def strip_overlays(page, selectors):
    # only what the caller names; the capture records what it removed
    for sel in selectors:
        page.evaluate('s => { document.querySelectorAll(s).forEach(e => e.remove());'
                      ' document.body.style.overflow = "visible"; document.documentElement.style.overflow = "visible"; }', sel)
    if selectors:
        page.wait_for_timeout(500)


def settle(page, url):
    try:
        page.goto(url, wait_until='networkidle', timeout=45000)
    except Exception:
        page.goto(url, wait_until='load', timeout=60000)
    page.wait_for_timeout(2500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url'); ap.add_argument('outdir'); ap.add_argument('--feel', action='store_true')
    ap.add_argument('--max-screens', type=int, default=40)
    ap.add_argument('--remove', action='append', default=[], help='CSS selector of a splash or overlay to delete before capture (repeatable); restores body scroll')
    a = ap.parse_args()
    out = pathlib.Path(a.outdir); (out / 'screens').mkdir(parents=True, exist_ok=True)
    result = {'captured': time.strftime('%Y-%m-%d %H:%M'), 'feelCaptured': a.feel}
    with sync_playwright() as p:
        b = p.chromium.launch()
        opts = dict(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
        if a.feel:
            opts['record_video_dir'] = str(out / '_video'); opts['record_video_size'] = {'width': 1440, 'height': 900}
        ctx = b.new_context(**opts); page = ctx.new_page()
        settle(page, a.url)
        result['bannerDismissed'] = dismiss_banners(page)
        strip_overlays(page, a.remove); result['removed'] = a.remove
        page.screenshot(path=str(out / 'fold-desktop.jpg'), type='jpeg', quality=82)
        result['measure'] = page.evaluate(MEASURE_JS)
        # scroll through by wheel, the way a person does, sampling position and taking one shot per screen
        vh = 900; samples = []; shot = 0; last_shot_y = -vh; t0 = time.time()
        page.mouse.move(720, 450)
        for i in range(a.max_screens * 10):
            page.mouse.wheel(0, 160); page.wait_for_timeout(110)
            y = page.evaluate('scrollY')
            samples.append([round(time.time() - t0, 2), y])
            if y - last_shot_y >= vh * 0.9:
                shot += 1; last_shot_y = y
                # lazy-loaded images paint black or blank until they arrive; a case study is mostly images
                try:
                    page.wait_for_function(IMAGES_READY_JS, timeout=6000)
                except Exception:
                    pass
                page.wait_for_timeout(300)
                page.screenshot(path=str(out / 'screens' / f'{shot:02d}.jpg'), type='jpeg', quality=78)
            at_end = y >= page.evaluate('document.documentElement.scrollHeight') - vh - 4
            if len(samples) > 12 and at_end and all(s[1] == samples[-1][1] for s in samples[-12:]):
                break  # really at the end, and it stayed there
        result['scroll'] = {
            'wheelSteps': len(samples), 'seconds': samples[-1][0] if samples else 0,
            'finalY': samples[-1][1] if samples else 0,
            # a site with smoothed scroll keeps moving between wheel events; plain scroll jumps 160px per step
            'meanStepPx': round(sum(abs(samples[i][1] - samples[i-1][1]) for i in range(1, len(samples))) / max(1, len(samples) - 1), 1),
            'screensShot': shot,
        }
        ctx.close()
        if a.feel:
            vids = list((out / '_video').glob('*.webm'))
            if vids:
                vids[0].rename(out / 'feel.webm'); (out / '_video').rmdir()
                (out / 'frames').mkdir(exist_ok=True)
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(out / 'feel.webm'), '-vf', 'fps=1,scale=720:-1',
                                str(out / 'frames' / '%03d.jpg')], check=False)
        m = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        mp = m.new_page(); settle(mp, a.url); dismiss_banners(mp); strip_overlays(mp, a.remove)
        mp.screenshot(path=str(out / 'fold-phone.jpg'), type='jpeg', quality=80)
        result['phone'] = mp.evaluate('({scrollWidth: document.documentElement.scrollWidth, innerWidth, screens: +(document.documentElement.scrollHeight/innerHeight).toFixed(1)})')
        m.close(); b.close()
    (out / 'measure.json').write_text(json.dumps(result, indent=1))
    ms = result['measure']
    print(f"{ms['title'][:60]!r}: {ms['screens']} screens, {result['scroll']['screensShot']} shots, "
          f"{ms['distinctFontSizes']} font sizes, pins {ms['pinnedSections_screens']}, libs "
          f"{[k for k, v in ms['libraries'].items() if v]}{', feel recorded' if a.feel else ''}")


if __name__ == '__main__':
    main()
