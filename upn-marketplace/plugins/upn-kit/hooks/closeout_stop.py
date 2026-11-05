"""Stop hook: offers the close-out once per session, so nobody types "save to the wiki" again.

If this session has written at least 3 files and the close-out skill has not run, Claude is asked to offer it in one
line (once per session, never again). The person says yes and the close-out skill writes the wiki page, the job's NOW
file and lists every saved file with its full path.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

MIN_WRITES = 3


def main():
    d = _lib.read_input()
    if d.get("stop_hook_active"):
        return
    flag = _lib.session_file(d.get("session_id"), "closeout-offered")
    if flag.exists():
        return
    writes, ran = set(), False
    for e in _lib.transcript(d.get("transcript_path", "")):
        for b in _lib.blocks(e):
            if b.get("type") != "tool_use":
                continue
            n, ti = b.get("name", ""), b.get("input") or {}
            if n in ("Write", "Edit", "MultiEdit"):
                fp = str(ti.get("file_path", "")).replace("\\", "/")
                if "/_state/" in fp or "/.claude/" in fp or "/upn-kit/" in fp:
                    continue
                writes.add(fp)
            if n == "Skill" and "close-out" in str(ti.get("skill", "")):
                ran = True
    if ran or len(writes) < MIN_WRITES:
        return
    _lib.dump_json(flag, {"offered": True})
    _lib.emit({"decision": "block",
               "reason": "CLOSE-OUT: this session has saved %d files and not been closed out. In one short line, offer: \"Shall I close this out? "
                         "I will write the wiki page and update the job's NOW file, then list every file I saved with its full path.\" "
                         "If they say yes, run the close-out skill. Do not offer again this session." % len(writes)})


if __name__ == "__main__":
    _lib.run(main)
