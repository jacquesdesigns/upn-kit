---
name: close-out
description: Close out a working session so nothing is lost: writes the wiki page, updates the job's NOW file, adds one line to hot.md, and lists every file saved with its full path. Use when the person says "close out", "save to the wiki", "save learnings", "write the handover", "wrap up", or says yes to the close-out offer at the end of a session. Replaces typing "save to the wiki" every time.
---

# Close-out

One recipe, the same every time, no questions beyond one: which job, if it is not obvious. Paths come from the folder the session ran in; `~/.claude/upn-kit/config.json` has `brain`.

## 1. Find the job and read what is there

The job is the folder of the NOW file handed over at session start, else the job the session worked on. Read its `NOW.md` (and `HANDOVER.md` if it has one) before writing anything.

## 2. Collect what this session saved

List every file written or changed in this session (from your own tool calls; check the folder if unsure). Keep two lists: made, changed. Say where each one is now, including any new file saved into a Dropbox job folder.

## 3. The wiki page

Write or update ONE page for what was learned, in the wiki area where pages of the same kind already live. Look at `wiki/index.md` and the two nearest pages first and copy their shape (frontmatter, headings, link style). Contents: what was done and why, decisions with their reasons, facts verified (with the source), what is still open, links to the job's NOW file. Add one line to the wiki index. Only durable things; what changes (status, sent, live) belongs in the NOW file, not the wiki.

## 4. The job's NOW file

Update, do not rewrite: **done** (what is now true, with date), **open** (what is waiting, on whom), **next** (the one next step), **files** (the made and changed lists with full paths). Keep it under about 60 lines; older detail moves to the wiki page. If the job has no NOW file, create it from the job-start template.

## 5. hot.md

Add one dated line to `wiki/hot.md` (create it if missing): `- YYYY-MM-DD <job>: <one line of what changed>`. Keep the newest 14 lines; move older ones to the bottom under "Older".

## 6. Check before you report

Search what you wrote for em dashes, double dashes and US spellings and fix them. Open each file you wrote and confirm it exists. Do not say it is saved until you have.

## 7. Report

One short list, full paths, nothing else:

```
Made:     <full path>
Changed:  <full path>
Wiki:     <full path>
NOW:      <full path>
Saved to Dropbox (new files only): <full path>
```
