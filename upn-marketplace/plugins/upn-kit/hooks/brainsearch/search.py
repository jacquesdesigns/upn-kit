#!/usr/bin/env python3
"""Ranked search over the brain-search index.

  search.py "job 10350 deadline"     top 5
  search.py "who is Dair" -n 10      more
  search.py "tender" --json          machine-readable

Ranking: SQLite FTS5 bm25 (title, frontmatter aliases and filename weigh most), then three
adjustments made here:
  1. A page whose title or alias IS the query (or the subject of "who is X") goes first.
  2. A page whose alias, or an entity page whose title, appears inside a longer query is boosted
     ("the traffic lead's notes" finds the page with that alias). "who is X" boosts entity pages further.
  3. Catalogue pages that mention everything (MEMORY.md, wiki/index.md, hot.md and
     every wiki folder's _index.md) are pushed down so they do not crowd out the real note.
  4. Recency: a document's bm25 score is multiplied by a factor that decays gently with age
     (full weight today, half the boost gone at 180 days, never below RECENCY_FLOOR). Memory,
     CLAUDE.md and the business briefs are rules, so they get no decay: a rule is not truer
     because it is newer. Each hit prints its date.
"""
import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

# column order in fts: title, aliases, path, summary, questions, body
WEIGHTS = "8.0, 8.0, 5.0, 4.0, 4.0, 1.0"
FETCH = 40
STOP = {"the", "a", "an", "of", "is", "was", "are", "who", "whos", "what", "s", "to", "in", "on", "for",
        "and", "did", "do", "does", "about", "where", "when", "how", "my", "our", "it", "that", "this", "with",
        "we", "i", "me", "us", "you", "they", "have", "has", "had", "been", "be", "were", "will", "would",
        "should", "could", "can", "at", "by", "from", "up", "out", "any", "so", "if", "last", "time", "yesterday",
        "earlier", "before", "already", "again", "ever", "got", "get", "there", "then", "than", "but", "or", "not"}
HALF_LIFE_DAYS = 180.0
RECENCY_FLOOR = 0.7      # an ancient document keeps 70% of its bm25 score; today's keeps 100%
DOWNRANK = {"memory/MEMORY.md", "MEMORY.md", "wiki/index.md", "wiki/hot.md", "hot.md"}
DOWNRANK_FACTOR = 0.2
EXACT = -1000.0
ALIAS_IN_QUERY = -40.0
TITLE_IN_QUERY = -15.0
WHO_ENTITY_IN_QUERY = -60.0
WHO_ENTITY_BASE = -10.0


def recency_factor(date_s, source, today=None):
    """1.0 for a rule (no decay) or today; falls towards RECENCY_FLOOR with a 180 day half-life."""
    if source in common.NO_DECAY_SOURCES or not date_s:
        return 1.0
    try:
        age = ((today or _date.today()) - _date.fromisoformat(date_s)).days
    except ValueError:
        return 1.0
    age = max(age, 0)
    return RECENCY_FLOOR + (1.0 - RECENCY_FLOOR) * 0.5 ** (age / HALF_LIFE_DAYS)


def norm_words(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"\w+", s.lower(), re.U)


def words(q):
    return re.findall(r"\w+", q, re.U)


def contains(hay, needle):
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def strip_stop(ws):
    out = [w for w in ws if w not in STOP]
    return out or ws


def who_subject(nw):
    """['who','is','mazvita'] -> ['mazvita']; None if not a who-is query."""
    if len(nw) >= 3 and nw[0] == "who" and nw[1] in ("is", "was", "are", "s"):
        return nw[2:]
    if len(nw) >= 2 and nw[0] == "whos":
        return nw[1:]
    return None


