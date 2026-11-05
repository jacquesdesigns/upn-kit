"""PreToolUse guard for Dropbox and "20. RAW". Reading is always allowed.

Dropbox (any folder with "dropbox" in its name): Claude MAY create a NEW file or folder (a Write to a path that does not
exist yet, a copy whose target name does not exist yet, mkdir of a new folder). It may NOT overwrite or edit an existing
file, move, rename or delete anything, copy over an existing file, run robocopy there, or unzip/tar into the folder.
"20. RAW" (and any root in config.json "protected"): fully read-only, no new files either.
Paths in config.json "allow" are let through (the person edits that list, Claude does not). PROMPT-1 puts the brain's Dropbox
mirror folder there, so the mirror (robocopy /MIR in or out, the hold file, pulling it back) keeps working exactly as before.
If the brain itself lives inside Dropbox (the person opens the Dropbox copy on their other computer), normal edits inside
that brain are exempt; "20. RAW" inside it stays read-only, and the rest of Dropbox stays new-files-only.

Covers Write / Edit / MultiEdit / NotebookEdit, shell commands (Bash or PowerShell), and the claude.ai Dropbox
connector's tools (mcp__claude_ai_Dropbox__*): read, list, search and get-link tools pass; a tool that uploads or creates
passes only when its input says it adds a new file and cannot overwrite; move, delete, rename, copy, restore, update and
anything unknown are blocked.
Limit: a command that builds its target path at run time (python -c, a variable) cannot be read by a hook.

Re-reads: a full Read of a file over 30 KB that this conversation has already read is refused, unless the file changed
since (size or time) or a line range is asked (offset, limit or pages). Bids and tenders are long, and each re-read
brings the handover line nearer. A compaction or a clear empties the list (the SessionStart hook with matcher
"clear|compact" runs this file), because the file is then no longer in the conversation.
"""
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

DROPBOX = re.compile(r"(^|/)[^/]*dropbox[^/]*(/|$)", re.I)
RAW = re.compile(r"(^|/)20\. ?raw(/|$)", re.I)

DELETE_MOVE = re.compile(r"(^|[\s;&|(])(rm|rmdir|del|erase|rd|mv|move|ren|rename|move-item|remove-item|rename-item|ri|mi|rni|trash|git\s+mv|git\s+rm)(\s|$)", re.I)
COPY = re.compile(r"(^|[\s;&|(])(cp|copy|copy-item|cpi|xcopy|robocopy|rsync|scp|install)(\s|$)", re.I)
ROBO = re.compile(r"(^|[\s;&|(])robocopy(\s|$)", re.I)
MKDIR = re.compile(r"(^|[\s;&|(])(mkdir|md)(\s|$)", re.I)
NEWITEM_DIR = re.compile(r"(^|[\s;&|(])(new-item|ni)(\s|$).*-ItemType\s+Directory", re.I)
WRITERS = re.compile(r"(^|[\s;&|(])(set-content|add-content|out-file|new-item|ni|tee|tee-object|sc|ac|clear-content|touch|truncate|sed\s+-i|compress-archive)(\s|$)", re.I)
EXTRACT = re.compile(r"(^|[\s;&|(])(expand-archive|unzip|tar|7z|7za|gunzip)(\s|$)", re.I)

# connector tool names: the last part of mcp__claude_ai_Dropbox__<verb>
CONNECTOR = re.compile(r"^mcp__[A-Za-z0-9_]*dropbox[A-Za-z0-9_]*__(.+)$", re.I)
READ_VERBS = re.compile(r"^(list|search|get|fetch|download|read|preview|view|find|lookup|metadata|check|stat)", re.I)
CREATE_VERBS = re.compile(r"^(upload|create|save|put|write|add|mkdir|make|new)", re.I)


def config_lists():
    cfg = _lib.load_config()
    return [_lib.norm(p) for p in cfg.get("protected", [])], [_lib.norm(p) for p in cfg.get("allow", [])]


EXEMPT_BRAINS = []   # brain roots that sit inside Dropbox and are the person's working copy (set in main)


def find_brain_in_dropbox(cwd):
    """Brain roots (config brain, or the one the session runs in) that live under a Dropbox path."""
    found = []
    cands = []
    cfg_brain = _lib.load_config().get("brain")
    if cfg_brain:
        cands.append(Path(cfg_brain))
    if cwd:
        c = Path(cwd)
        for p in [c] + list(c.parents):
            try:
                if (p / "CLAUDE.md").is_file() and ((p / "wiki").is_dir() or (p / "upn").is_dir()):
                    cands.append(p)
                    break
            except OSError:
                break
    for b in cands:
        n = _lib.norm(b)
        if DROPBOX.search(n + "/") and n not in found:
            found.append(n)
    return found


