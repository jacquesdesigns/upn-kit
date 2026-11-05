"""Doctor-lite: checks that matter here, one red line per fault. Standard library only; always exits 0.

Run by the session-start hook (its lines are shown to the person and given to Claude) or by hand:
  python doctor.py
Checks: MEMORY.md index size; a second competing MEMORY.md at the brain root; memory files pointing at paths that no longer
exist; em dashes in wiki pages changed this week; the Dropbox mirror ran this week; the memory folder is in the mirror.
The mirror checks need config.json keys "mirror_task" (Windows scheduled task name) and "mirror_script" (path of its script);
without them those two checks are skipped, not guessed.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

INDEX_MAX_BYTES = 15000
INDEX_MAX_LINES = 200
DEAD_SHOWN = 8


def lines():
    out = []
    root = _lib.brain_root()
    cfg = _lib.load_config()
    mems = _lib.memory_dirs()

    for m in mems:
        idx = m / "MEMORY.md"
        if idx.is_file():
            size = idx.stat().st_size
            n = len(idx.read_text("utf-8", "replace").splitlines())
            if size > INDEX_MAX_BYTES or n > INDEX_MAX_LINES:
                out.append("RED: %s is %d bytes, %d lines (keep under %d bytes and %d lines; past 25KB entries drop silently)"
                           % (idx, size, n, INDEX_MAX_BYTES, INDEX_MAX_LINES))
            # a file counts as indexed if MEMORY.md names it, or a hub file that is itself reached names it
            # (Prompt 1 sets up this hub layout: the index lists hubs, each hub lists its facts)
            text = idx.read_text("utf-8", "replace")
            files = [f for f in m.glob("*.md") if f.name != "MEMORY.md"]
            missing = [f for f in files if f.name not in text]
            grew = True
            while grew and missing:
                grew = False
                for f in [f for f in files if f not in missing]:
                    t = f.read_text("utf-8", "replace")
                    found = [g for g in missing if g.name in t]
                    if found:
                        missing = [g for g in missing if g not in found]
                        grew = True
            if missing:
                out.append("RED: %d memory file(s) not in the index or any hub it lists, first: %s"
                           % (len(missing), ", ".join(f.name for f in missing[:4])))
        elif any(m.glob("*.md")):
            out.append("RED: %s has memory files but no MEMORY.md index" % m)
        if (root / "MEMORY.md").is_file() and idx.is_file():
            out.append("RED: two indexes compete: %s and %s (keep one; the auto-memory one is the one Claude loads)" % (root / "MEMORY.md", idx))
        # memory paths that no longer exist
        dead = []
        for f in list(m.glob("*.md"))[:200]:
            try:
                t = f.read_text("utf-8", "replace")
            except OSError:
                continue
            for p in re.findall(r"`([A-Za-z]:\\[^`\n]+|[^`\s]+/[^`\s]+\.[A-Za-z0-9]{1,5})`", t):
                if p.startswith(("http", "~", "<")) or "*" in p or "<" in p:
                    continue
                cand = Path(p) if re.match(r"^[A-Za-z]:", p) else root / p
                try:
                    if not cand.exists():
                        dead.append((f.name, p))
                except OSError:
                    pass
        for name, p in dead[:DEAD_SHOWN]:
            out.append("RED: memory %s points at a path that is gone: %s" % (name, p))
        if len(dead) > DEAD_SHOWN:
            out.append("RED: ... and %d more dead memory paths" % (len(dead) - DEAD_SHOWN))

    wiki = root / "wiki"
    if wiki.is_dir():
        bad = []
        cutoff = time.time() - 7 * 86400
        for p in wiki.rglob("*.md"):
            try:
                if p.stat().st_mtime >= cutoff and "\u2014" in p.read_text("utf-8", "replace"):
                    bad.append(p.name)
            except OSError:
                pass
        if bad:
            out.append("RED: em dash in %d wiki page(s) changed this week, e.g. %s" % (len(bad), ", ".join(sorted(bad)[:4])))

    task = cfg.get("mirror_task") if _lib.role() == "main" else None
    if task and sys.platform.startswith("win"):
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-ScheduledTaskInfo -TaskName '%s' | Select-Object LastRunTime,LastTaskResult | ConvertTo-Json" % task.replace("'", "''")],
                               capture_output=True, text=True, timeout=15)
            info = json.loads(r.stdout)
            lr = info.get("LastRunTime")
            m = re.search(r"/Date\((\d+)\)/", str(lr))
            ts = int(m.group(1)) / 1000 if m else None
            if ts is None or time.time() - ts > 8 * 86400:
                out.append("RED: the Dropbox mirror task '%s' has not run in the last 8 days" % task)
            elif info.get("LastTaskResult") not in (0, 267009, 267011):
                out.append("RED: the Dropbox mirror task '%s' last result was %s (0 is clean; robocopy 1 to 7 are also fine)" % (task, info.get("LastTaskResult")))
        except Exception:
            out.append("RED: could not read the Dropbox mirror task '%s'" % task)
    script = cfg.get("mirror_script") if _lib.role() == "main" else None
    if script and Path(script).is_file() and mems:
        t = Path(script).read_text("utf-8", "replace").lower().replace("/", "\\")
        if ".claude\\projects" not in t and not any(str(m).lower().replace("/", "\\") in t for m in mems):
            out.append("RED: the memory folder is not in the mirror script %s" % script)
    return out


def main():
    _lib.utf8_out()
    try:
        for l in lines():
            print(l)
    except BaseException as e:
        print("RED: doctor could not run: %s" % e)
    sys.exit(0)


if __name__ == "__main__":
    main()
