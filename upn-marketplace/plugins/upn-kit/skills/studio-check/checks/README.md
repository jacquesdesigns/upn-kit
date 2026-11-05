# The studio check kit

One kit for every CDS job. A job supplies only its `job.json`; the kit serves the build, loads every
page the way a person would, measures, and writes a report. Every check below names what it protects,
its limit, and the failure that taught it. A check that cannot measure says so: `skip` and `error`
always carry the reason, and neither is ever a pass.

## Run it

From the repo root, with the studio venv (Python 3.14, Playwright, Pillow; nothing else):

```
<python> "<kit_root>/skills/studio-check/checks/studio_check.py" --job "<your Studio folder>/projects/<client>/<job>"
```

| flag | what it does |
|---|---|
| `--quick` | Chromium only, at 390, 1280 and 1440 wide, no films. For fast loops while building. Not a gate. |
| `--only layout,controls` | only these groups (the report's `mode` becomes `quick`) |
| `--pages home,work` | only these job.json pages |
| `--url URL` | check an address instead of serving `serve.root` |
| `--live` | check job.json `live_url` (the Live row of the build system: the whole kit against the deployed site) |
| `--list` | print every check, its limit and what taught it |

Without `--url` or `--live` it serves `serve.root` on a free port on 127.0.0.1 (127.0.0.1, because
font kits such as Adobe Fonts are keyed to that host). The full run is the gate. It exits 1 on any
fail or error, 0 otherwise.

## What it writes

`<job>/evidence/checks/<YYYYMMDD-HHMMSS>/` and `<job>/evidence/checks/latest` (the newest run's name).

- `report.json` , the interface other tools read: `job`, `run`, `target`, `live`, `mode` (`quick`
  when `--quick` or `--only` was used, else `full`), `groups` run, `engines` attempted, `summary`
  (pass, fail, skip, error) and `results`, one row per check per page per viewport per engine, each
  with `measured`, `limit`, `protects`, `taught_by` and `evidence` (paths inside the run folder).
  Flows are rows in group `controls` with `check` set to `flow: <flow name>`.
- `report.md` , the same for people: errors, failures, skips with reasons, then passes by check.
- `shots/<page>__<w>x<h>__<engine>.png` (full page) and `shots/<page>__<w>x<h>__<engine>__fold<N>.png`
  (each viewport-height screen, reached by scrolling and given time to settle, as a person sees it).
  Also `flow__…` and `menu__…` shots of what each press opened.
- `films/<page>__<w>x<h>__chromium.mp4` , each page scrolled and filmed at an exact 30fps.
- `sheets/<page>__widths.png` (the first screen at every width on one sheet), `sheets/<page>__folds.png`
  (every fold at 390 and 1440) and `sheets/<page>__<w>x<h>__<engine>__strip.png` (eight moments of each film, named after its film).

## job.json

The shape is fixed in `the studio build notes` ("Shared interfaces"). Anything missing falls back to
`limits.json` `defaults`; a job's `limits` object replaces any key of `limits.json` `limits` or
`lists`. Optional keys the kit also reads, all with defaults:

- `grid.margin_var` , the outer margin token (the gutter when absent). `grid.columns` may be a number,
  a token name (`"--cols"`), or breakpoints `{"0": 4, "768": 8, "1100": 12}`.
- `copy.allow_prices`, `copy.allow_dates` (false), `copy.mockup_dirs` (`["mockups"]`),
  `copy.banned_images` (file names whose pixels carry facts the page cannot stand behind).
- `limits.section_selector` , what counts as a fold for the spacing group (default: the children of
  `<main>`, descending through a single wrapper, plus the body's header and footer).
- `limits.sizes` , replace any of the viewport lists.
- `flows[].steps` , `{"tap": sel}` (a real touchscreen tap on a touch viewport, a mouse click
  otherwise) or `{"click": sel}`, each hit-tested first, with `"navigates": true` when the press
  loads a new page; `{"expect_visible": sel, "expect_min_height": px, "expect_min_width": px}` (on
  screen AND on top at its centre); `{"expect_hidden": sel}`; `{"expect_url": "part"}`;
  `{"expect_text": "words", "in": sel}`; `{"scroll_to": px | sel | "bottom"}`;
  `{"type": "text", "into": sel}`; `{"press": "Escape"}`; `{"wait": ms}`; `{"back": true}`;
  `{"goto": "page name"}`. A flow may name its starting `page`; otherwise it starts on the first.
- Opt-outs in the markup: `data-clip-ok` and `data-overlap-ok` on a deliberate window (a marquee, a
  crop); anything matching `lists.clip_ok` is treated the same.

`00 brief/PLAN.md` (the composition plan) is read by the hierarchy group: a heading naming the page
(its job.json name), then per fold a heading or line with "Fold N" (add a width such as 390 to scope a
row to that width; without one it is read at 1440) and a line `Dominant: <words or a `selector`>`;
or a table with a Fold column and a Dominant column.

## How it measures (the shared definitions)

Every group uses one page library (`common.py`, `LIB_JS`), so no two groups disagree about a page:
visible means displayed, not hidden, over 2px, and effectively over 5% opaque through its ancestors;
a text leaf is an element with its own words; glyphs are measured by Range rects over text nodes,
clipped by every clipping ancestor starting at the element itself; fixed and sticky chrome is left
out of text overlap and tested instead by the controls group. The page's own scrolling element is
found and used, so a site whose body scrolls is still walked. Timing results wait for a quiet
machine and skip, never pass or fail, when it stays busy.

## The checks

### truth

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `no-dashes` | the studio's punctuation: no em dash, no spaced en dash, no double hyphen | 0 hits | v1 BUILD-LOG, 27 Sep: the copy check failed the first draft on 15 counts |
| `no-ai-mention` | nothing a visitor sees names AI, a model or a tool | 0 hits | the studio's copy rule (switch off per job in job.json lists.ai_mentions) |
| `british-spelling` | British English everywhere | 0 US spellings | v1 BUILD-LOG, 27 Sep: the copy check failed the first draft on 15 counts |
| `no-hype` | plain words, never press-release copy | 0 hype words | the root voice rules: no hype, no empty intensifiers |
| `banned-words` | the job's own words to avoid stay out | 0 hits from job.json copy.banned | v1 copy check, 27 Sep: "loader", "ground", "component" in visitor copy |
| `no-price` | no price is stated unless the job allows it | 0 prices (copy.allow_prices false) | v1 PLAN.md: no prices anywhere |
| `no-date` | no day-level date is invented or stated unless the job allows it | 0 dates (copy.allow_dates false) | v1 BUILD-LOG, 28 Sep: an earlier job mockups printing "Sat 9 July 2027", a Friday |
| `unknowns-marked` | what is not known yet says so in the job's words, never a placeholder | 0 placeholders; unknowns read "to confirm" | the studio build notes: 15 of 45 reversals were invented facts |
| `no-mockup-imagery` | no picture carries a fact the page cannot stand behind | 0 pictures from a mockups folder or the banned list | an earlier job site test.py: poster mockups printing "12-14 JUL 2025" and "ARTIST NAME" |

### layout

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `no-sideways-pan` | the page never moves sideways under a thumb or a trackpad | scrollWidth <= innerWidth and a sideways scroll moves 0px | an earlier job site test.py: html overflow-x clip hid a page 536px wide at 390 |
| `nothing-painted-past` | nothing is drawn outside the screen, even where overflow is clipped | 0 elements past the viewport edge | an earlier job site test.py: the pan test passed while the layout was 536px wide |
| `text-overlap` | two things that should both be readable are both readable | 0 glyph overlaps (Range rects, over 12px2) | the studio build notes: 955 green an earlier job gates, overlaps at 960, 1100, 1680 and 2560 |
| `text-clipped` | no word is cut off by a box that hides its overflow | 0 clipped text runs | the studio build notes: "0 overflows" reported on a page with overlapping text |

### grid

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `on-grid` | every block sits on the job's columns, so the page reads as one designed grid | 0 blocks off a column or gutter edge by more than 2px | new with the build system, 29 Sep: nothing measured the grid before |

### spacing

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `fold-padding` | every fold breathes by the same scale, so the rhythm reads as designed | 0 paddings off the scale (within 1px) | an earlier job spacing.py: its negative control, 60px fold padding, a 19px inset, a heading 5px off its paragraph |
| `one-gutter` | one side margin per width, the same on both sides | one gutter per width, equal left and right, on the gutter token or the scale | an earlier job spacing.py: its negative control, 60px fold padding, a 19px inset, a heading 5px off its paragraph |
| `rhythm` | heading to body and body to action gaps come from the scale | 0 gaps off the scale (within 1px) | an earlier job spacing.py: its negative control, 60px fold padding, a 19px inset, a heading 5px off its paragraph |
| `no-orphan` | nothing floats away from what it belongs to | no gap between neighbours larger than the largest step | an earlier job spacing.py: its negative control, 60px fold padding, a 19px inset, a heading 5px off its paragraph |
| `start-axis` | a fold's content starts on one line, so the eye has one edge to follow | stacked blocks start within 2px of one axis | an earlier job spacing.py: its negative control, 60px fold padding, a 19px inset, a heading 5px off its paragraph |

### hierarchy

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `sizes-per-fold` | a screen has a few clear steps of type, not a crowd of competing middle sizes | at most 4 distinct sizes in any fold | the studio build notes: the portfolio mockups read as "clustered" (27 Sep) |
| `display-to-body` | the first screen has one thing louder than everything else | largest text at least 3x the body size in the first fold | the studio build notes: the portfolio mockups read as "clustered" (27 Sep) |
| `plan-dominant` | the build shows what the composition plan said each fold would lead with | the largest text in the fold is the planned dominant thing | the build system, 29 Sep: the judge checks the build against the plan |

### type_colour

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `fonts-render` | the job's typeface is what people see, never a fallback that happens to look close | every declared family the page uses is loaded and measures unlike the fallback | v1 PLAN.md: the Adobe Fonts kit only loads on 127.0.0.1 or localhost |
| `contrast` | every word can be read against what is actually behind it | WCAG AA: 4.5:1, 3.0:1 at 24px and over | v1 BUILD-LOG, 28 Sep: cream on paper at 1.1:1, grey on stone at 4.2:1 |

### controls

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `hit-testable` | every control is on top where it is drawn, so a press lands on it | 0 covered controls (elementFromPoint at the centre, scrolled to mid-screen) | the studio build notes: 955 an earlier job gates green while the phone menu never opened |
| `target-size` | a thumb hits the control and not its neighbour | at least 44px at 390 (height only for a link in a list or nav; a link in a sentence is exempt) | an earlier job site test.py: the 44px hit test at 390 |
| `flow: <flow name>` | what the job says a person can do, they can do: a real press, and what it opened is on screen | every step's expected result holds | the studio build notes: the an earlier job phone menu never opened while its gate was green |
| `flows-listed` | the job names what a person must be able to do, so the kit can press it | job.json lists at least one flow | the build system, 29 Sep: a flow nobody lists is a flow nobody presses |
| `menu-opens-and-closes` | a menu or disclosure opened mid-page shows its panel, closes, and gives the page back | opens (panel on screen), closes, scroll within 4px of where it was, page still scrolls | an earlier job menu.py: open it mid-page, not just at the top |

### motion

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `film` | the scroll can be judged as it moves, at an exact cadence that compares with the references | a film at an exact 30fps from the compositor, and its frame strip | v1 BUILD-LOG, 27 Sep: record_video_dir smeared, so films come off the compositor |
| `frame-times` | the scroll stays smooth on a slower machine than ours | under 1.0% of frames over 20ms and none over 50ms at 4x CPU throttle | the studio build notes: the 133ms frame |
| `pin-start` | a pinned section engages where it sits, so it never jumps | every pin's start within 2px of its spacer, at rest and after a scroll through | the studio build notes: "clean film" claimed while three of four pins fired early |
| `reduced-motion` | a person who asks for less motion still gets every piece of information, as a still | 0 text blocks the default shows but reduced motion hides | v1 PLAN.md: reduced motion shows every piece of information as a still |
| `without-gsap` | if the animation library fails to arrive, the page still says everything | 0 text blocks lost with GSAP blocked | an earlier job deck test.py: with GSAP blocked every section must still show its text |

### engines

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `wheel-steps` | a trackpad scroll reaches the whole page in every engine | reaches the foot; never more than 2 backward steps in a row (24px every 16ms) | the studio build notes: the WebKit smooth-scroll trap on an older MacBook in Safari |
| `touch-scroll` | a finger drag moves the page and reaches the foot | the first drag moves the page by at least a quarter of the drag; drags reach the foot; no backward run over 2 | the build system, 29 Sep: nothing had dragged a finger through a page before |
| `address-bar-resize` | when a phone's address bar hides or shows, full-height sections and pins stay consistent | full-height sections all track or all hold; pins within 2px; no sideways pan | an earlier job's iOS full-bleed rules: 100dvh and the plate that blued the live grid |

### system

| check | what it protects | limit (default) | what taught it |
|---|---|---|---|
| `components-identical` | components are copied from the system, never redrawn | 0 components that differ from their source | the studio build notes: drifted starred components (an earlier job) |
| `tokens-only` | every colour, face, curve and duration comes from the tokens, so the system holds | 0 raw values in the site's own CSS, JS and inline styles | an earlier job site test.py: the token gate over the site's own css and js |

## Where each group looks

| group | engine | viewports |
|---|---|---|
| truth | Chromium | 1440x900, the rendered page |
| layout, grid, spacing, hierarchy, type_colour | Chromium, one shared sweep | 320, 360, 390, 430, 768, 960, 1024, 1100, 1180, 1280, 1366, 1440, 1536, 1680, 1920, 2560, 3440 at 900 tall, plus 1280x720, 1366x768 and 844x390 (fonts at 390 and 1440) |
| controls | Chromium; flows in every engine | 390x844 (touch) and 1440x900 (mouse); each flow at its own viewport |
| motion | Chromium (CDP) | 1440x900 and 390x844 |
| engines | Chromium, WebKit, Firefox | wheel at 1440x900; touch and the address bar at 390x844 |
| system | none (files under serve.root) | |

`--quick` keeps only 390, 1280 and 1440, Chromium only, and makes no films.

## Not built yet, or partial

- Firefox is not installed on the owner's machine: the kit codes for it and reports `skip` with the reason.
- WebKit: this Playwright (1.63) expects `webkit-2359`; the machine has `webkit-2287`, so WebKit also
  reports `skip` until `playwright install webkit` is run.
- No OCR: facts inside pictures are caught only by the mockup folders and the banned image list.
- The acceptance test in `the studio build notes` (run the kit against the old builds; it must catch every
  known escape) has not been run, by the owner's call to save credits. The limits are proposals until he
  confirms them.


## The fast loop (added 6 Oct 2026, beside the gate, not instead of it)

The full run above is the gate. These are the minute-long checks the conductor runs after every handback, built from the
probes an earlier job wrote by hand thirty times. All read the optional `job.json` `page_check` object.

| file | what it does | time |
|---|---|---|
| `page_check.py` | direct load of every page, 2 sizes, Chromium and WebKit in parallel; 0 responses >= 400 and 0 errors; the first press of each flow must be visible and unique; banned words and dashes; a `walk` through real keys and Back and Forward; a screenshot after the open sequence; `--sheet` contact sheet; `--urls a,b,c` compares variants | about 70 s for 9 URLs x 2 sizes x 2 engines |
| `gesture_check.py` | every scrollable element (computed overflow) gets trackpad, wheel, fling and touch swipes started inside it; the step counter and face must not change; optional chrome gesture must step | about 50 s |
| `audio_check.py` | plays, performs each "leave", then measures the level of every audio context (analyser tapped, context forced to run): 0 means silent | about 40 s |
| `inputs.py` | the real input shapes and the audio tap, for any probe | |
| `serve_dev.py`, `devcheck.html`, `devcheck_summary.py` | no-cache dev server; `/_devcheck/` records what a real finger sends and the momentum after it | |
| `brief_lint.py` | flags offer words in a designer brief ("may", "if the rendering supports it") and banned words and dashes | instant |

`page_check` keys (all optional): `open` {desktop, phone} step lists (`key`, `wait`, `wheel`, `tap`, `click`, `swipe`; swipe
is Chromium only, use taps for WebKit), `ready_js`, `skip_hook_pages`, `multi_hooks`, `walk` and `walk_phone`
(`{"start":"/"}, {"click":sel,"expect_path":"/x/"}, {"back":true,"expect_path":"/"}`), `step_counter`, `face_js`,
`chrome_points`, `audio` {start, play, plays_js, leaves[]}. A worked example is `cds/01 clients/signal-2002/site/job.json`.
Proof it can fail: pointed at a deliberately broken copy of SIGNAL (no `<base href>`, a hidden hook twin first) it reports
the 404s and the hidden-twin hook; on the real site it passes all 138 rows.
