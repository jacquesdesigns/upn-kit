"""UserPromptSubmit: tells Claude the real context fill; checkpoint at 15%, handover at 25%.

The fill comes from the last reply's token usage in the transcript. Every prompt gets one gauge line.
At 15% (once): the hook writes a checkpoint into this session's state file and asks Claude to bring it up to date.
At 25% (once): the hook writes the handover note, with an OPEN line, and asks Claude to finish the step, complete the
note and tell the person to start a new conversation (the next conversation offers the note itself).
Window size: config.json "context_window" (default 1,000,000; set 200000 if the account has the smaller window).
Every gauge line carries the local time, so Claude never invents a time in a note (it is given the date, never the clock).
The handover note keeps the person's last three messages word for word, and its OPEN line names the live thing to open first.
Nothing here opens windows or types for anyone.
"""
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

LEVELS = (("handover", 25), ("checkpoint", 15))
VERBATIM_CHARS = 2000

OPEN_RULE = ('make the OPEN line say the one next step in a few words. When the work is on a live thing (a file, a page, a link), '
             'the line starts with it: "OPEN: next = open <file | page | link> FIRST, then <the one next step>". The next conversation '
             'carries on ON that thing: no new options, no restart.')


def clock_note(clock):
    return " The time now is %s (local): use it for any time you write in the note, and never write a time you did not read." % clock


def fill(path, window):
    tokens = None
    for e in _lib.transcript(path):
        u = (e.get("message") or {}).get("usage") if e.get("type") == "assistant" else None
        if isinstance(u, dict):
            t = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
            if t:
                tokens = t
    if tokens is None:
        return None, None
    return tokens, 100.0 * tokens / max(window, 1)


def state_path(d):
    sid8 = re.sub(r"[^A-Za-z0-9]", "", d.get("session_id") or "none")[:8]
    folder = _lib.state_dir(d.get("cwd"))
    return folder / ("%s-%s.md" % (datetime.date.today().isoformat(), sid8)), sid8


def recent_facts(path):
    prompts, files = [], []
    for e in _lib.transcript(path):
        if _lib.is_user_prompt(e):
            t = " ".join(b.get("text", "") for b in _lib.blocks(e) if b.get("type") == "text").strip()
            if t:
                prompts.append(t)
        for b in _lib.blocks(e):
            if b.get("type") == "tool_use" and b.get("name") in ("Write", "Edit", "MultiEdit"):
                fp = (b.get("input") or {}).get("file_path")
                if fp and fp not in files:
                    files.append(fp)
    return prompts[-3:], files[-15:]


def write_state(d, level, pct, current=""):
    p, sid8 = state_path(d)
    p.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    prompts, files = recent_facts(d.get("transcript_path", ""))
    # the message that set this hook off is not in the transcript yet
    if current.strip() and (not prompts or prompts[-1] != current.strip()):
        prompts.append(current.strip())
    prompts = prompts[-3:]
    stamp = "[%s | job: see NOW file | source: hook]" % now.strftime("%Y-%m-%d")
    block = ["", "## %s %s (context %d%%)" % ("Handover" if level == "handover" else "Checkpoint", now.strftime("%H:%M"), pct),
             "- files written this session %s: %s" % (stamp, "; ".join(files) or "none"),
             "", "### The person said, last three (verbatim)"]
    for t in prompts or ["(none yet)"]:
        t = t if len(t) <= VERBATIM_CHARS else t[:VERBATIM_CHARS] + " [... cut ...]"
        block.append("> " + t.replace("\n", "\n> "))
        block.append("")
    if p.exists():
        txt = p.read_text("utf-8", "replace")
    else:
        txt = "# STATE (untitled, give it a one-line title)\nsession: %s | started %s\n" % (sid8, now.strftime("%Y-%m-%d %H:%M"))
    if level == "handover":
        txt = re.sub(r"^OPEN:.*\n", "", txt, flags=re.M)
        lines = txt.split("\n")
        lines.insert(1, "OPEN: next = (Claude: replace with the one next step, in a few words)")
        txt = "\n".join(lines)
    p.write_text(txt.rstrip("\n") + "\n" + "\n".join(block) + "\n", encoding="utf-8")
    return p


def main():
    d = _lib.read_input()
    cfg = _lib.load_config()
    window = int(cfg.get("context_window", 1_000_000))
    tokens, pct = fill(d.get("transcript_path", ""), window)
    clock = datetime.datetime.now().strftime("%H:%M")
    if pct is None:
        _lib.context_for("UserPromptSubmit", "Time now: %s (local)." % clock)
        return
    p = int(round(pct))
    flag = _lib.session_file(d.get("session_id"), "warned")
    warned = _lib.load_json(flag, [])
    due = [name for name, at in LEVELS if pct >= at and name not in warned]
    advice = "past the handover line" if p >= 25 else "checkpoint passed; keep the state file current" if p >= 15 else "fine"
    text = "Context window: %d%% full (%s), time now %s (local)." % (p, advice, clock)
    if due:
        level = due[0]
        warned = list(set(warned + [n for n, at in LEVELS if pct >= at]))
        _lib.dump_json(flag, warned)
        sp = write_state(d, level, p, d.get("prompt", "") or "")
        if level == "checkpoint":
            text += ("\nCONTEXT %d%%: checkpoint saved to %s.%s Finish the step you are on, then bring that file up to date: what is built, what is "
                     "VERIFIED and how, what is not verified, decisions with reasons, the exact next steps. Keep the section \"The person said, last "
                     "three (verbatim)\" word for word. Put [date | job | source] on every fact. "
                     "Carry on with the task. Tell the person in one line: \"Context is at %d%%, checkpoint saved.\"" % (p, sp, clock_note(clock), p))
        else:
            text += ("\nCONTEXT %d%%: hand-over line. The handover note is at %s.%s Finish the step you are on (start nothing new), complete the note "
                     "(what is built, what is VERIFIED, what is not, decisions with reasons, exact next steps; [date | job | source] on every fact; keep "
                     "the section \"The person said, last three (verbatim)\" word for word), and %s The message the person just sent is the next step: "
                     "put it in the OPEN line and do not start it here. Then tell the person in one line: \"Context is at %d%%. Please start a "
                     "new conversation; it will offer to pick up from the note at %s.\"" % (p, sp, clock_note(clock), OPEN_RULE, p, sp))
    _lib.context_for("UserPromptSubmit", text)


if __name__ == "__main__":
    _lib.run(main)
