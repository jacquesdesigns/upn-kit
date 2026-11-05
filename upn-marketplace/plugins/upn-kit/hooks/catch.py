"""Catch: when the person corrects Claude, save it as a rule before carrying on.

UserPromptSubmit: spots a correction ("I told you", "you always", "stop doing", "from now on", "not what I asked"...)
and tells Claude to save it first: as a rule in ~/.claude/upn-kit/rules.json when a pattern can check it (a word, a
spelling, a phrase), or as ONE dated line in the memory index otherwise. Until that is done, PreToolUse blocks other edits.
Only the person's own typed words count; machine messages (_lib.MACHINE) do not.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

CORRECTION = re.compile(
    r"\b(i (already )?told you|i('ve| have) already said|i('ve| have) said (it|this|that) (before|already|twice)|how many times|"
    r"you keep \w+ing\b|you always|you never|again\b.*\b(wrong|mistake|did|doing)|(wrong|mistake).*\bagain\b|stop doing|"
    r"don'?t (ever )?do that|not what i asked|you forgot|you didn'?t (check|look|read|use)|that'?s (not right|wrong)|"
    r"remember (this|that)(?=\s*($|[.,!;:]|for\b|next\b|in future\b|i\b|we\b|you\b|it\b|the\b))|from now on|never do|always do)", re.I)
SOFT = re.compile(r"\b(from now on|remember (this|that)|always do|never do)\b", re.I)
PENDING_MINUTES = 30


def is_correction(text):
    m = CORRECTION.search(text)
    if not m:
        return False
    if SOFT.search(m.group(0)) and text.strip().endswith("?"):
        return False
    if "?" in text and re.search(r"\b(why|how (does|do|come)|what('?s| is) the reason)\b", text, re.I):
        return False
    return True


def is_agent_handback(text):
    """Any machine message (agent reports, task notifications, hook output, compaction summaries): _lib.MACHINE."""
    return _lib.is_machine(text[:400])


def is_lesson_write(path):
    p = _lib.norm(path)
    if p.startswith(_lib.norm(_lib.DATA)):
        return True
    return bool(re.search(r"/\.claude/projects/[^/]+/memory/", p + "/"))


def prompt_main(d):
    text = d.get("prompt", "") or ""
    if is_agent_handback(text) or not is_correction(text):
        return
    _lib.dump_json(_lib.session_file(d.get("session_id"), "catch"), {"t": time.time(), "text": text[:200]})
    rules = _lib.DATA / "rules.json"
    mem = ", ".join(str(m) for m in _lib.memory_dirs(d.get("cwd"))) or "the memory folder"
    _lib.context_for("UserPromptSubmit",
        "CATCH: the person is correcting you. Before any other change, turn this into a rule so they never say it twice.\n"
        "1. If a pattern can check it (a word, a spelling, a phrase, a path), add it to %s as {\"id\",\"pattern\",\"flags\",\"reason\",\"said\",\"added\"} "
        "inside {\"rules\": [...]}. The voice check enforces it on every write from then on.\n"
        "2. If it cannot (judgement, process), add ONE dated line to the right topic file in %s: \"- <YYYY-MM-DD> (said): <the rule, with why>\". "
        "Do not create a new memory file for one correction.\n"
        "3. Tell the person in one line which you did. Other file edits stay blocked until one of these is written." % (rules, mem))


def pretool_main(d):
    if d.get("tool_name") not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return
    f = _lib.session_file(d.get("session_id"), "catch")
    pend = _lib.load_json(f, None)
    if not pend:
        return
    if time.time() - pend.get("t", 0) > PENDING_MINUTES * 60:
        try:
            f.unlink()
        except OSError:
            pass
        return
    path = _lib.target_path(d.get("tool_input") or {})
    if is_lesson_write(path):
        try:
            f.unlink()
        except OSError:
            pass
        return
    _lib.deny("CATCH: the person just corrected you (\"%s\"). Save the correction as a rule first (rules.json or one dated memory line), "
              "then carry on with this edit." % pend.get("text", "")[:80])


def main():
    d = _lib.read_input()
    if d.get("hook_event_name") == "PreToolUse" or "tool_name" in d:
        pretool_main(d)
    else:
        prompt_main(d)


if __name__ == "__main__":
    _lib.run(main)
