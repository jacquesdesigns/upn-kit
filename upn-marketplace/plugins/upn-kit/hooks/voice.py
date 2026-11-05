"""PostToolUse voice check: no em dashes, no double dashes, British spelling, fixed straight after each write.

Looks only at the text just written (Write content, Edit new_string) in prose files (.md .txt .html .htm).
Code blocks, inline code, URLs and quoted strings are left alone. Extra rules the person has taught live in
~/.claude/upn-kit/rules.json (see the catch hook). On a hit it tells Claude to fix the file now, before anything else.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

PROSE = re.compile(r"\.(md|txt|html?)$", re.I)
SKIP = re.compile(r"(^|/)(_archive|node_modules|\.claude|20\. ?RAW|\.raw|\.obsidian|upn-kit|memory)(/|$)", re.I)

# (pattern, british form)
US_WORDS = [
    (r"\bcolor(s|ed|ing|ful)?\b", "colour"), (r"\bfavorite(s)?\b", "favourite"), (r"\bbehavior(s|al)?\b", "behaviour"),
    (r"\bneighbo(r|rhood|rhoods|rs)\b", "neighbour/neighbourhood"), (r"\bcenter(s|ed|ing)?\b", "centre"),
    (r"\bgray\b", "grey"), (r"\bcatalog(s)?\b", "catalogue"), (r"\bhonor(s|ed)?\b", "honour"), (r"\blabor\b", "labour"),
    (r"\bdefense\b", "defence"), (r"\boffense\b", "offence"), (r"\bjewelry\b", "jewellery"), (r"\baluminum\b", "aluminium"),
    (r"\btraveling\b|\btraveled\b", "travelling/travelled"), (r"\bmodeling\b|\bmodeled\b", "modelling/modelled"),
    (r"\bcanceled\b|\bcanceling\b", "cancelled/cancelling"), (r"\bfulfill(ment)?\b", "fulfil/fulfilment"),
    (r"\b(organi|recogni|analy|summari|prioriti|utili|authori|speciali|minimi|maximi|emphasi|standardi|capitali|critici|finali|customi|optimi|apologi|visuali|mobili|pedestriani|urbani|memori|stabili|normali|categori|synchroni|digiti|harmoni|locali|generali|centrali|characteri|materiali|legali|formali|initiali)z(e|es|ed|ing|ation|ations|er|ers)\b", "-ise / -isation form"),
]
# first-letter capitals are usually proper nouns (Pew Research Center), so "center" is only flagged in lower case
LOWER_ONLY = {r"\bcenter(s|ed|ing)?\b"}


def strip_noise(text, html=False):
    if html:
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"https?://\S+|[A-Za-z]:[\\/]\S+", " ", text)
    text = re.sub(r'"[^"\n]{1,80}"|“[^”\n]{1,80}”', " ", text)
    return text


def check(text, html=False):
    prose = strip_noise(text, html)
    out = []
    if "\u2014" in prose:
        out.append("em dash (use commas, semicolons, full stops or brackets)")
    if re.search(r"\s\u2013\s", prose):
        out.append("spaced en dash used as a dash (use a comma or full stop)")
    # client--project folder names are paths, not prose: drop any token with a / or \ in it (this also catches the
    # tail of a Windows path cut at a space, "Brain\upn\projects\upn--kit-install\NOW.md") before looking for --
    if re.search(r"(?<![\w-])--(?![\w-])|\w--\w|\s--\s", re.sub(r"\S*[\\/]\S*", " ", prose)):
        out.append("double dash")
    for pat, uk in US_WORDS:
        if not uk:
            continue
        flags = 0 if pat in LOWER_ONLY else re.I
        m = re.search(pat, prose, flags)
        if m:
            out.append('US spelling "%s" (British: %s)' % (m.group(0), uk))
    for r in _lib.load_json(_lib.DATA / "rules.json", {}).get("rules", []):
        try:
            if re.search(r["pattern"], prose, re.I if "i" in r.get("flags", "i") else 0):
                out.append("taught rule: %s" % r.get("reason", r["pattern"]))
        except (re.error, KeyError, TypeError):
            continue
    return out


def main():
    d = _lib.read_input()
    tool = d.get("tool_name", "")
    if tool not in ("Write", "Edit", "MultiEdit"):
        return
    ti = d.get("tool_input") or {}
    path = _lib.target_path(ti)
    if not PROSE.search(path) or SKIP.search(_lib.norm(path)):
        return
    found = check(_lib.written_text(tool, ti), html=bool(re.search(r"\.html?$", path, re.I)))
    if found:
        _lib.emit({"decision": "block",
                   "reason": "VOICE CHECK on %s: %s. Fix these in the file now, before doing anything else, then carry on." % (path, "; ".join(found[:6])),
                   "hookSpecificOutput": {"hookEventName": "PostToolUse",
                                          "additionalContext": "VOICE CHECK: fix %s in %s now." % ("; ".join(found[:6]), path)}})


if __name__ == "__main__":
    _lib.run(main)
