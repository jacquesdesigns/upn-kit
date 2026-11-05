"""Fast page check: the inner loop beside the full kit (6 Oct 2026).

The full kit (studio_check.py) is the gate and takes minutes a page. This is what the conductor runs after every
handback and every send-back, in parallel, in well under a minute for a whole site, so nothing is reported on trust.
It writes nothing into the job's build; it only loads, looks and counts.

Per URL, size and engine it checks:
  load        0 responses >= 400, 0 page errors or console errors, a title
  open        the job's own open sequence (skip a loader, open doors, ...) then the optional ready_js is true
  hooks       every selector the job's flows press (tap, click) for this page: exactly ONE visible match;
              hidden twins (total > visible) are named; a hook found nowhere is "pending", not a fail
  copy        job.json copy.banned words, em and en dashes and " -- " in the visible text, aria-labels, alt and titles
  shot        a screenshot AFTER the open sequence (so the doors are open), plus an optional contact sheet

Usage (repo root):
  <python> "<kit_root>/skills/studio-check/checks/page_check.py" --job "<job dir>" --base http://127.0.0.1:4365 --pages all
  ... --urls http://127.0.0.1:4401/print/,http://127.0.0.1:4402/print/ --sheet      # variants side by side
  ... --engines chromium,webkit   --sizes 1440x900,390x844   --quick (chromium, 1440 and 390 only)

job.json "page_check" (all optional):
  open: {"desktop": [steps], "phone": [steps]}  steps: {"key":"Escape"} {"wait":ms} {"wheel":dy,"at":[x,y]}
        {"tap":[x,y]} {"click":"selector"} {"swipe":[x0,y0,x1,y1]}  (swipe needs Chromium; use taps for WebKit)
  ready_js: JS expression, true when the face is showing
  walk / walk_phone: [{"start":"/"}, {"click":sel,"expect_path":"/sound/"}, {"back":true,"expect_path":"/"}] key and history hops, 0 responses >= 400 each
  skip_hook_pages: page names whose hooks are not built yet
  multi_hooks: selectors that legitimately match several visible items (a list; the first is pressed)
  Only the FIRST press of each flow is checked; later ones depend on what it opened.
Exit 1 on any fail or error. A skip is never a pass.
"""
import argparse, asyncio, json, os, re, sys, time
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--job", required=True)
ap.add_argument("--base", help="e.g. http://127.0.0.1:4365")
ap.add_argument("--pages", default="all", help="job.json page names, comma separated, or all")
ap.add_argument("--urls", help="explicit full URLs, comma separated (overrides --base and --pages)")
ap.add_argument("--engines", default="chromium")
ap.add_argument("--sizes", default="1440x900,390x844")
ap.add_argument("--quick", action="store_true")
ap.add_argument("--sheet", action="store_true", help="write sheet.png, every shot on one contact sheet")
ap.add_argument("--conc", type=int, default=6)
ap.add_argument("--out")
a = ap.parse_args()

job = json.load(open(os.path.join(a.job, "job.json")))
pc = job.get("page_check", {}) or {}
banned = [w.lower() for w in (job.get("copy", {}) or {}).get("banned", [])]
pages = {p["path"]: p["name"] for p in job.get("pages", [])}
flows = job.get("flows", [])
sizes = [tuple(int(v) for v in s.split("x")) for s in ("1440x900,390x844" if a.quick else a.sizes).split(",")]
engines = ["chromium"] if a.quick else a.engines.split(",")
if a.urls: urls = a.urls.split(",")
else:
    assert a.base, "give --base or --urls"
    want = None if a.pages == "all" else set(a.pages.split(","))
    urls = [a.base.rstrip("/") + p["path"] for p in job.get("pages", []) if want is None or p["name"] in want]
    urls = [u + (".html" if u.endswith("/404") else "") for u in urls]
ts = time.strftime("%Y%m%d-%H%M%S")
out = a.out or os.path.join(a.job, "evidence", "pagecheck", ts); os.makedirs(os.path.join(out, "shots"), exist_ok=True)

DASH = re.compile("[\u2014\u2013]| -- ")
def page_name(u):
    p = urlparse(u).path
    for k in (p, p.rstrip("/") + "/", p.replace(".html", "")):
        if k in pages: return pages[k]
    return p.strip("/") or "home"
def hook_selectors(name, mob):
    sels = []
    for f in flows:
        if f.get("page") != name: continue
        vp = f.get("viewport") or [1440, 900]
        if (vp[0] < 600) != mob: continue
        for s in f.get("steps", []):
            k = "tap" if "tap" in s else "click" if "click" in s else None
            if k and isinstance(s[k], str):
                if s[k] not in sels: sels.append(s[k])
                break   # later presses in a flow depend on what the first one opened
    return sels

