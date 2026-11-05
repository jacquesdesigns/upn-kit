"""Brain-search for the UPN kit: paths, source discovery and the SQLite FTS5 schema. Standard library only.

Scope is fixed on purpose: the person's memory folder(s), wiki/, every NOW.md and HANDOVER*.md, every CLAUDE.md,
the root MEMORY.md. Never entered: _archive, .raw, "20. RAW", node_modules, .git, .obsidian, any Dropbox folder.
The database lives in ~/.claude/upn-kit/brain.db, outside the brain and outside Dropbox.
"""
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

ROOT = Path(os.environ.get("BRAIN_SEARCH_ROOT") or _lib.brain_root())
MEMORY_DIRS = [Path(p) for p in os.environ.get("BRAIN_SEARCH_MEMORY", "").split(os.pathsep) if p] or _lib.memory_dirs()
DB_DIR = Path(os.environ.get("BRAIN_SEARCH_DB_DIR") or _lib.DATA)
DB_PATH = DB_DIR / "brain.db"
ALIASES_PATH = Path(__file__).resolve().parent / "aliases.json"

SKIP_DIRS = set(_lib.SKIP_DIRS) | {"_context", "_Desktop Claude Archive", "_second-brain-removed", "claude-obsidian"}
TEXT_EXT = {".md", ".txt"}
MAX_BODY_CHARS = 300_000
LONG_FILE_LINES = 150
MAX_DEPTH = 7
ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
# Standing instructions are not truer because they are newer: no recency boost for these.
NO_DECAY_SOURCES = {"memory", "root", "business"}
SCHEMA_VERSION = "5"
SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
  id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, rel TEXT NOT NULL, source TEXT NOT NULL,
  date TEXT NOT NULL DEFAULT '', title TEXT NOT NULL, mtime REAL NOT NULL, size INTEGER NOT NULL,
  hash TEXT NOT NULL, lines INTEGER NOT NULL, summary TEXT NOT NULL DEFAULT '',
  summary_kind TEXT NOT NULL DEFAULT 'fallback', questions TEXT NOT NULL DEFAULT '',
  aliases TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT '', indexed_at REAL NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
  title, aliases, path, summary, questions, body, tokenize = 'porter unicode61 remove_diacritics 2'
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


def is_dropbox(name):
    return "dropbox" in name.lower()


def connect(create=True):
    if create:
        DB_DIR.mkdir(parents=True, exist_ok=True)
    elif not DB_PATH.exists():
        return None
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    if create:
        try:
            ok = con.execute("SELECT v FROM meta WHERE k='schema'").fetchone()
            ok = ok and ok[0] == SCHEMA_VERSION
        except sqlite3.Error:
            ok = False
        if not ok:
            for t in ("fts", "docs", "meta"):
                con.execute("DROP TABLE IF EXISTS " + t)
            con.executescript(SCHEMA)
            con.execute("INSERT OR REPLACE INTO meta (k,v) VALUES ('schema', ?)", (SCHEMA_VERSION,))
            con.commit()
    return con


def walk(base, exts=TEXT_EXT, max_depth=MAX_DEPTH):
    base = Path(base)
    if not base.is_dir():
        return
    stack = [(base, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            continue
        for e in entries:
            if e.name.startswith(".") or e.is_symlink():
                continue
            if e.is_dir():
                if e.name in SKIP_DIRS or is_dropbox(e.name):
                    continue
                if depth + 1 <= max_depth:
                    stack.append((Path(e.path), depth + 1))
            elif e.is_file() and Path(e.name).suffix.lower() in exts:
                yield Path(e.path)


def discover():
    """Sorted list of (path, source) for everything in scope."""
    found = {}

    def add(p, source):
        p = Path(p)
        if p.is_file():
            found.setdefault(str(p), source)

    for m in MEMORY_DIRS:
        for p in walk(m, {".md"}, max_depth=1):
            add(p, "memory")
    for p in walk(ROOT / "wiki", {".md"}):
        add(p, "wiki")
    add(ROOT / "CLAUDE.md", "root")
    add(ROOT / "MEMORY.md", "root")
    add(ROOT / "hot.md", "wiki")
    for p in walk(ROOT, {".md"}):
        n = p.name
        if n == "NOW.md":
            add(p, "now")
        elif re.match(r"^HANDOVER[\w .-]*\.md$", n, re.I):
            add(p, "now")
        elif n == "CLAUDE.md":
            add(p, "business")
    for sub, src in (("atoms", "atoms"), ("storage", "storage")):
        for p in walk(_lib.DATA / sub, {".md"}, max_depth=0):
            add(p, src)
    out = []
    mem = [str(m.resolve()) for m in MEMORY_DIRS] + [str(_lib.DATA.resolve())]
    root_s = str(ROOT.resolve())
    for p, src in found.items():
        rp = str(Path(p).resolve())
        if not (rp.startswith(root_s + os.sep) or any(rp.startswith(m + os.sep) for m in mem)):
            continue
        out.append((p, src))
    return sorted(out)


def doc_date(fm, name, mtime):
    import time as _t
    for k in ("updated", "created", "date"):
        m = ISO_DATE.search(str(fm.get(k, "")))
        if m:
            return "-".join(m.groups())
    m = ISO_DATE.search(name)
    if m:
        return "-".join(m.groups())
    return _t.strftime("%Y-%m-%d", _t.localtime(mtime))


def rel_of(path):
    p = Path(path)
    for sub in ("atoms", "storage"):
        try:
            return sub + "/" + str(p.relative_to(_lib.DATA / sub)).replace("\\", "/")
        except ValueError:
            pass
    for m in MEMORY_DIRS:
        try:
            return "memory/" + str(p.relative_to(m)).replace("\\", "/")
        except ValueError:
            pass
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)
