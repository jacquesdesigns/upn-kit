---
name: brain-search
description: Search the brain (memory, wiki, every NOW file and handover, CLAUDE.md files, the nightly atoms and the Dropbox storage index) before answering about the past. Use when the person asks "did we", "what did we decide", "where is the X job", "what is the status of", "last time", or names a job, client or person and the answer may already be written down.
---

# Brain search

One ranked search over everything written down, in about a tenth of a second, no model call.

```
python "<kit_root>/hooks/brainsearch/search.py" "words to look for" -n 8
```

(`kit_root` is in `~/.claude/upn-kit/config.json`. Use `py` if `python` is not found.)

What it covers: the memory folder, `wiki/`, every `NOW.md` and `HANDOVER*.md`, every `CLAUDE.md`, the root `MEMORY.md`, the nightly atoms (one-line commands, errors, fixes and decisions from past conversations) and the storage index (job folder names, dates and file counts in Dropbox, never contents). It never reads `20. RAW`, `.raw`, `_archive` or anything in Dropbox itself.

How to use it:
1. Search before answering anything about the past or about where something is. A hit is a pointer: open the file it names before you rely on it.
2. A NOW file or a state file beats the wiki for anything that changes (status, what is sent, what is live). The wiki beats memory for anything stable. If two disagree, say so.
3. For "where is the X job", search the job name or number; the storage index answers with the Dropbox path. Read-only: you only report the path.
4. No result is an answer too: say nothing was found, then ask.

The index refreshes itself at the start of each session when it is more than a day old. To rebuild by hand: `python "<kit_root>/hooks/brainsearch/index.py"` (add `--full` to rebuild every row). Nicknames with no page of their own go in `hooks/brainsearch/aliases.json`; for anything with a wiki page, put the nickname in that page's `aliases:` frontmatter instead.
