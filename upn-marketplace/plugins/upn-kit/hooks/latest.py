"""PostToolUse: keeps a job's NOW.md fresh during the day.

After each write to this conversation's own notes file (_state/<date>-<session>.md), its title, its NOW / OPEN / GATE /
WAITING lines and its newest facts are copied into the NOW.md of the job the conversation works in, as one
"## LATEST (auto ...)" section, replaced in place, never added twice. Without this a NOW file changes only at 23:00 and
at close-out, so a second conversation the same day reads the morning's version.

The job: the NOW.md in the folder the conversation was opened in (or a folder above it, up to the brain); else the job
folder of the newest file this conversation wrote. No job found, nothing written. Writes by subagents are ignored.
"""
import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

HEAD = "## LATEST (auto"
FACTS = 6
MARKS = re.compile(r"^(NOW|OPEN|GATE|WAITING|ANSWERED):")


def job_now(start, root):
    """The nearest NOW.md at or above `start`, never above the brain root, never the brain's own."""
    p = Path(start)
    if not _lib.norm(p).startswith(_lib.norm(root)):
        return None
    for d in [p] + list(p.parents):
        if _lib.norm(d) == _lib.norm(root):
            break
        n = d / "NOW.md"
        if n.is_file():
            return n
    return None


def job_for(d, root, notes):
    now = job_now(d.get("cwd") or os.getcwd(), root)
    if now:
        return now
    written = []
    for e in _lib.transcript(d.get("transcript_path", "")):
        for b in _lib.blocks(e):
            if b.get("type") == "tool_use" and b.get("name") in _lib.WRITE_TOOLS:
                written.append(_lib.target_path(b.get("input") or {}))
    for fp in reversed(written):
        if fp and _lib.norm(fp) != _lib.norm(notes):
            now = job_now(Path(fp).parent, root)
            if now:
                return now
    return None


def block(notes, sid8):
    lines = notes.read_text("utf-8", "replace").splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "(untitled)")
    marks = [l.strip() for l in lines[:15] if MARKS.match(l.strip())]
    facts = [l.rstrip() for l in lines if l.startswith("- ")][:FACTS]
    when = datetime.datetime.now().strftime("%d %b %H:%M")
    head = ["%s, from conversation %s at %s; that conversation's own notes, not checked)" % (HEAD, sid8, when),
            "From %s: %s" % (notes.name, title)]
    return "\n".join(head + marks + facts) + "\n"


def put(now_md, new_block):
    """Replace the LATEST section, or put it before the first "## " heading. True when the file changed."""
    txt = now_md.read_text("utf-8", "replace")
    at = txt.find(HEAD)
    if at >= 0:
        end = txt.find("\n## ", at + 1)
        new = txt[:at] + new_block + ("\n" + txt[end + 1:] if end >= 0 else "")
    else:
        first = txt.find("\n## ")
        new = (txt[:first + 1] + new_block + "\n" + txt[first + 1:]) if first >= 0 else txt.rstrip("\n") + "\n\n" + new_block
    if new == txt:
        return False
    tmp = now_md.with_name(now_md.name + ".latest-tmp")
    tmp.write_text(new, encoding="utf-8")
    os.replace(str(tmp), str(now_md))
    return True


def main():
    d = _lib.read_input()
    if d.get("agent_id"):
        return
    sid8 = re.sub(r"[^A-Za-z0-9]", "", d.get("session_id") or "")[:8]
    if not sid8:
        return
    cwd = d.get("cwd") or os.getcwd()
    folder = _lib.state_dir(cwd)
    ti = d.get("tool_input") or {}
    if d.get("tool_name") in ("Bash", "PowerShell"):   # a heredoc, Set-Content or redirect into the notes file
        m = re.search(r"\d{4}-\d\d-\d\d-%s\.md" % re.escape(sid8), str(ti.get("command") or ""))
        notes = folder / m.group(0) if m else None
    else:
        fp = _lib.target_path(ti)
        notes = Path(fp) if fp else None
    if not notes or not re.match(r"^\d{4}-\d\d-\d\d-%s\.md$" % re.escape(sid8), notes.name):
        return
    if _lib.norm(notes.parent) != _lib.norm(folder) or not notes.is_file():
        return
    now = job_for(d, _lib.brain_root(cwd), notes)
    if now:
        put(now, block(notes, sid8))


if __name__ == "__main__":
    _lib.run(main)
