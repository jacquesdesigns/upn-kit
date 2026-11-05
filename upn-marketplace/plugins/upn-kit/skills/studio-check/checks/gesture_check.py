"""Scroll-ownership and doors-gesture check (6 Oct 2026), config driven, Chromium (CDP touch).

For every scrollable element on a page (found by COMPUTED overflow, never a selector list) it sends real input shapes
(trackpad stream, wheel notches, fling on desktop; touch swipes, a fast fling, a swipe that continues past the end on a
phone) starting INSIDE it and asserts that the page's step counter and face did not change: a gesture that starts in a
scrollable element belongs to it. Optionally asserts that a gesture on plain chrome DOES step (chrome_points).

job.json page_check: step_counter (JS expression, e.g. "window.__steps"), face_js (e.g. "location.pathname"),
  open (as page_check.py), chrome_points {"desktop": [x,y], "phone": [x,y]} (optional, per page name or "default").
Usage: gesture_check.py --job J --base http://127.0.0.1:4365 --pages home,scene [--sizes 1440x900,390x844]
"""
import argparse, asyncio, json, os, sys, time
from urllib.parse import urlparse
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__)); import inputs

ap = argparse.ArgumentParser(); ap.add_argument("--job", required=True); ap.add_argument("--base", required=True)
ap.add_argument("--pages", default="all"); ap.add_argument("--sizes", default="1440x900,390x844"); a = ap.parse_args()
job = json.load(open(os.path.join(a.job, "job.json"))); pc = job.get("page_check", {}) or {}
want = None if a.pages == "all" else set(a.pages.split(","))
pages = [p for p in job.get("pages", []) if want is None or p["name"] in want]
sizes = [tuple(int(v) for v in s.split("x")) for s in a.sizes.split(",")]
COUNT = pc.get("step_counter", "0"); FACE = pc.get("face_js", "location.pathname")
SCAN = """()=>{const o=[];document.querySelectorAll('*').forEach(e=>{const s=getComputedStyle(e);
 const y=/(auto|scroll)/.test(s.overflowY)&&e.scrollHeight>e.clientHeight+1, x=/(auto|scroll)/.test(s.overflowX)&&e.scrollWidth>e.clientWidth+1;
 const r=e.getBoundingClientRect(); if((y||x)&&r.width>20&&r.height>20&&s.visibility!=='hidden'&&r.bottom>0&&r.top<innerHeight)
 o.push({sel:e.tagName.toLowerCase()+(e.className&&typeof e.className==='string'?'.'+e.className.trim().split(/\\s+/).join('.'):''),x:r.x,y:r.y,w:r.width,h:r.height,y_over:y,x_over:x,top:e.scrollTop})});return o}"""

async def one(pw, p, size, rows):
    w, h = size; mob = w < 600; name = p["name"]
    b = await pw.chromium.launch(); ctx = await b.new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob); page = await ctx.new_page(); cdp = await ctx.new_cdp_session(page)
    def row(check, status, measured, note=""): rows.append({"page": name, "size": f"{w}x{h}", "check": check, "status": status, "measured": measured, "note": note})
    try:
        await page.goto(a.base.rstrip("/") + p["path"] + (".html" if p["path"].endswith("/404") else ""), wait_until="load"); await page.wait_for_timeout(800)
        # reuse page_check's open sequence
        for s in (pc.get("open", {}) or {}).get("phone" if mob else "desktop", [{"key": "Escape"}, {"wait": 1500}]):
            if "key" in s: await page.keyboard.press(s["key"])
            elif "wait" in s: await page.wait_for_timeout(s["wait"])
            elif "wheel" in s: await page.mouse.move(*s.get("at", [100, 100])); await page.mouse.wheel(0, s["wheel"])
            elif "tap" in s: (await page.touchscreen.tap(*s["tap"])) if mob else (await page.mouse.click(*s["tap"]))
            elif "swipe" in s: await inputs.touch_swipe(cdp, *s["swipe"])
        scr = await page.evaluate(SCAN); row("scan", "pass", f"{len(scr)} scrollable", ", ".join(f"{s['sel'][:30]} {'y' if s['y_over'] else ''}{'x' if s['x_over'] else ''}" for s in scr[:6]))
        for s in scr:
            cx, cy = s["x"] + s["w"] / 2, s["y"] + s["h"] / 2; c0 = await page.evaluate(COUNT); f0 = await page.evaluate(FACE)
            if mob:
                y0, y1 = s["y"] + s["h"] - 15, s["y"] + 15
                for _ in range(3): await inputs.touch_swipe(cdp, cx, y0, cx, y1); await page.wait_for_timeout(500)
                await inputs.touch_fling(cdp, cx, y0, y1); await page.wait_for_timeout(700)
                await inputs.touch_swipe(cdp, cx, y0 - 100, cx, y1, moves=30); await page.wait_for_timeout(900)
            else:
                for gen in (inputs.trackpad_stream, inputs.wheel_notches, inputs.fling):
                    d, gap = gen()
                    for _ in range(2): await inputs.wheel(page, d, gap, (cx, cy)); await page.wait_for_timeout(500)
            await page.wait_for_timeout(1200); c1 = await page.evaluate(COUNT); f1 = await page.evaluate(FACE)
            ok = c0 == c1 and f0 == f1
            row("owned", "pass" if ok else "fail", f"{s['sel'][:40]}: steps {c0}->{c1}, face {f0}->{f1}", "" if ok else "a gesture that started inside a scrollable element moved the doors")
        pt = (pc.get("chrome_points", {}) or {}).get(name) or (pc.get("chrome_points", {}) or {}).get("default")
        if pt and pt.get("phone" if mob else "desktop"):
            x, y = pt["phone" if mob else "desktop"]; c0 = await page.evaluate(COUNT)
            if mob: await inputs.touch_swipe(cdp, x, y + 50, x, y - 40, moves=8)
            else: d, gap = inputs.trackpad_stream(); await inputs.wheel(page, d, gap, (x, y))
            await page.wait_for_timeout(2500); c1 = await page.evaluate(COUNT)
            row("chrome", "pass" if c1 > c0 else "fail", f"steps {c0}->{c1}", "" if c1 > c0 else "a gesture on plain chrome did not step")
    except Exception as e: row("run", "error", "", str(e)[:140])
    await b.close()

async def main():
    t0 = time.time(); rows = []
    async with async_playwright() as pw: await asyncio.gather(*[one(pw, p, s, rows) for p in pages for s in sizes])
    summ = {k: sum(1 for r in rows if r["status"] == k) for k in ("pass", "fail", "skip", "error")}
    out = os.path.join(a.job, "evidence", "pagecheck"); os.makedirs(out, exist_ok=True); json.dump({"summary": summ, "results": rows}, open(os.path.join(out, "gesture_latest.json"), "w"), indent=1)
    print(f"gesture_check: {len(pages)} pages x {len(sizes)} sizes in {round(time.time() - t0, 1)} s: " + ", ".join(f"{v} {k}" for k, v in summ.items()))
    for r in rows:
        if r["status"] != "pass" or r["check"] == "scan": print(f"  {r['status'].upper() if r['status']!='pass' else 'info'} {r['page']} {r['size']} | {r['check']} | {r['measured']} | {r['note']}")
    sys.exit(1 if summ["fail"] or summ["error"] else 0)
asyncio.run(main())
