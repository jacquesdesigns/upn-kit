"""Brief lint (6 Oct 2026): "briefs name, they do not offer". Anything a designer brief mentions gets built.
Flags offer words and hedges in the brief files given, and (with --job) job.json copy.banned words and dashes.
It prints warnings with line numbers; a flagged line is either rewritten to name what is wanted, or moved out to a question
for the owner BEFORE the brief goes out. Exit 1 with --strict.
Usage: brief_lint.py [--job JOB_DIR] [--strict] FILE.md ...
"""
import re, sys, json, os
args = sys.argv[1:]; strict = "--strict" in args; job = None
if "--job" in args: job = args[args.index("--job") + 1]
files = [x for i, x in enumerate(args) if not x.startswith("--") and (i == 0 or args[i - 1] != "--job")]
OFFER = re.compile(r"\b(may|might|optionally|optional|could also|could|consider|perhaps|if (?:the )?(?:rendering|time|possible|it fits|there is room|you like|useful)|feel free|or similar|something like|maybe|ideally|nice to have|up to you|your choice)\b", re.I)
banned = []
if job: banned = [w.lower() for w in (json.load(open(os.path.join(job, "job.json"))).get("copy", {}) or {}).get("banned", [])]
DASH = re.compile("[\u2014\u2013]| -- ")
n = 0
SLUG = re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)*-(?:19|20)\d\d\b|`[^`]*`")      # reference card names and code spans may carry banned words
QUOTED = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d')                             # the owner's own words are quoted, not offered
for f in files:
    for i, line in enumerate(open(f).read().split("\n"), 1):
        body = QUOTED.sub(" ", line); copy = SLUG.sub(" ", body)
        for m in OFFER.finditer(body): print(f"{f}:{i}: offer word '{m.group(0)}' | {line.strip()[:120]}"); n += 1
        if DASH.search(line): print(f"{f}:{i}: dash | {line.strip()[:120]}"); n += 1
        for w in banned:
            if re.search(r"\b" + re.escape(w) + r"\b", copy, re.I): print(f"{f}:{i}: banned word '{w}' | {line.strip()[:120]}"); n += 1
print(f"brief_lint: {n} flag(s) in {len(files)} file(s)")
sys.exit(1 if (n and strict) else 0)
