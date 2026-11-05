"""Summarise a /_devcheck/ recording (6 Oct 2026): what a real finger sends, so the probes can send the same.
Per swipe: touchmove count, duration, mean gap, peak speed, and how long the list kept scrolling AFTER the finger lifted
(momentum; Chromium emulation sends none). Usage: devcheck_summary.py <devcheck-*.json> ..."""
import json, sys, statistics as st
for f in sys.argv[1:]:
    d = json.load(open(f)); ev = d["events"]; print(f"{f}\n  {d['ua'][:90]}\n  dpr {d['dpr']}, viewport {d['w']}x{d['h']}, standalone {d['standalone']}")
    swipes, cur = [], None
    for e in ev:
        if e["k"] == "touchstart": cur = {"in": e["in"], "pts": [e], "end": None, "scroll_after": []}
        elif cur and e["k"] == "touchmove": cur["pts"].append(e)
        elif cur and e["k"] in ("touchend", "touchcancel"): cur["end"] = e; swipes.append(cur)
        elif e["k"] == "scroll" and swipes and swipes[-1]["end"] and e["t"] >= swipes[-1]["end"]["t"]: swipes[-1]["scroll_after"].append(e)
    for i, s in enumerate(swipes, 1):
        p = s["pts"]; dur = (s["end"]["t"] - p[0]["t"]); moves = len(p) - 1
        gaps = [b["t"] - a["t"] for a, b in zip(p, p[1:])]; sp = max([abs(b["y"] - a["y"]) / max(1, b["t"] - a["t"]) for a, b in zip(p, p[1:])] or [0])
        mom = (s["scroll_after"][-1]["t"] - s["end"]["t"]) if s["scroll_after"] else 0
        print(f"  swipe {i} in {s['in']:5}: {moves:3} moves, {dur:4} ms, mean gap {round(st.mean(gaps),1) if gaps else 0} ms, peak {sp:.2f} px/ms, momentum after lift {mom} ms")
    w = [e for e in ev if e["k"] == "wheel"]
    if w: print(f"  wheel: {len(w)} events, first deltas {[e['dy'] for e in w[:8]]}")
