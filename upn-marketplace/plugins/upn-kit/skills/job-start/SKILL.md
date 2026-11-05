---
name: job-start
description: Start a UPN job from a job number: makes the job folder, the NOW file and the project map row, and records the Dropbox paths so nobody types them again. Use when the person gives a job number ("job 10360", "new job 10343 for ..."), says "start a job", "set up the folder for", or "where is job 10335".
---

# Job start

The person gives a job number. You do the rest, and ask only for what you cannot find.

## Ask for these (in one message, only the ones missing)

- job number (e.g. 10360), client, short project name;
- the job's Dropbox folder (the person can paste it; for a number seen before it is already recorded);
- the stage, if they say one, and the due date if there is one.

Look first: search the brain (`brain-search`) for the number, and read `<brain>/upn/job-paths.json` if it exists. Never guess a Dropbox path; if the storage index lists the number, offer that path and let the person confirm.

## Then run the script (it does the deterministic part)

```
python "<kit_root>/skills/job-start/scripts/jobstart.py" --brain "<brain>" --number 10360 --client "<client>" --project "<project>" --dropbox "<Dropbox path>" --stage "<stage or blank>" --due "<date or blank>"
```

It makes `upn/projects/<client>--<project>/` (copying `upn/projects/_template` when that exists, else an empty folder), writes the job's `NOW.md` with the Dropbox path, adds one row to `upn/PROJECT_MAP.md` matching that table's own columns, and records the number against the folder and the Dropbox path in `upn/job-paths.json`. It refuses to overwrite anything that exists. It never creates or changes anything in Dropbox.

## After it runs

1. Read back what it printed: the folder, the NOW file, the map row, the recorded path.
2. Tell the person where the job's files are recorded (the NOW file and the map row). Where drafts live is their call; do not impose a folder structure. In Dropbox Claude can save a new file (a new name) but never overwrite, edit, move, rename or delete; the NOW file's files list says what was saved where.
3. If the person asked "where is job N", answer from `job-paths.json` and the NOW file; do not run the script.

Folder names are `<client>--<project>`, lower case, hyphens inside each part. Quote the person's wording in NOW.md; never invent a client name or a date.
