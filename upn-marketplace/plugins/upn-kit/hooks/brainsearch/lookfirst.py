#!/usr/bin/env python3
"""UserPromptSubmit hook: look at the brain before answering about the past.

Reads the hook JSON on stdin ({"prompt": "..."}). If the prompt is about the past or about status
(a plain rule-based test, no model), it runs the brain-search ranking on the prompt's content words
and prints at most 5 lines to stdout, which Claude Code adds to the context:

  LOOK FIRST (brain-search, ranked, newest boosted): <date> <path>: <snippet>

Otherwise it prints nothing. It never fires on a machine message (_lib.MACHINE: agent reports, task notifications,
hook output, compaction summaries). Each block it prints adds one line to lookfirst-hits.log in the kit folder
(time, session, lines, first path), so the one-month report can count whether it earns its place. It never fails the prompt: every error ends in exit 0 with no output.
Pure standard library, no model call, a few tens of milliseconds.
"""
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent))
import _lib  # noqa: E402  (hooks/_lib.py: the shared machine-message pattern and the kit folder)

PREFIX = "LOOK FIRST (brain-search, ranked, newest boosted): "
MAX_LINES = 5
MAX_WORDS = 12
SNIP_CHARS = 150

PAST = re.compile(
    r"\b(did we|have we|had we|what did|when did|where did|why did|who did|how did we|last time|decided|"
    r"decide|status|what is live|what's live|whats live|where are we|where were we|remember|recall|before|"
    r"yesterday|last week|last month|earlier|already|previously|used to|the other day|we agreed|we said|"
    r"did i|have i|was it|were we)\b",
    re.I,
)
# words the trigger phrases are made of, dropped from the search so they do not drown the topic
TRIGGER_WORDS = {"decided", "decide", "status", "remember", "recall", "agreed", "said", "previously", "live",
                 "week", "month"}


def job_names():
    """Folder names of the jobs with a NOW.md (job numbers and names), so a question naming a job looks first."""
    names = set()
    try:
        import common
        for path, src in common.discover():
            if src == "now":
                for w in re.split(r"[\s_\-]+", Path(path).parent.name.lower()):
                    if len(w) >= 3:
                        names.add(w)
    except Exception:
        pass
    return names


def is_about_the_past(prompt):
    if PAST.search(prompt):
        return True
    if "?" in prompt:
        low = prompt.lower()
        return any(re.search(r"\b%s\b" % re.escape(n), low) for n in job_names())
    return False


def content_words(prompt):
    import search  # brainsearch/search.py
    ws = [w for w in search.words(prompt[:600]) if len(w) > 1]
    keep = [w for w in ws if w.lower() not in search.STOP and w.lower() not in TRIGGER_WORDS]
    seen, out = set(), []
    for w in keep:
        if w.lower() not in seen:
            seen.add(w.lower())
            out.append(w)
    return out[:MAX_WORDS]


def lines_for(prompt):
    if not prompt or not prompt.strip() or _lib.is_machine(prompt) or not is_about_the_past(prompt):
        return []
    import search
    words = content_words(prompt)
    if not words:
        return []
    con, rows, _extra, _named = search.search(" ".join(words), MAX_LINES)
    if con is None or not rows:
        return []
    out = []
    for r in rows[:MAX_LINES]:
        snip = re.sub(r"\s+", " ", (r["snip"] or r["summary"] or "")).strip(" .")
        if len(snip) > SNIP_CHARS:
            snip = snip[: SNIP_CHARS - 1].rstrip() + "…"
        out.append("%s%s %s: %s" % (PREFIX, r["date"], r["rel"], snip))
    return out


HITS = "lookfirst-hits.log"


def count_hit(session_id, out):
    """One line per LOOK FIRST block in the kit folder: local time, session, how many lines, the first path offered."""
    try:
        first = out[0][len(PREFIX):].split(" ", 1)[1].split(": ", 1)[0]
        _lib.DATA.mkdir(parents=True, exist_ok=True)
        with open(_lib.DATA / HITS, "a", encoding="utf-8") as f:
            f.write("%s %s %d %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"),
                                       re.sub(r"[^A-Za-z0-9]", "", session_id or "")[:8] or "-", len(out), first))
    except Exception:
        pass


def main():
    try:
        raw = sys.stdin.read()
        prompt, sid = "", ""
        if raw.strip():
            try:
                data = json.loads(raw)
                prompt = data.get("prompt", "") if isinstance(data, dict) else ""
                sid = data.get("session_id", "") if isinstance(data, dict) else ""
            except ValueError:
                prompt = raw
        out = lines_for(str(prompt))
        if out:
            count_hit(str(sid), out)
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass
            sys.stdout.write("\n".join(out) + "\n")
    except BaseException:  # never fail the prompt
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