def kind(path):
    """'raw' (fully read-only), 'dropbox' (new files only) or None."""
    if not path:
        return None
    p = _lib.norm(path)
    extra, allow = config_lists()
    if any(p == a or p.startswith(a + "/") for a in allow):
        return None
    if RAW.search(p + "/") or any(p == r or p.startswith(r + "/") for r in extra):
        return "raw"
    if any(p == b or p.startswith(b + "/") for b in EXEMPT_BRAINS):
        return None
    if DROPBOX.search(p + "/"):
        return "dropbox"
    return None


def exists(path):
    try:
        return os.path.exists(path)
    except (OSError, ValueError):
        return True   # cannot tell: treat as existing, so it is blocked


def tokens(cmd):
    try:
        return shlex.split(cmd, posix=False)
    except ValueError:
        return cmd.split()


def clean(tok):
    return tok.strip("'\"").rstrip(";|&)")


def is_switch(t):
    """-r, -Recurse, /S, /E:x are options; /var/x and C:\\x are paths."""
    return t.startswith("-") or bool(re.match(r"^/[A-Za-z?]{1,3}(:.*)?$", t))


def new_only(path, what):
    """Return a block reason if `path` is protected and the action is not a plain create of a new thing."""
    k = kind(path)
    if k is None:
        return None
    if k == "raw":
        return "%s is in \"20. RAW\", which is read-only (no new files either)" % path
    if exists(path):
        return "%s already exists in Dropbox; Claude only saves new files there, never overwrites or edits" % path
    return None


def block_any(path, what):
    k = kind(path)
    if k is None:
        return None
    return "%s is in %s; Claude cannot %s anything there" % (path, "\"20. RAW\"" if k == "raw" else "Dropbox", what)


def command_block(cmd):
    """Return a reason if the shell command would break the rules, else None."""
    for seg in re.split(r"(?:&&|\|\||;|\n)", cmd):
        seg_s = seg.strip()
        if not seg_s:
            continue
        toks = [clean(t) for t in tokens(seg_s)]
        # redirects: > creates, >> appends; both fine only into a NEW file in Dropbox
        for m in re.finditer(r"\d?>>?\s*(\"[^\"]+\"|'[^']+'|[^\s;|&]+)", seg_s):
            r = new_only(clean(m.group(1)), "write")
            if r:
                return r
        args = [t for t in toks[1:] if t and not is_switch(t)]
        paths = [t for t in args if re.search(r"[\\/]|^[A-Za-z]:", t)]

        if DELETE_MOVE.search(seg_s):
            for t in paths:
                r = block_any(t, "move, rename or delete")
                if r:
                    return r
        if EXTRACT.search(seg_s):
            dests = re.findall(r"(?:-DestinationPath|-Dest|-d|-C)\s+(\"[^\"]+\"|'[^']+'|[^\s]+)", seg_s, re.I)
            dests += re.findall(r"\s-o(\"[^\"]+\"|'[^']+'|[^\s]+)", seg_s)
            if re.search(r"expand-archive", seg_s, re.I) and not dests and len(paths) > 1:
                dests = [paths[-1]]
            if re.search(r"\b(tar|unzip)\b", seg_s, re.I) and not dests:
                dests = []
            for d in dests:
                r = block_any(clean(d), "unpack into")
                if r:
                    return r
        if ROBO.search(seg_s):
            nonflag = [t for t in toks[1:] if t and not is_switch(t)]
            dest = nonflag[1] if len(nonflag) > 1 else None
            if dest and kind(dest):
                return "robocopy into %s is blocked (it can replace or purge files; /MIR and /PURGE delete). Save a new file instead" % dest
        elif COPY.search(seg_s):
            nonflag = [t for t in toks[1:] if t and not is_switch(t)]
            m = re.search(r"-(?:Destination|Dest)\s+(\"[^\"]+\"|'[^']+'|\S+)", seg_s, re.I)
            dest = clean(m.group(1)) if m else (nonflag[-1] if len(nonflag) > 1 else None)
            srcs = [t for t in nonflag if t != dest and not t.startswith("-")]
            if dest and kind(dest):
                if kind(dest) == "raw":
                    return "%s is in \"20. RAW\", which is read-only" % dest
                target = dest
                if exists(dest) and os.path.isdir(dest):
                    if any(os.path.isdir(s) for s in srcs):
                        return "copying a folder into the existing folder %s could replace files; copy single new files instead" % dest
                    names = [os.path.basename(s.rstrip("\\/")) for s in srcs]
                    clash = [n for n in names if exists(os.path.join(dest, n))]
                    if clash:
                        return "%s already exists in %s; Claude never copies over an existing file" % (clash[0], dest)
                    continue
                if exists(target):
                    return "%s already exists in Dropbox; Claude never copies over an existing file" % target
        if MKDIR.search(seg_s) or NEWITEM_DIR.search(seg_s):
            for t in paths:
                r = new_only(t, "create")
                if r:
                    return r
        elif WRITERS.search(seg_s):
            for t in paths:
                r = new_only(t, "write")
                if r:
                    return r
        if re.search(r"\b(python|py|node)\b", seg_s, re.I):
            m = re.search(r"([A-Za-z]:[\\/][^\"'\s]*(?:dropbox|20\. ?raw)[^\"'\s]*)", seg_s, re.I)
            if m and re.search(r"(open\(|write|unlink|rmtree|copy|move|rename|remove|replace)", seg_s, re.I):
                return "a script that writes to %s cannot be checked; Claude saves new files with the Write tool instead" % m.group(1)
    return None


