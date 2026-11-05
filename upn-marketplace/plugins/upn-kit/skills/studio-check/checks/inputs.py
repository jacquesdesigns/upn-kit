"""Real-input shapes for the studio probes (6 Oct 2026). Import from any job probe or use gesture_check.py.

A headless test that sends one tidy event passes where a real trackpad fails (an earlier job, 5 Oct: a scroll that
passed a single-event test did nothing on the owner's trackpad). These send what devices send.
"""
import asyncio, math

def trackpad_stream(n=60, peak=30):
    """60 wheel deltas: start at 1 to 2 px, rise, decay (about one second at 20 ms)."""
    d = [max(1, round(peak * math.sin(math.pi * i / n) ** 0.7)) if i < int(n * .75) else max(0, round(peak * (n - i) / (n * .25))) for i in range(n)]
    d[0] = 1; d[1] = 2
    return d, 20

def wheel_notches(k=3, step=100):  return [step] * k, 60
def fling(n=180, v0=40):           return [max(1, int(v0 * math.exp(-i / 50))) for i in range(n)], 16

async def wheel(page, deltas, gap, at, sign=1):
    await page.mouse.move(*at)
    for d in deltas:
        await page.mouse.wheel(0, sign * d); await page.wait_for_timeout(gap)

async def touch_swipe(cdp, x0, y0, x1, y1, moves=14, dt=16):
    """A finger drag as CDP touch events (Chromium only; WebKit has no CDP, use taps there)."""
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for i in range(1, moves + 1):
        await asyncio.sleep(dt / 1000)
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / moves, "y": y0 + (y1 - y0) * i / moves}]})
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})

async def touch_fling(cdp, x, y0, y1): await touch_swipe(cdp, x, y0, x, y1, moves=6, dt=8)

# Audio: tap every connection to the destination so silence can be PROVEN (not read from a flag).
AUDIO_INIT = """
(()=>{const O=window.AudioContext||window.webkitAudioContext; if(!O||window.__audioTap) return; window.__audioTap=1; window.__ctxs=[];
 const oc=AudioNode.prototype.connect;
 AudioNode.prototype.connect=function(t,...r){const c=this.context; if(t&&c&&t===c.destination){ if(!c.__an){c.__an=c.createAnalyser(); c.__an.fftSize=512;} if(this!==c.__an){try{oc.call(this,c.__an)}catch(e){}} if(!window.__ctxs.includes(c)) window.__ctxs.push(c);} return oc.call(this,t,...r)}})();
"""
AUDIO_LEVEL = """async()=>{const out=[];for(const c of (window.__ctxs||[])){const was=c.state; if(was==='suspended') await c.resume(); await new Promise(r=>setTimeout(r,500));
 const a=c.__an,d=new Float32Array(a.fftSize);let m=0;for(let i=0;i<6;i++){a.getFloatTimeDomainData(d);for(const v of d)m=Math.max(m,Math.abs(v));await new Promise(r=>setTimeout(r,60));}
 out.push({was,peak:+m.toFixed(4)}); if(was==='suspended') await c.suspend();} return out}"""
async def audio_peak(page):
    """Highest level across every audio context after forcing each to run for half a second, then restoring it. 0 = silent."""
    r = await page.evaluate(AUDIO_LEVEL); return (max((x["peak"] for x in r), default=0.0), r)