def load_aliases():
    try:
        d = json.loads(common.ALIASES_PATH.read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return {k.lower(): v for k, v in d.items() if not k.startswith("_") and isinstance(v, list)}


def phrase(s):
    w = words(s)
    return '"%s"' % " ".join(w) if w else ""


def build_queries(q, subject=None):
    """Return (strict, loose, expansions). strict = every content word; loose = any word."""
    ws = subject if subject else strip_stop(words(q))
    if not ws:
        return "", "", []
    low = " ".join(norm_words(q))
    extra = []
    for k, vals in load_aliases().items():
        if re.search(r"\b%s\b" % re.escape(" ".join(norm_words(k))), low):
            extra.extend(vals)
    alias_part = [phrase(v) for v in extra if phrase(v)]
    strict = " AND ".join('"%s"' % w for w in ws)
    loose = " OR ".join('"%s"' % w for w in ws)
    if alias_part:
        strict = "(%s) OR %s" % (strict, " OR ".join(alias_part))
        loose = "%s OR %s" % (loose, " OR ".join(alias_part))
    return strict, loose, extra


SELECT = (
    "SELECT d.id, d.rel, d.title, d.summary, d.summary_kind, d.source, d.kind, d.aliases, d.date, "
    "snippet(fts, 5, '[', ']', ' ... ', 22) AS snip, "
    "snippet(fts, 4, '[', ']', ' ... ', 14) AS qsnip, "
    "bm25(fts, %s) AS score FROM fts JOIN docs d ON d.id = fts.rowid " % WEIGHTS
)


def run(con, match, limit):
    return {r["id"]: r for r in con.execute(SELECT + "WHERE fts MATCH ? ORDER BY score LIMIT ?", (match, limit))}


def named_docs(con, nw, subject):
    """Pages whose title or alias is, or sits inside, the query. Returns {id: (bonus, why)}."""
    who = subject is not None
    full = tuple(nw)
    exact_keys = {full, tuple(strip_stop(nw))}
    if subject:
        exact_keys.add(tuple(subject))
    hits = {}
    for r in con.execute("SELECT id, rel, title, aliases, kind, source FROM docs "
                         "WHERE source='wiki' OR aliases != ''"):
        entity = r["rel"].startswith("wiki/entities/") or r["kind"] == "entity"
        phrases = []
        if r["source"] == "wiki":
            phrases.append((tuple(norm_words(r["title"])), False))
        for a in filter(None, (x.strip() for x in r["aliases"].split("|"))):
            phrases.append((tuple(norm_words(a)), True))
        best = 0.0
        why = ""
        for ph, is_alias in phrases:
            if not ph or sum(len(w) for w in ph) < 3 or all(w in STOP for w in ph):
                continue
            if ph in exact_keys:
                b = EXACT - (1 if entity else 0)
            elif contains(nw, ph):
                if is_alias:
                    b = WHO_ENTITY_IN_QUERY if (who and entity) else ALIAS_IN_QUERY
                elif entity:
                    b = WHO_ENTITY_IN_QUERY if who else TITLE_IN_QUERY
                else:
                    continue
            else:
                continue
            if b < best:
                best, why = b, " ".join(ph)
        if best:
            hits[r["id"]] = (best, why)
    return hits


def search(q, n=5):
    con = common.connect(create=False)
    if con is None:
        return None, [], [], {}
    nw = norm_words(q)
    subject = who_subject(nw)
    strict, loose, extra = build_queries(q, subject)
    if not strict:
        return con, [], extra, {}
    cands = run(con, strict, FETCH)
    if len(cands) < FETCH:
        for i, r in run(con, loose, FETCH).items():
            cands.setdefault(i, r)
    named = named_docs(con, nw, subject)

    # named pages that the text query did not return: fetch them directly
    missing = [i for i in named if i not in cands]
    for i in missing:
        row = con.execute(SELECT + "WHERE fts MATCH ? AND d.id = ?", (loose, i)).fetchone()
        if row is None:
            row = con.execute(
                "SELECT d.id, d.rel, d.title, d.summary, d.summary_kind, d.source, d.kind, d.aliases, d.date, "
                "d.summary AS snip, '' AS qsnip, 0.0 AS score FROM docs d WHERE d.id = ?", (i,)).fetchone()
        if row is not None:
            cands[i] = row

    scored = []
    for i, r in cands.items():
        s = r["score"] * recency_factor(r["date"], r["source"])
        entity = r["rel"].startswith("wiki/entities/") or r["kind"] == "entity"
        if subject and entity:
            s += WHO_ENTITY_BASE
        if i in named:
            s += named[i][0]
        elif r["rel"] in DOWNRANK or r["rel"].endswith("/_index.md"):
            s *= DOWNRANK_FACTOR
        scored.append((s, r))
    scored.sort(key=lambda x: x[0])
    return con, [r for _, r in scored[:n]], extra, {i: v[1] for i, v in named.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    con, rows, extra, named = search(a.query, a.n)
    if con is None:
        sys.exit("No index yet. Run: python %s" % (Path(__file__).resolve().parent / "index.py"))
    meta = dict(con.execute("SELECT k, v FROM meta").fetchall())
    age_h = (time.time() - float(meta.get("last_run", 0))) / 3600
    if a.json:
        print(json.dumps([{k: r[k] for k in ("rel", "date", "title", "snip", "summary", "summary_kind", "score")} for r in rows],
                         indent=1, ensure_ascii=False))
        return
    if extra:
        print("(also searched for: %s, from aliases.json)" % ", ".join(extra))
    if not rows:
        print("No matches.")
    for i, r in enumerate(rows, 1):
        snip = re.sub(r"\s+", " ", r["snip"] or "").strip()
        if "[" not in snip and "[" in (r["qsnip"] or ""):
            snip = "(likely question) " + re.sub(r"\s+", " ", r["qsnip"]).strip()
        why = "  (matches the page name or alias \"%s\")" % named[r["id"]] if r["id"] in named else ""
        print("%d. %s  [%s]%s" % (i, r["rel"], r["date"], why))
        print("   %s" % r["title"])
        print("   %s" % snip.strip(". "))
        tag = {"haiku": "", "frontmatter": " [from the note's own description]"}.get(
            r["summary_kind"], " [first paragraph, not a model summary]")
        print("   summary: %s%s" % (r["summary"], tag))
    if age_h > 24:
        print("\nIndex is %.0f hours old. Refresh: python %s" % (age_h, Path(__file__).resolve().parent / "index.py"))
    if meta.get("summary_note"):
        print("\nNote: " + meta["summary_note"])


if __name__ == "__main__":
    main()
