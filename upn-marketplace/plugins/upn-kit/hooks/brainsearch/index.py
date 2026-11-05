#!/usr/bin/env python3
"""Build or refresh the brain-search index (SQLite FTS5). No model calls: long files use their description or first paragraph.

Incremental: a file is only re-read if its mtime or size changed.

  index.py          refresh
  index.py --full   rebuild every row
  index.py --if-old refresh only when the index is more than a day old
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


# ---------------------------------------------------------------- parsing

def parse_list(raw):
    """'["a", "b"]' or 'a, b' -> ['a', 'b']"""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [x.strip().strip("'\"") for x in raw.split(",") if x.strip().strip("'\"")]


def parse(text):
    """Return (frontmatter dict, body without frontmatter). fm['_aliases'] is a list."""
    fm = {"_aliases": []}
    m = FM.match(text)
    if m:
        lines = m.group(1).splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            i += 1
            if ":" in line and not line.startswith((" ", "\t", "-")):
                k, v = line.split(":", 1)
                k, v = k.strip().lower(), v.strip()
                if k in ("aliases", "alias") and not v:       # block list
                    while i < len(lines) and lines[i].lstrip().startswith("- "):
                        fm["_aliases"].append(lines[i].lstrip()[2:].strip().strip("'\""))
                        i += 1
                elif k in ("aliases", "alias"):
                    fm["_aliases"].extend(parse_list(v))
                else:
                    fm[k] = v.strip("'\"")
        text = text[m.end():]
    return fm, text


def title_of(fm, body, path):
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip().strip("*")[:160]
    if fm.get("name"):
        return fm["name"][:160]
    return Path(path).stem.replace("_", " ").replace("-", " ")


def first_paragraph(body):
    para = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            if para:
                break
            continue
        if s.startswith(("#", "|", "---", "```", "<", "![")):
            if para:
                break
            continue
        para.append(s)
    return " ".join(para)


def one_line(s, n=230):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def fallback_summary(fm, body, title):
    if fm.get("description"):
        return one_line(fm["description"]), "frontmatter"
    para = first_paragraph(body)
    return one_line(("%s. %s" % (title, para)) if para else title), "fallback"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_row(con, existing_id, rec, body):
    cols = ("path", "rel", "source", "date", "title", "mtime", "size", "hash", "lines",
            "summary", "summary_kind", "questions", "aliases", "kind", "indexed_at")
    vals = [rec[c] for c in cols]
    if existing_id is None:
        cur = con.execute("INSERT INTO docs (%s) VALUES (%s)" % (",".join(cols), ",".join("?" * len(cols))), vals)
        did = cur.lastrowid
    else:
        con.execute("UPDATE docs SET %s WHERE id=?" % ",".join(c + "=?" for c in cols), vals + [existing_id])
        did = existing_id
        con.execute("DELETE FROM fts WHERE rowid=?", (did,))
    con.execute("INSERT INTO fts (rowid, title, aliases, path, summary, questions, body) VALUES (?,?,?,?,?,?,?)",
                (did, rec["title"], rec["aliases"], rec["rel"], rec["summary"], rec["questions"], body))
    return did



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--if-old", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    if args.if_old:
        con0 = common.connect(create=False)
        if con0 is not None:
            try:
                last = float(con0.execute("SELECT v FROM meta WHERE k='last_run'").fetchone()[0])
                if time.time() - last < 86400:
                    return
            except Exception:
                pass
            con0.close()
    con = common.connect()
    files = common.discover()
    have = {r["path"]: r for r in con.execute("SELECT id,path,mtime,size,hash FROM docs")}
    seen = set()
    n_new = n_changed = n_touch = n_same = 0
    for path, source in files:
        p = Path(path)
        try:
            st = p.stat()
        except OSError:
            continue
        seen.add(path)
        old = have.get(path)
        if old and not args.full and old["mtime"] == st.st_mtime and old["size"] == st.st_size:
            n_same += 1
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        h = sha(data)
        if old and not args.full and old["hash"] == h:
            con.execute("UPDATE docs SET mtime=?, size=? WHERE id=?", (st.st_mtime, st.st_size, old["id"]))
            n_touch += 1
            continue
        text = data.decode("utf-8", "replace")
        fm, body = parse(text)
        title = title_of(fm, body, path)
        summary, kind = fallback_summary(fm, body, title)
        rec = dict(path=path, rel=common.rel_of(path), source=source, title=title,
                   date=common.doc_date(fm, p.name, st.st_mtime), mtime=st.st_mtime,
                   size=st.st_size, hash=h, lines=text.count("\n") + 1, summary=summary,
                   summary_kind=kind, questions="", indexed_at=time.time(),
                   aliases=" | ".join(fm["_aliases"]), kind=fm.get("type", ""))
        write_row(con, old["id"] if old else None, rec, text[: common.MAX_BODY_CHARS])
        if old:
            n_changed += 1
        else:
            n_new += 1
    gone = [r for p, r in have.items() if p not in seen]
    for r in gone:
        con.execute("DELETE FROM fts WHERE rowid=?", (r["id"],))
        con.execute("DELETE FROM docs WHERE id=?", (r["id"],))
    con.execute("INSERT OR REPLACE INTO meta (k,v) VALUES ('last_run', ?)", (str(time.time()),))
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    con.close()
    if not args.quiet:
        print("Indexed %d files in %.1fs: %d new, %d changed, %d touched only, %d unchanged, %d removed."
              % (total, time.time() - t0, n_new, n_changed, n_touch, n_same, len(gone)))
        print("DB %s." % common.DB_PATH)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
