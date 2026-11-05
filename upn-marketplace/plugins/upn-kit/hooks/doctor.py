"""Doctor-lite: checks that matter here, one red line per fault. Standard library only; always exits 0.

Run by the session-start hook (its lines are shown to the person and given to Claude) or by hand:
  python doctor.py
Checks: MEMORY.md index size; a second competing MEMORY.md at the brain root; memory files pointing at paths that no longer
exist; em dashes in wiki pages changed this week; the Dropbox mirror ran this week; the memory folder is in the mirror.
Also: a job's NOW.md with more than about 40 hand-written lines above its machine sections (AMBER, a warning); new
tooling files (scripts, settings) that tonight's night save will not commit (RED; the types are read from nightly.py's
own TEXT list, so the two cannot drift apart).
The mirror checks need config.json keys "mirror_task" (Windows scheduled task name) and "mirror_script" (path of its script);
without them those two checks are skipped, not guessed.
"""
import ast
import os
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
# 0 is clean; robocopy exits 1 to 7 when it copied fine; 267009 is "running now"
TASK_OK = set(range(0, 8)) | {267009}
NOW_MAX_LINES = 40
MACHINE_HEADS = ("## NIGHT LOG", "## LATEST (auto")   # written by nightly.py and latest.py, not by hand
NIGHTLY = Path(__file__).resolve().parent / "nightly.py"
# scripts and settings: what a person or Claude makes to run the system, as opposed to documents and media
TOOLING = {".ps1", ".psm1", ".bat", ".cmd", ".vbs", ".sh", ".py", ".js", ".mjs", ".cjs", ".ts", ".css", ".json", ".jsonl",
           ".yml", ".yaml", ".toml", ".ini", ".cfg", ".xml", ".svg", ".reg"}
UNTRACKED_SHOWN = 4


def night_save_rules(path=NIGHTLY):
    """TEXT, BIG and NEVER_COMMIT from nightly.py's source (read, never imported, so this check cannot drift from it)."""
    want = {"TEXT": None, "BIG": None, "NEVER_COMMIT": None}
    for node in ast.parse(Path(path).read_text("utf-8")).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in want:
                    want[t.id] = ast.literal_eval(node.value)
    if want["TEXT"] is None:
        raise ValueError("no TEXT list in %s" % path)
    return {str(e).lower() for e in want["TEXT"]}, want["BIG"] or 2_000_000, tuple(want["NEVER_COMMIT"] or ())


def hand_lines(text):
    """Lines above the NIGHT LOG, not counting the LATEST section the hook writes."""
    n, machine = 0, False
    for line in text.splitlines():
        if line.startswith("## NIGHT LOG"):
            break
        if line.startswith("## "):
            machine = line.startswith(MACHINE_HEADS)
        if not machine:
            n += 1
    return n


def check_now_sizes(root):
    import nightly
    out = []
    for p in nightly.find_now_files(root, limit=300):
        try:
            n = hand_lines(p.read_text("utf-8", "replace"))
        except OSError:
            continue
        if n > NOW_MAX_LINES:
            out.append((n, p))
    out.sort(reverse=True)
    return ["AMBER: %s has %d hand-written lines above its machine sections (about %d max); move settled detail to the wiki "
            "or a file it links to" % (p, n, NOW_MAX_LINES) for n, p in out[:5]]


def check_untracked_tooling(root):
    """RED when new scripts or settings sit outside git and tonight's night save will leave them out."""
    if _lib.role() != "main" or not (Path(root) / ".git").exists():
        return []
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--others", "--exclude-standard"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    if r.returncode != 0:
        return []
    text, big, never = night_save_rules()
    loose = []
    for f in r.stdout.split("\0"):
        ext = os.path.splitext(f)[1].lower()
        if not f or ext not in TOOLING or any(b in f.replace("\\", "/").lower() for b in never):
            continue
        try:
            too_big = (Path(root) / f).stat().st_size > big
        except OSError:
            continue
        if ext not in text or too_big:
            loose.append(f)
    if not loose:
        return []
    return ["RED: %d new tooling file(s) the night save will not commit (add the type to TEXT in nightly.py, or commit or "
            "gitignore them): %s" % (len(loose), ", ".join(loose[:UNTRACKED_SHOWN]) + (" ..." if len(loose) > UNTRACKED_SHOWN else ""))]


def parse_task_csv(text):
    """(last run as epoch seconds or None, last result as int or None) from `schtasks /query /tn X /v /fo csv`.
    schtasks writes the date in the computer's short format, so day-first and month-first are both tried and the
    latest reading that is not in the future wins."""
    import csv
    import datetime
    rows = list(csv.reader(text.strip().splitlines()))
    if len(rows) < 2:
        return None, None
    head, row = rows[0], rows[1]
    col = {h.strip().lower(): i for i, h in enumerate(head)}
    lr = row[col.get("last run time", 5)].strip()
    res = row[col.get("last result", 6)].strip()
    ts = None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
        try:
            t = datetime.datetime.strptime(lr, fmt).timestamp()
        except ValueError:
            continue
        if t <= time.time() + 86400 and (ts is None or t > ts):
            ts = t
    try:
        res = int(res)
    except ValueError:
        res = None
    return ts, res


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
        # schtasks, not Get-ScheduledTaskInfo: the CIM cmdlets fail with "Access denied" for some non-admin users.
        # Called from Python with a list of arguments, so no shell (Git Bash included) rewrites /query.
        try:
            r = subprocess.run(["schtasks", "/query", "/tn", task, "/v", "/fo", "csv"],
                               capture_output=True, text=True, errors="replace", timeout=15)
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip())
            ts, res = parse_task_csv(r.stdout)
            if ts is None or time.time() - ts > 8 * 86400:
                out.append("RED: the Dropbox mirror task '%s' has not run in the last 8 days" % task)
            elif res not in TASK_OK:
                out.append("RED: the Dropbox mirror task '%s' last result was %s (0 is clean; robocopy 1 to 7 are also fine)" % (task, res))
        except Exception:
            out.append("RED: could not read the Dropbox mirror task '%s'" % task)
    script = cfg.get("mirror_script") if _lib.role() == "main" else None
    if script and Path(script).is_file() and mems:
        t = Path(script).read_text("utf-8", "replace").lower().replace("/", "\\")
        if ".claude\\projects" not in t and not any(str(m).lower().replace("/", "\\") in t for m in mems):
            out.append("RED: the memory folder is not in the mirror script %s" % script)
    for check in (check_untracked_tooling, check_now_sizes):
        try:
            out.extend(check(root))
        except Exception as e:
            out.append("RED: doctor check %s could not run: %s" % (check.__name__, e))
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
