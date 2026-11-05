"""Stop hook: flags a reply that claims done / live / saved without a check after the last change.

Reads this turn from the transcript: the last change (a file written, a copy, a build, a send) and the last check
(a file read back, a listing, a fetch, a test run) after it. If the reply claims the work is done and no check follows
the last change, Claude is asked to check first and then say what it saw. Fires once per turn (stop_hook_active guard).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

CHANGE_CMD = re.compile(r"\b(git\s+(push|commit)|npm\s+run|npx|pnpm|yarn|python\S*\s+\S*(build|render|make|export|generate)\S*|"
                        r"copy|cp|mv|move|ren|robocopy|xcopy|Copy-Item|Move-Item|Set-Content|Out-File|Add-Content|Start-Process|"
                        r"schtasks|deploy|wrangler|pandoc|soffice|libreoffice|Compress-Archive|zip)\b", re.I)
CHECK_CMD = re.compile(r"\b(curl|ls|dir|cat|type|head|tail|wc|stat|Get-ChildItem|Get-Content|Get-Item|Test-Path|Select-String|"
                       r"git\s+(status|log|diff)|plugin\s+validate|pytest|python\S*\s+-c|findstr|grep|rg|file)\b", re.I)
CHECK_TOOLS = re.compile(r"^(Read|WebFetch|Glob|Grep|mcp__playwright__|mcp__claude-in-chrome__|mcp__claude-vscode__getDiagnostics)")
NOTES = re.compile(r"(/_state/|/\.claude/|/memory/|/upn-kit/|/scratchpad/|/Temp/|/tmp/)", re.I)
CLAIM = re.compile(r"\b(done|deployed|shipped|fixed|working|built|finished|in place|is ready|it'?s up|is live|now live|are live|"
                   r"saved|written|created|sent|installed|complete[d]?|all set)\b", re.I)
NEGATED = re.compile(r"(\bnot|\bnever|n't|\bno longer|\byet to be|\bnothing|\bnone|\bwhen|\bonce|\bif|\buntil|\bbefore|\bafter|\bwill be|\bto be|\bcan be|\bshould be|\bcould be)\s+(\w+'?\w*\s+){0,3}$", re.I)


def claim_in(text):
    t = re.sub(r"```.*?```", "", text, flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    t = "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("|"))
    t = re.sub(r'"[^"\n]{1,80}"|“[^”\n]{1,80}”', "", t)
    for m in CLAIM.finditer(t):
        if not NEGATED.search(t[max(0, m.start() - 30):m.start()]):
            return m.group(0)
    return None


def classify(name, ti):
    if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return "other" if NOTES.search(str(ti.get("file_path", "")).replace("\\", "/")) else "change"
    if name in ("Bash", "PowerShell"):
        c = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\s*\1\s*(\n|$)", "\n", ti.get("command", "") or "", flags=re.S)
        if CHANGE_CMD.search(c):
            return "change"
        if CHECK_CMD.search(c):
            return "check"
        return "other"
    return "check" if CHECK_TOOLS.match(name or "") else "other"


def analyse(path):
    """Return (last assistant text of the turn, index of last change, index of last check) for the current turn."""
    entries = list(_lib.transcript(path))
    start = 0
    for i, e in enumerate(entries):
        if _lib.is_user_prompt(e):
            start = i + 1
    last_change = last_check = 0
    text = ""
    n = 0
    for e in entries[start:]:
        if e.get("type") != "assistant":
            continue
        for b in _lib.blocks(e):
            if b.get("type") == "tool_use":
                n += 1
                k = classify(b.get("name", ""), b.get("input") or {})
                if k == "change":
                    last_change = n
                elif k == "check":
                    last_check = n
            elif b.get("type") == "text" and b.get("text", "").strip():
                text = b["text"]
    return text, last_change, last_check


def main():
    d = _lib.read_input()
    if d.get("stop_hook_active"):
        return
    text, lc, lk = analyse(d.get("transcript_path", ""))
    if not text:
        text = d.get("last_assistant_message", "") or ""
    claim = claim_in(text) if text else None
    if claim and lc > 0 and lk < lc:
        _lib.emit({"decision": "block",
                   "reason": 'PROOF: your reply says "%s", but nothing was checked after the last change. Check it now (open the file, '
                             'list the folder, run the test, fetch the page), then tell the person what you saw, or say plainly that it is not verified.' % claim})


if __name__ == "__main__":
    _lib.run(main)
