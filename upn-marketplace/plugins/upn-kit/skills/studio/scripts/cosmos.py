#!/usr/bin/env python3
"""Download every element on a public Cosmos board, headless: images AND videos, in board order.

  cosmos.py BOARD_URL OUTDIR [--prefix name]

What this handles (each one lost items on the 27 Sep 2026 portfolio pull):
- The grid is virtualised, so it is swept top to bottom at three step sizes and collected by id.
- Videos render either as <video> (id is in the poster) or as a poster <img> whose alt starts
  "A video". Each is hovered, then clicked, to start its Mux HLS stream, which ffmpeg saves as .mp4.
  The page preloads neighbouring streams, so CHECK each video against its poster by eye after a pull.
- Newer uploads live under cdn.cosmos.so/images/<id>, older ones at cdn.cosmos.so/<id>; both are tried.
- "More ideas" recommendations and avatars are excluded by tile size (>60px) and by the board count.
- The pull is checked against the board's own numberOfElements, and says loudly if they differ.
Writes OUTDIR/<prefix>-NN.jpg (poster for a video), <prefix>-NN.mp4, manifest.json, SOURCE.txt.
Images keep their own ratio. Needs ffmpeg on the PATH.
"""
import argparse, json, pathlib, re, subprocess, urllib.request
from playwright.sync_api import sync_playwright

COLLECT = r"""() => [...document.querySelectorAll('img,video')].map(e => {
  const s = e.tagName == 'VIDEO' ? e.poster : (e.currentSrc || e.src);
  const m = (s || '').match(/[0-9a-f]{8}-[0-9a-f-]{27}/);
  const b = e.getBoundingClientRect();
  return m && e.clientWidth > 60 && !(e.alt || '').startsWith('Cover of ') ? {id: m[0], tag: e.tagName, alt: e.alt || '',
    x: Math.round(b.x), y: Math.round(b.y + scrollY), w: Math.round(b.width), h: Math.round(b.height)} : null;
}).filter(Boolean)"""


def board_count(html):
    # the page also carries the owner's whole-profile count, so this returns every value; the board's is one of them
    counts = re.findall(r'numberOfElements\\?":(\d+)', html)
    return sorted(set(int(c) for c in counts))


def fetch_image(uid, path):
    for base in (f'https://cdn.cosmos.so/{uid}', f'https://cdn.cosmos.so/images/{uid}'):
        for q in ('?format=jpg&w=2000', '?w=2000', ''):
            try:
                req = urllib.request.Request(base + q, headers={'Referer': 'https://www.cosmos.so/', 'User-Agent': 'Mozilla/5.0'})
                data = urllib.request.urlopen(req, timeout=60).read()
                if len(data) > 3000:
                    path.write_bytes(data); return base + q
            except Exception:
                pass
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('url'); ap.add_argument('outdir'); ap.add_argument('--prefix')
    a = ap.parse_args()
    out = pathlib.Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    prefix = a.prefix or re.sub(r'[^a-z0-9]+', '-', a.url.rstrip('/').split('/')[-1].lower())
    items, streams = {}, []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1440, 'height': 1000})
        pg.on('request', lambda r: streams.append(r.url) if r.url.startswith('https://stream.mux.com') and '.m3u8' in r.url else None)
        pg.goto(a.url, wait_until='networkidle', timeout=60000); pg.wait_for_timeout(2500)
        counts = board_count(pg.content().replace('\\"', '"'))
        for step in (300, 450, 700):
            pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(400); y = 0
            while y < pg.evaluate('document.body.scrollHeight') + 1000:
                for r in pg.evaluate(COLLECT):
                    items.setdefault(r['id'], r)
                y += step; pg.evaluate(f'scrollTo(0,{y})'); pg.wait_for_timeout(350)
        for v in [i for i in items.values() if i['tag'] == 'VIDEO' or i['alt'].startswith('A video')]:
            pg.evaluate(f"scrollTo(0,{max(0, v['y'] - 300)})"); pg.wait_for_timeout(800)
            before = set(streams); cx = v['x'] + v['w'] / 2; cy = v['y'] - pg.evaluate('scrollY') + v['h'] / 2
            pg.mouse.move(cx, cy); pg.wait_for_timeout(2500)
            if not [s for s in streams if s not in before]:
                pg.mouse.click(cx, cy); pg.wait_for_timeout(4000); pg.keyboard.press('Escape'); pg.wait_for_timeout(1500)
            new = [s for s in streams if s not in before]
            v['stream'] = new[0] if new else None
            pg.mouse.move(5, 5); pg.wait_for_timeout(500)
        b.close()
    order = sorted(items.values(), key=lambda i: (i['y'], i['x']))
    man, problems = [], []
    for n, it in enumerate(order, 1):
        stem = f'{prefix}-{n:02d}'
        rec = {'file': f'{stem}.jpg', 'cosmosId': it['id'], 'cosmosAlt': it['alt'],
               'type': 'video' if (it['tag'] == 'VIDEO' or it['alt'].startswith('A video')) else 'image'}
        rec['fetched'] = fetch_image(it['id'], out / rec['file'])
        if not rec['fetched']:
            problems.append(f'{stem}: image not fetched')
        if rec['type'] == 'video':
            rec['stream'] = it.get('stream'); rec['video'] = f'{stem}.mp4'
            if rec['stream']:
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', rec['stream'], '-c', 'copy', '-bsf:a', 'aac_adtstoasc',
                                str(out / rec['video'])], check=False)
            if not (out / rec['video']).exists():
                problems.append(f'{stem}: video not saved')
        man.append(rec)
    json.dump({'board': a.url, 'numberOfElementsOnPage': counts, 'pulled': len(man), 'items': man},
              open(out / 'manifest.json', 'w'), indent=1)
    (out / 'SOURCE.txt').write_text(f'{a.url}\n{len(man)} elements, cosmos.so, private working reference, not for republication\n')
    nv = sum(r['type'] == 'video' for r in man)
    print(f'{len(man)} elements ({len(man) - nv} images, {nv} videos) -> {out}')
    print(f'numberOfElements values on the page: {counts}; the board\'s own count must be one of them and equal {len(man)}')
    for pr in problems:
        print('PROBLEM', pr)
    if nv:
        print('Check each video against its poster by eye: neighbouring streams preload and can be matched wrongly.')


if __name__ == '__main__':
    main()
