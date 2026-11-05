"""PreToolUse: read the job's NOW file before editing anything in a job folder.

A job folder is any folder under the brain that has a NOW.md (or a HANDOVER*.md) in it or above it. Before the first
Write / Edit there in a session, the NOW file must have been read (or handed over by the session-start hook). If not,
the edit is refused with the file to read. Editing the NOW file itself is always allowed.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

SOURCE = re.compile(r"^(NOW|HANDOVER[\w .-]*)\.md$", re.I)
EXEMPT = re.compile(r"(/_state/|/\.claude/|/memory/|/upn-kit/|/scratchpad/|/temp/|/tmp/|/wiki/)", re.I)


def source_for(path, root):
    """Nearest NOW.md / HANDOVER*.md in the file's folder or an ancestor, stopping at the brain root."""
    p = Path(path)
    root_n = _lib.norm(root)
    for d in [p.parent] + list(p.parent.parents):
        dn = _lib.norm(d)
        if not (dn == root_n or dn.startswith(root_n + "/")) or dn == root_n:
            break
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for n in names:
            if SOURCE.match(n):
                return d / n
    return None


def was_read(src, d):
    target = _lib.norm(src)
    for e in _lib.transcript(d.get("transcript_path", "")):
        for b in _lib.blocks(e):
            if b.get("type") != "tool_use":
                continue
            ti = b.get("input") or {}
            if b.get("name") == "Read" and _lib.norm(ti.get("file_path", "")) == target:
                return True
            if b.get("name") in ("Bash", "PowerShell") and Path(src).name.lower() in (ti.get("command", "") or "").lower() \
                    and re.search(r"\b(cat|type|Get-Content|head|tail|more)\b", ti.get("command", ""), re.I):
                return True
    injected = _lib.load_json(_lib.session_file(d.get("session_id"), "injected"), [])
    return target in [_lib.norm(x) for x in injected]


def main():
    d = _lib.read_input()
    if d.get("tool_name") not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return
    path = _lib.target_path(d.get("tool_input") or {})
    if not path or SOURCE.match(Path(path).name) or EXEMPT.search(_lib.norm(path) + "/"):
        return
    root = _lib.brain_root(d.get("cwd"))
    src = source_for(path, root)
    if not src or was_read(src, d):
        return
    _lib.deny("RIGHT SOURCE: this file is in a job folder. Read %s first (it says what is settled and what is open), "
              "then make the edit." % src)


if __name__ == "__main__":
    _lib.run(main)
