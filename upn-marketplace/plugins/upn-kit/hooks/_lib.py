"""Shared helpers for the UPN kit hooks. Standard library only; works on Windows and Mac.

Every hook calls run(main). A hook can never break a session: any error ends in exit 0 with no output.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

DATA = Path(os.environ.get("UPN_KIT_HOME") or (Path.home() / ".claude" / "upn-kit"))
CONFIG = DATA / "config.json"
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)

# folders never entered when walking a brain
SKIP_DIRS = {"_archive", ".raw", "node_modules", ".git", ".obsidian", ".playwright-mcp", "__pycache__",
             "20. RAW", ".venv", "venv", "_state"}


def utf8_out():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def read_input():
    utf8_out()
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        d = json.loads(raw) if raw.strip() else {}
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def run(fn):
    try:
        fn()
    except SystemExit:
        raise
    except BaseException:
        pass
    sys.exit(0)


def load_config():
    try:
        d = json.loads(CONFIG.read_text("utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_config(cfg):
    DATA.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def slug_of(path):
    """Claude Code's project folder name for a working directory: every non-alphanumeric becomes a dash."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def brain_root(cwd=None):
    cfg = load_config()
    b = cfg.get("brain")
    if b and Path(b).is_dir():
        return Path(b)
    c = Path(cwd or os.getcwd())
    for p in [c] + list(c.parents):
        if (p / "CLAUDE.md").is_file() and ((p / "wiki").is_dir() or (p / "upn").is_dir()):
            return p
    return c


def role():
    """'main' (this computer holds the master brain) or 'second' (the other computer; no git, no nightly writes into the brain)."""
    return "second" if str(load_config().get("role", "main")).lower() == "second" else "main"


def state_dir(cwd=None):
    """Where session state files live: _state in the brain on the main machine; outside the brain (and so outside Dropbox) on a second one."""
    if role() == "second":
        return DATA / "state"
    return brain_root(cwd) / "_state"


def memory_dirs(cwd=None):
    cfg = load_config()
    out = [Path(p) for p in cfg.get("memory_dirs", []) if Path(p).is_dir()]
    if out:
        return out
    base = Path.home() / ".claude" / "projects"
    cands = [brain_root(cwd), Path(cwd or os.getcwd())]
    for c in cands:
        m = base / slug_of(c) / "memory"
        if m.is_dir() and m not in out:
            out.append(m)
    return out


def norm(p):
    """Forward slashes, lower case, no trailing slash: for comparing Windows and Mac paths."""
    return str(p).replace("\\", "/").rstrip("/").lower()


def session_file(sid, name):
    d = DATA / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d / ("%s-%s.json" % (re.sub(r"[^A-Za-z0-9_-]", "", sid or "none")[:40], name))


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except Exception:
        return default


def dump_json(path, obj):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def transcript(path):
    """Yield the transcript's JSON lines (dicts). Silent on any problem."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except ValueError:
                        continue
    except Exception:
        return


def blocks(entry):
    m = entry.get("message") if isinstance(entry, dict) else None
    c = m.get("content") if isinstance(m, dict) else None
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    return [b for b in (c or []) if isinstance(b, dict)]


def is_user_prompt(entry):
    """A real typed prompt, not a tool result or a system note."""
    if entry.get("type") != "user":
        return False
    bs = blocks(entry)
    if not bs or any(b.get("type") == "tool_result" for b in bs):
        return False
    t = " ".join(b.get("text", "") for b in bs if b.get("type") == "text").strip()
    return bool(t) and not t.startswith("<")


def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                 "permissionDecisionReason": reason}})


def context_for(event, text):
    emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def written_text(tool, ti):
    """The new text a Write/Edit/MultiEdit puts on disk."""
    if tool == "Write":
        return ti.get("content", "") or ""
    if tool == "Edit":
        return ti.get("new_string", "") or ""
    if tool == "MultiEdit":
        return "\n".join(e.get("new_string", "") or "" for e in ti.get("edits", []) if isinstance(e, dict))
    return ""


WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def target_path(ti):
    return ti.get("file_path") or ti.get("notebook_path") or ti.get("path") or ""