async def run_steps(page, cdp, steps, touch):
    for s in steps:
        if "key" in s: await page.keyboard.press(s["key"])
        elif "wait" in s: await page.wait_for_timeout(s["wait"])
        elif "wheel" in s:
            x, y = s.get("at", [100, 100]); await page.mouse.move(x, y); await page.mouse.wheel(0, s["wheel"])
        elif "tap" in s:
            if touch: await page.touchscreen.tap(*s["tap"])
            else: await page.mouse.click(*s["tap"])
        elif "click" in s: await page.click(s["click"], timeout=3000)
        elif "swipe" in s:
            if cdp is None: raise RuntimeError("swipe needs Chromium (CDP); use taps for WebKit")
            x0, y0, x1, y1 = s["swipe"]
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
            for i in range(1, 15):
                await asyncio.sleep(.016)
                await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / 14, "y": y0 + (y1 - y0) * i / 14}]})
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})

TEXT_JS = """()=>{const t=[document.title,document.body.innerText];
 document.querySelectorAll('[aria-label],[alt],[title]').forEach(e=>{t.push(e.getAttribute('aria-label')||'',e.getAttribute('alt')||'',e.getAttribute('title')||'')});
 return t.join('\\n')}"""

async def check(sem, browsers, engine, url, size):
    w, h = size; mob = w < 600; name = page_name(url); rows = []
    label = f"{name}@{w}x{h}/{engine}"
    def row(check, status, measured="", note=""): rows.append({"url": url, "page": name, "size": f"{w}x{h}", "engine": engine, "check": check, "status": status, "measured": measured, "note": note})
    async with sem:
        ctx = await browsers[engine].new_context(viewport={"width": w, "height": h}, is_mobile=mob and engine != "firefox", has_touch=mob)
        page = await ctx.new_page(); bad, errs = [], []
        page.on("response", lambda r: bad.append(f"{r.status} {urlparse(r.url).path}") if r.status >= 400 and "favicon" not in r.url else None)
        page.on("pageerror", lambda e: errs.append(str(e)[:100]))
        page.on("console", lambda m: errs.append("console: " + m.text[:100]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
        cdp = await ctx.new_cdp_session(page) if engine == "chromium" else None
        try:
            await page.goto(url, wait_until="load", timeout=20000)
            steps = (pc.get("open", {}) or {}).get("phone" if mob else "desktop") or [{"key": "Escape"}, {"wait": 1500}]
            await page.wait_for_timeout(800)
            try: await run_steps(page, cdp, steps, mob); opened = True; why = ""
            except Exception as e: opened = False; why = str(e)[:120]
            ready = pc.get("ready_js")
            if opened and ready:
                ok = await page.evaluate(ready)
                row("open", "pass" if ok else "fail", "ready_js " + str(ok), "" if ok else "the face is not showing after the open sequence")
            elif not opened: row("open", "skip" if "CDP" in why else "error", "", why)
            else: row("open", "pass", "no ready_js", "open sequence ran")
            shot = os.path.join(out, "shots", re.sub(r"[^a-z0-9]+", "-", f"{name}-{w}x{h}-{engine}-{urlparse(url).netloc}".lower()) + ".png")
            await page.screenshot(path=shot)
            row("load", "pass" if not bad and not errs else "fail", f"{len(bad)} bad, {len(errs)} errors", "; ".join((bad + errs)[:3]))
            title = await page.title();
            if not title.strip(): row("title", "fail", "", "empty title")
            sels = hook_selectors(name, mob)
            if name in (pc.get("skip_hook_pages") or []): sels = []
            for sel in sels:
                try:
                    total = await page.locator(sel).count(); vis = await page.locator(sel + ":visible").count()
                    first_vis = await page.locator(sel).first.is_visible() if total else False
                except Exception as e: row("hook", "error", sel, str(e)[:80]); continue
                if total == 0: row("hook", "skip", sel, "pending: not on this page yet")
                elif not first_vis: row("hook", "fail", sel, f"the FIRST match is hidden ({vis} visible of {total}): a flow pressing it hits a hidden twin")
                elif sel in (pc.get("multi_hooks") or []) and vis >= 1: row("hook", "pass", sel, f"{vis} visible of {total} (repeated item)")
                elif vis == 1: row("hook", "pass", sel, f"1 visible of {total}" if total > 1 else "")
                else: row("hook", "fail", sel, f"{vis} visible of {total}" + (" (hidden twin matches)" if vis == 0 or total > vis else ""))
            text = await page.evaluate(TEXT_JS); low = text.lower()
            hits = sorted({w_ for w_ in banned if re.search(r"\b" + re.escape(w_) + r"\b", low)})
            dash = len(DASH.findall(text))
            row("copy", "pass" if not hits and not dash else "fail", f"{len(hits)} banned, {dash} dashes", ", ".join(hits[:5]))
        except Exception as e: row("run", "error", "", str(e)[:140])
        finally: await ctx.close()
    return rows, shot if "shot" in dir() else None

async def walk(browsers, engine, base, steps, size, label):
    """Navigate by the real keys and Back/Forward: every hop must land on its path with 0 responses >= 400."""
    rows = []; w, h = size; mob = w < 600
    ctx = await browsers[engine].new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob); page = await ctx.new_page()
    cdp = await ctx.new_cdp_session(page) if engine == "chromium" else None; bad = []
    page.on("response", lambda r: bad.append(f"{r.status} {urlparse(r.url).path}") if r.status >= 400 and "favicon" not in r.url else None)
    def row(status, measured, note=""): rows.append({"url": base, "page": label, "size": f"{w}x{h}", "engine": engine, "check": "walk", "status": status, "measured": measured, "note": note})
    try:
        await page.goto(base + steps[0].get("start", "/"), wait_until="load"); await page.wait_for_timeout(800)
        await run_steps(page, cdp, (pc.get("open", {}) or {}).get("phone" if mob else "desktop") or [{"key": "Escape"}, {"wait": 1500}], mob)
        for i, s in enumerate(steps[1:], 1):
            bad.clear()
            try:
                if "click" in s: await page.click(s["click"], timeout=4000)
                elif s.get("back"): await page.go_back()
                elif s.get("forward"): await page.go_forward()
                elif "steps" in s: await run_steps(page, cdp, s["steps"], mob)
                await page.wait_for_timeout(s.get("wait", 4500))
                path = urlparse(page.url).path; ok = path.rstrip("/") == s["expect_path"].rstrip("/")
                row("pass" if ok and not bad else "fail", f"hop {i}: {path}", "" if ok and not bad else f"expected {s['expect_path']}; " + "; ".join(bad[:3]))
            except Exception as e: row("error", f"hop {i}", str(e)[:100]); break
    except Exception as e: row("error", "start", str(e)[:100])
    await ctx.close(); return rows

async def main():
    t0 = time.time(); sem = asyncio.Semaphore(a.conc); results = []; shots = []
    async with async_playwright() as pw:
        browsers = {}
        for e in engines:
            try: browsers[e] = await getattr(pw, e).launch()
            except Exception as ex: results.append({"url": "-", "page": "-", "size": "-", "engine": e, "check": "launch", "status": "error", "measured": "", "note": str(ex)[:120]})
        engs = [e for e in engines if e in browsers]
        jobs = [check(sem, browsers, e, u, s) for e in engs for u in urls for s in sizes]
        if a.base and (pc.get("walk") or pc.get("walk_phone")):
            for e in engs:
                if pc.get("walk"): jobs.append(walk(browsers, e, a.base.rstrip("/"), pc["walk"], (1440, 900), "walk-desktop"))
                if pc.get("walk_phone"): jobs.append(walk(browsers, e, a.base.rstrip("/"), pc["walk_phone"], (390, 844), "walk-phone"))
        for res in await asyncio.gather(*jobs):
            rows, shot = res if isinstance(res, tuple) else (res, None)
            results += rows
            if shot: shots.append(shot)
        for b in browsers.values(): await b.close()
    summ = {k: sum(1 for r in results if r["status"] == k) for k in ("pass", "fail", "skip", "error")}
    json.dump({"job": a.job, "urls": urls, "engines": engs, "sizes": [f"{w}x{h}" for w, h in sizes], "seconds": round(time.time() - t0, 1), "summary": summ, "results": results}, open(os.path.join(out, "report.json"), "w"), indent=1)
    md = [f"# Page check {ts}", f"{len(urls)} URLs x {len(sizes)} sizes x {len(engs)} engines in {round(time.time() - t0, 1)} s. " + ", ".join(f"{v} {k}" for k, v in summ.items()), ""]
    for st in ("error", "fail", "skip"):
        rs = [r for r in results if r["status"] == st]
        if rs: md += [f"## {st} ({len(rs)})"] + [f"- {r['page']} {r['size']} {r['engine']} | {r['check']} | {r['measured']} | {r['note']}" for r in rs] + [""]
    open(os.path.join(out, "report.md"), "w").write("\n".join(md))
    if a.sheet and shots:
        from PIL import Image
        ims = [Image.open(s).convert("RGB") for s in sorted(shots)]; cw = 480; th = [im.resize((cw, int(im.height * cw / im.width))) for im in ims]
        cols = 3; rowsn = (len(th) + cols - 1) // cols; rh = max(t.height for t in th)
        sh = Image.new("RGB", (cols * cw, rowsn * rh), "black")
        for i, t in enumerate(th): sh.paste(t, ((i % cols) * cw, (i // cols) * rh))
        sh.save(os.path.join(out, "sheet.png"))
    print(f"page_check: {len(urls)} URLs x {len(sizes)} sizes x {len(engs)} engines in {round(time.time() - t0, 1)} s: " + ", ".join(f"{v} {k}" for k, v in summ.items()) + f"  -> {out}")
    for r in results:
        if r["status"] in ("fail", "error"): print(f"  {r['status'].upper()} {r['page']} {r['size']} {r['engine']} | {r['check']} | {r['measured']} | {r['note']}")
    sys.exit(1 if summ["fail"] or summ["error"] else 0)
asyncio.run(main())
