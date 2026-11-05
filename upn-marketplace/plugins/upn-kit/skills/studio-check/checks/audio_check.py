"""Audio silence proof (6 Oct 2026), config driven. Silence is MEASURED (an analyser tapped on every audio context, each
forced to run for half a second), not read from a flag. Rule it protects: sound plays only while a face that shows its
controls is on screen; leaving stops it (an earlier job, the owner: "I've already got no way of turning it off").

job.json page_check.audio: {"start": "/", "open": true, "play": [steps], "plays_js": "SIGNAL.player.playing",
  "leaves": [{"name": "SOUND to TECH", "steps": [{"click": sel}], "expect": "stopped"|"playing"}], "wait": 4500}
steps: {"click": sel} {"wait": ms} {"key": k}. Usage: audio_check.py --job J --base URL
"""
import argparse, asyncio, json, os, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__)); import inputs
ap = argparse.ArgumentParser(); ap.add_argument("--job", required=True); ap.add_argument("--base", required=True); a = ap.parse_args()
job = json.load(open(os.path.join(a.job, "job.json"))); pc = job.get("page_check", {}) or {}; cfg = pc.get("audio")
if not cfg: print("audio_check: no page_check.audio in job.json (nothing to check)"); sys.exit(0)
async def steps(page, ss):
    for s in ss:
        if "click" in s: await page.click(s["click"], timeout=4000)
        elif "wait" in s: await page.wait_for_timeout(s["wait"])
        elif "key" in s: await page.keyboard.press(s["key"])
        elif "wheel" in s: await page.mouse.move(*s.get("at", [100, 100])); await page.mouse.wheel(0, s["wheel"])
async def main():
    rows = []
    async with async_playwright() as pw:
        for leave in cfg["leaves"]:
            b = await pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"]); ctx = await b.new_context(viewport={"width": 1440, "height": 900}); await ctx.add_init_script(inputs.AUDIO_INIT); page = await ctx.new_page()
            try:
                await page.goto(a.base.rstrip("/") + cfg.get("start", "/"), wait_until="load"); await page.wait_for_timeout(800)
                await steps(page, (pc.get("open", {}) or {}).get("desktop", [{"key": "Escape"}, {"wait": 1500}]) if cfg.get("open", True) else [])
                await steps(page, cfg.get("play", [])); await page.wait_for_timeout(1500)
                p0, _ = await inputs.audio_peak(page); playing = await page.evaluate(cfg["plays_js"]) if cfg.get("plays_js") else None
                if not (p0 > 0.001): rows.append((leave["name"], "error", f"never started: peak {p0}", "")); await b.close(); continue
                await steps(page, leave["steps"]); await page.wait_for_timeout(cfg.get("wait", 4500))
                p1, detail = await inputs.audio_peak(page); playing2 = await page.evaluate(cfg["plays_js"]) if cfg.get("plays_js") else None
                exp = leave.get("expect", "stopped"); ok = (p1 == 0 and not playing2) if exp == "stopped" else (p1 > 0.001 and bool(playing2))
                rows.append((leave["name"], "pass" if ok else "fail", f"before {p0}, after {p1}, flag {playing}->{playing2}, expected {exp}", ""))
            except Exception as e: rows.append((leave["name"], "error", str(e)[:120], ""))
            await b.close()
    fails = [r for r in rows if r[1] != "pass"]
    print(f"audio_check: {len(rows)} leaves, {len(rows) - len(fails)} pass, {len(fails)} not")
    for n, st, m, _ in rows: print(f"  {st:5} {n}: {m}")
    sys.exit(1 if fails else 0)
asyncio.run(main())
