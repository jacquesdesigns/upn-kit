---
name: studio
description: Run a studio job the studio's way, starting with references. Use when the person gives references (Cosmos boards, Awwwards or other websites, images) for any web, brand or design job, asks to collect or understand references, build reference sheets, start a new studio job (/studio new <client> <job>), or build or resume a studio site (/studio build <job dir>). Covers references first, then the brief, then the build path: the designer, the check kit, the separate judge and the fix loop.
---

# Studio

Every job moves in this order: **references, then brief, then design.** References can be gathered before the brief is settled; design waits for both.

- `/studio new <client> <job>` starts a job folder from the template.
- `/studio build <job dir>` runs or resumes a job through its stages (Phase 3).

Paths and tools come from `~/.claude/upn-kit/config.json`: `home` (the Studio folder, normally `~/Studio`), `python` (the kit's Python, with Playwright installed) and `kit_root` (where this plugin lives). Read it first. If `python` is missing, run the setup step in the kit's PROMPT-2 before going on.

## Before anything, read these

1. `<home>/taste/STANCE.md` if it exists: how this person looks at work.
2. `<home>/taste/LESSONS.md` and `<home>/taste/REVERSAL-LOG.md` (newest entries): what went wrong before and what they sent back. Short; read all of it.
3. The job's own `00 brief/INTAKE.md` and `DESIGN-NOTES.md` if the job exists.

Old job folders are evidence of what happened, not templates. Reuse their tools, never their designs.

## Phase 1: References (no brief needed)

Start the job with `/studio new <client> <job>`:
`<python> "<kit_root>/skills/studio/scripts/new_job.py" "<client>" "<job>" --name "<name>"` makes `<home>/projects/<client>/<job>/` with `job.json`, `00 brief/` (`INTAKE.md`, `_BRIEF.md`, `RUBRIC.md`, `PLAN.md`), `DECISIONS.md`, `OPEN.md`, `DESIGN-NOTES.md` and `evidence/`. Add `references/`.

**Record each reference in `00 brief/INTAKE.md`** as the person gives it: the link, its kind, what they like about it in their words, and what not to take. Kinds:
- **look**: type, colour, hierarchy, image treatment, composition, the device (boards, images);
- **feel**: how it scrolls, how long things hold, how it moves and responds (websites);
- **structure**: what is on it and in what order (websites);
- **voice**: how the words sound;
- **not this**: what to avoid.
If they have not said what a reference is for, write your best reading and mark it *(reading, confirm)*. Unanswered brief questions stay marked **open**; never fill them in yourself.

**Capture every reference** (scripts in this skill's `scripts/`, run with the kit's `python`):
- Cosmos board: `cosmos.py BOARD_URL references/<slug>`: every element in board order, images and videos, at its own ratio. Its count must equal the board's own count (it prints both).
- Website, feel: `capture_site.py URL references/<slug> --feel`: screens while scrolling, a scroll recording, frames and timings (page length, pins, transitions, scroll smoothing, libraries).
- Website, structure or look: `capture_site.py URL references/<slug>` (no recording).
- A splash or promo overlay that locks scrolling: name it and pass `--remove '.splash'`. The script never clicks.
- Look at the frames before trusting a capture: an intro gate can fill the whole recording; re-record past it.
- A period site: find captures through the Wayback Machine's CDX search, load them in `if_` mode, and shoot at the period's screen size as well as 1440.
- **Read the code of every website reference.** Screenshots show what a site does; only the code shows how. Use the `web-feature-reverse-engineer` skill if it is installed, or open the page's scripts yourself with headless Playwright (never a browser connector), and write `references/<slug>/HOW-IT-WORKS.md`: the stack, how input becomes motion, every scroll trigger, durations and easings, mobile handling. Mark what is confirmed in code and what is inferred. Check the headline numbers by grepping the saved code before they go into a reading.
- Loose images: copy into `references/<slug>/`. Never crop, resize to fit a grid or filter a reference.
- One line per reference in `references/index.jsonl`: `id`, `kind`, `for` (their words), `not`, `source`, `maker` (who made it, and where the credit was found, or "not found").

**Read each item at full size** before any sheet or reading: a sheet tile is under 300px and reads as a grey rectangle. For each reference write a short note in `references/<slug>/NOTES.md`: what is there, how it is made (render, photograph, print or code; for a site, the stage and how it was built), where the eye goes, the elements worth taking and the job each does for the visitor, and what not to take. Observations and measurements, never adjectives, never "good" or "bad".

**Understand the whole set:**
- `contact_sheet.py references/_sheet-all.jpg references/*`: the whole set on one sheet, sampled evenly, plus one sheet per kind. Look at every sheet yourself before writing a word about it.
- `feel_ranges.py references --kind feel`: what the feel references agree on, as ranges.
- `references/READING.md`: one line per reference saying what you read from it, for the person to correct; then a matrix (type, spacing and scale, colour and lightness, layout, the device, image treatment, motion and pacing, structure) with what the set agrees on as a range and where it splits (a split is named, never averaged away); then **questions for the brief**: what the set implies about purpose and audience, asked, not decided.
- **Read the set against the deliverable.** Write what the set does not carry that the job will need (for a website: a site of the target kind, showing how it was put together). Each gap is a question to the person in the same message as the sheets, never a note buried in READING.
- References you find yourself (Inspo, Mobbin if connected) go in `references/candidates/` and are marked as candidates, never mixed with theirs.

Then stop and show the sheets, the readings and the questions. When they have confirmed the subject and every reference's kind, tick the "confirms" line in `INTAKE.md` with the date and their words, only on their own message.

## Phase 2: Brief

**They talk, you write.** Do not make anyone fill a template. Let them say everything first. Ask at most three questions, and only where the answer would change the design. Then write the brief back in plain words, under 200 words: the one thing the site has to do, for whom, the pages, what they will look at first and what they will do with it, what is fixed, what is open. Mark every guess "(my reading)". They answer yes or correct lines; that is the brief.

Fill `00 brief/_BRIEF.md` from their answers and the client's own words (quote them). Every must-have quotes its source. Build `RUBRIC.md` from the references with the `rubric` skill, never by hand; its top band is what "show the person" means. Unanswered fields stay open.

## Phase 3: The build path

Only when references and brief are both settled. Check every route against the whole set, never one favourite.

**Design first, engineering second.** The first thing the person sees is a whole page, not fold 1 of 16. A `studio-designer` agent (one per route) composes a real draft on 127.0.0.1 from the references, the brief's facts table and the job's ban list, looks at its own screenshots three or four times, and hands over the URL. The person scrolls and sends it back one structural variable at a time until the direction holds; they tick the route line in `DECISIONS.md`. Every change after the first pick is briefed in the designer's EDIT mode, naming what may change. Only then do `studio-builder` agents harden the draft in place (tokens only, components, the kit at every width) and the `studio-judge` agent judge it. There is no plan stage: the approved draft is the plan.

**Two send-backs on the same point: change the method, not the draft.** When the person sends two drafts back for the same reason, dispatch no third designer. Diagnose what the drafts share (what the references miss, the medium, where the structure came from), bring the diagnosis and one probe that tests it.

**Generated comps are sketches, never references.** Nothing a designer composes cites a comp.

**Briefs name, they do not offer.** Anything a designer brief mentions gets built. If it is a question, it is the person's, asked before the brief.

**The stages and their gates** (the job's `job.json` records `stage`; move on only when the gate is met from the files, never from a claim):

| stage | the work | the gate |
|---|---|---|
| intake | Phase 1 | subject in one sentence; every reference with its kind, confirmed; the confirms line ticked |
| brief | Phase 2 | every must-have quotes a source; `RUBRIC.md` with bands; pages and flows in `job.json` |
| direction | a designer per route, whole page on 127.0.0.1 | the person ticks a route in `DECISIONS.md` |
| system | a builder lifts tokens, grid, scales and components from the approved draft; the system page | kit `--only system` green |
| build | builders harden the draft in place; then the full kit | newest full kit run: 0 fail, 0 error, every page and flow measured |
| critique | the `studio-judge` agent, given only the job folder | the verdict judged that run; no gate failed; the rubric's top band |
| handback | deploy and `--live` run if there is a `live_url`; write a short handback note | the note exists, built after the newest run and verdict |

**The system page shows the website, in this order and nothing else:** 1. the basics, visually (mark and how it is used, colours, type, the repeating device); 2. every component the pages use, desktop and phone side by side, the menu open and closed; 3. the full pages at both sizes; 4. the detail as reference (exact colours, sizes, spacing, tokens); 5. the kit's results, last. It is one builder pass; past that, stop and show the person.

**The first scroll is the clock.** From the brief being settled, the person sees a whole page they can scroll within one sitting (about 40 minutes of designer time). If a designer has not handed over a URL in that window, stop it and serve what exists. A run that reaches a judge before the person has scrolled anything is wrong even if every gate is green.

**Test the way a hand moves.** Any wheel, scroll or swipe control is checked with the input a real device sends (a trackpad stream, a mouse wheel, a fling, a swipe), then the screen after each gesture is looked at, not a counter. The kit has these ready: `checks/inputs.py`, `checks/gesture_check.py`, `checks/audio_check.py`, driven by `job.json` `page_check`.

**The fast loop: every handback and every send-back gets one minute, not a hand-written probe.** `<python> "<kit_root>/skills/studio-check/checks/page_check.py" --job J --base URL [--pages ...] [--engines chromium,webkit] [--sheet]`: direct load of every page at two sizes, no responses over 400, no page errors, the first press of each flow visible and unique, banned words and dashes in the visible text, a screenshot after opening, and a contact sheet. Then LOOK at the sheet. The full kit is still the gate.

**Variants rule.** When a page is built as variants, each is a different device and structure, judged side by side on one sheet before the person sees them; surface (material, colour, grain) is a separate later pass. Copying the home and re-skinning is the failure this rule exists for.

**The conductor plans, agents build.** This conversation plans each step, writes each brief, dispatches, and verifies every report against the files (the kit's `report.json`, the shots and sheets) before the next step. The designer is `studio-designer`, builders are `studio-builder` (one fresh context per step), the critic is `studio-judge`, never this conversation. Agents get the job's files and a short brief. An agent's report is a claim until checked. Every agent report carries a **Skills:** line.

**Size limits.** One builder builds one page and stops at 12 logged steps; a fix builder takes five fixes. Agents judging a build read the kit's contact sheets, ten pictures at most. Agents reading references do the opposite: the full-size file, one item at a time. No sandbox copies of a job.

**The loop.** Builder, then the full kit, then the judge (`Judge the build at <job dir>.` and nothing else), then the ranked fixes to a FRESH `studio-builder` carrying only that list and the job folder, then the full kit and the judge again. When a defect does not shrink in two passes, stop: write it in `OPEN.md` under "Defects that did not shrink" with both passes' evidence and say so. Never advance past a red gate.

**The run log.** `evidence/RUN-LOG.md`, append only, one line per step: `- <YYYY-MM-DD HH:MM> | <stage> | <who> | <step> | <result> | <evidence>`. The result comes from the files, never an opinion.

**Resume, never restart.** After a break: read the whole run log, `OPEN.md`, the newest kit report and verdict; carry on from the last step with evidence.

## Finding the maker

For references that stand out, trace who made them: the brand's about page, the footer or "site by" credit, the studio's portfolio, Fonts In Use. Record it in `maker`. Behance and gallery sites rarely credit anyone.

## Using references properly

References are a private working library: keep the source on every item, never publish them, and never feed them to image models as style inputs for client work.

## Setup (once, done by PROMPT-2)

The kit's Python needs `playwright` and `pillow`, and `python -m playwright install chromium`. `ffmpeg` must be on PATH for recording frames.
