---
name: studio-check
description: Run the studio check kit on a studio job's built site and read its report. Use while building any website (a quick run after each change), before calling a build done (the full run is the gate), before the judge or a handback, against the live URL after a deploy, or when the person asks "does it work", "run the checks", "is it broken anywhere", "check it at every width", "check it in Safari". Writes evidence/checks/<run>/report.json, report.md, shots, films and sheets in the job folder.
---

# Studio check

The shared check kit lives in this skill's `checks/` folder (`<kit_root>/skills/studio-check/checks/`; `kit_root` and `python` are in `~/.claude/upn-kit/config.json`). Its `README.md` lists every
check with what it protects, its limit and the failure that taught it. Read that before arguing with a
result.

**A builder's "done" is a claim until the full run is green.** Green means 0 fail and 0 error. A skip
is not a pass: read every skip's reason, and say it out loud in the handback when it hides something
(an engine that did not launch, a page that does not scroll, a timing run on a busy machine).

## Run it

Run it with the kit's Python:

```
<python> "<kit_root>/skills/studio-check/checks/studio_check.py" --job "<job folder>"
```

The job folder holds `job.json` (the template in the studio skill shows its shape).
The kit serves `serve.root` itself on 127.0.0.1; never start your own server for it.

- **While building: `--quick`.** Chromium only, at 390, 1280 and 1440, no films. Run it after each
  change, one change per step. Add `--only layout,controls` or `--pages home` to narrow it. A quick run
  is never the gate (the report says `"mode": "quick"`).
- **Before saying done: the full run**, no flags. Seventeen widths plus the short heights and a phone
  on its side, every flow in every engine, the films, the frame times, the engines.
- **After a deploy: `--live`**, the whole kit against job.json `live_url`. Fixes that only held on
  127.0.0.1 are found here.
- `--list` prints every check with its limit.

It exits 1 on any fail or error. It takes a few minutes a page for the full run; run it in the
background and keep working on something that does not touch the build.

## Read the report

Open `<job>/evidence/checks/latest` for the run name, then `report.md` in that folder.

1. **Errors first.** The kit could not measure: a page that did not load, a check that crashed. Fix
   the cause or report it; never read an error as nothing wrong.
2. **Failures.** Each row says what was measured against which limit, where (page, viewport, engine),
   and which shot, film or sheet shows it. Open the evidence and look at it before changing anything:
   the tool output is not the finding, the picture is. Fix the defect in the build, one change per
   step, then re-run the group that failed with `--only`.
3. **Skips.** Each carries its reason. A missing engine, a job.json with no flows, no PLAN.md: each is
   something the run did not prove.
4. **Look at the sheets** (`sheets/<page>__widths.png`, `__folds.png`, the film strips) even when
   everything is green. Checks passing only means the page is ready to be looked at.

`report.json` is what the judge and the handback page read; never edit it by hand.

## Rules

- Never change a limit to make a run pass. When a check is wrong about its purpose, re-express what it
  protects, say so, and change the check in the kit (for every job), not the job's limits.
- Never weaken a check inside a job by hiding elements from it. The only opt-outs are `data-clip-ok`
  and `data-overlap-ok` on a deliberate window (a marquee, a crop), and each one needs its reason in
  the job's `DECISIONS.md`.
- If a defect does not shrink in two passes, stop and write it into the job's `OPEN.md` for the person.
- Headless only, through the kit's Python; never a browser connector.