def connector_block(tool, ti):
    m = CONNECTOR.match(tool)
    if not m:
        return None
    verb = m.group(1)
    if READ_VERBS.match(verb):
        return None
    if CREATE_VERBS.match(verb):
        mode = str(ti.get("mode") or ti.get("write_mode") or ti.get("conflict") or "").lower()
        overwrite = ti.get("overwrite")
        adds = mode in ("add", "new", "create", "autorename", "fail") or ti.get("autorename") is True
        if re.search(r"folder|dir", verb, re.I) and not overwrite:
            return None
        if adds and overwrite not in (True, "true") and mode not in ("overwrite", "update", "replace"):
            return None
        return ("the Dropbox connector tool %s does not say it adds a NEW file without overwriting (its input has no mode of add / "
                "autorename), so Claude cannot know the target is new. Save the file in the job folder in the brain instead" % tool)
    return "the Dropbox connector tool %s changes or removes existing things (move, delete, rename, copy, restore, update); Claude may only read, list, search and add new files" % tool


REREAD_BYTES = 30000


def reads_file(d):
    return _lib.session_file(d.get("session_id"), "reads" + (("-" + str(d["agent_id"])) if d.get("agent_id") else ""))


def reread_block(d, ti):
    """A reason when this is a full re-read of a big file the conversation already holds, unchanged. Records each read."""
    path = ti.get("file_path") or ""
    if not path:
        return None
    try:
        st = os.stat(path)
    except (OSError, ValueError):
        return None
    if any(ti.get(k) is not None for k in ("offset", "limit", "pages")):
        return None
    f = reads_file(d)
    seen = _lib.load_json(f, {})
    key = _lib.norm(path)
    now = [st.st_size, st.st_mtime_ns]
    if seen.get(key) == now and st.st_size > REREAD_BYTES:
        return "%s (%d KB) is already in this conversation and has not changed since it was read" % (
            os.path.basename(path), round(st.st_size / 1024))
    seen[key] = now
    _lib.dump_json(f, seen)
    return None


def main():
    d = _lib.read_input()
    if d.get("hook_event_name") == "SessionStart":   # after a compaction or a clear nothing is held any more
        try:
            reads_file(d).unlink()
        except OSError:
            pass
        return
    tool = d.get("tool_name", "")
    ti = d.get("tool_input") or {}
    if tool == "Read":
        why = reread_block(d, ti)
        if why:
            _lib.deny("ALREADY READ: %s. Use what you already have; to change it, use Edit; to look at one part again, Read "
                      "with offset and limit (a line range)." % why)
        return
    EXEMPT_BRAINS[:] = find_brain_in_dropbox(d.get("cwd"))
    why = None
    if tool in ("Edit", "MultiEdit", "NotebookEdit"):
        why = block_any(_lib.target_path(ti), "edit")
    elif tool == "Write":
        why = new_only(_lib.target_path(ti), "write")
    elif tool in ("Bash", "PowerShell"):
        why = command_block(ti.get("command", "") or "")
    elif tool.lower().startswith("mcp__") and "dropbox" in tool.lower():
        why = connector_block(tool, ti)
    if why:
        _lib.deny("GUARD: %s. In Dropbox Claude can read and save NEW files only (never overwrite, edit, move, rename or delete); "
                  "\"20. RAW\" is read-only. Save the work in the job folder in the brain and tell the person the full path." % why)


if __name__ == "__main__":
    _lib.run(main)
