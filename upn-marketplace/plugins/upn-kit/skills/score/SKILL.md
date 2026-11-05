---
name: score
description: Use when the person wants to score, grade, evaluate, rate, or judge an artefact (a page, pitch, bid response, copy, document, plan) against a named rubric or standard, or asks "how does this stack up", "is this ready to ship", "score this against X". Applies any rubric in <brain>/shared/rubrics/REGISTRY.md, for 
---

# /score , judge an artefact against a rubric

## Overview
Take an artefact and a rubric name, check the gates, run every criterion, land it in a band, say the
verdict in one line, then list the specific fixes ranked. One context does the whole thing.

## When to use
- "Score this tender response against the bid-response rubric", "how does this page rate", "is this ready", "grade
  this pitch", "run the standard over this".
- Any time an artefact should be judged against a bar that already exists.

Do NOT use to create the bar , that is `/rubric`. Do NOT use to reason through a contested decision
with no clean rubric , that is `/court`.

## Steps
1. **Resolve the rubric.** Read `<brain>/shared/rubrics/REGISTRY.md`, match the name the person gave to a row, open
   that file. If no rubric was named, list what the registry offers and ask which. If nothing fits,
   offer to build one with `/rubric` first.
2. **Read the artefact.** The file or the pasted content. Whole thing.
3. **Check the gates FIRST.** Each gate in the rubric's `## Gates` is an observable yes/no. Any gate
   that fails fails the piece outright regardless of score. Report which gate and why before the table.
4. **Score every criterion.** Go through the FULL `## Criteria` list this run, not just what failed
   last time. A criterion that genuinely does not apply is **N/A** and drops out of the denominator
   (it is never scored 0). Score against what the rubric says the criterion tests, not your gut.
5. **Total, band, verdict.** Sum (or, for multiplicative rubrics, compute per-unit and read the
   PATTERN per the bands table). Land it in a `## Bands` row. State the verdict in one line.
6. **Rank the fixes.** Name the specific, concrete changes that move the score most, hardest-hitting
   first. Point at the exact slide/line/section, not "improve the hook".

## The output (this is the shape , match it)
```
GATES: pass   (or: FAIL , <which gate>, <why> , stop here, fix the gate first)

<criterion>   12/15  ▓▓▓▓░
<criterion>   10/10  ▓▓▓▓▓
<criterion>    6/15  ▓▓░░░  ← dragging
<criterion>    N/A          (not in scope for this piece)
...
TOTAL   78/100    band: useful not viral
VERDICT: fix these two before it ships.
  1. <specific fix, exact location>
  2. <specific fix, exact location>
```
Prose in the fixes stays British English, no em dashes, no hype. For multiplicative rubrics render the
per-unit table (e.g. per lane: H × C) and read the pattern, the way the audit framework does. Note any
N/A dimensions after the table (omitted from the denominator, not a defect).

## Two rules
**Full re-run every time.** When the person pushes back or you iterate, re-score EVERY criterion, never
only the one that failed last round. Fixing one flagged criterion and re-presenting is the trial-and-
error loop that judging against references exists to avoid. One evaluated pass, all criteria, each round.

**One context, no agent chain.** The whole evaluation happens here, in this context. Do NOT spawn a
build agent, then a verify agent, then a fix agent , that ping-pong re-reads the artefact every
handoff and blew the token cap three times on the content factory. Evaluate and name fixes in one go.

## --jury (opt-in only, big calls)
For a genuinely high-stakes judgement the person can pass `--jury`: fan out a few independent scorers and
reconcile. It is NOT the default. Before fanning out, state the rough cost and offer the lean single
pass first (keep research lean). Never fire the jury unasked.

## Common mistakes
| Thought | Reality |
|---|---|
| "Last round only the hook was weak, I'll just re-score the hook" | Re-run every criterion. Single-flag re-scoring is the trap. |
| "This criterion doesn't apply, score it 0" | 0 means present-and-bad. Not-in-scope is N/A, dropped from the denominator. |
| "Score first, gates are a formality" | Gates first. A gate failure ships nothing regardless of a high score. |
| "I'll build/verify/fix with separate agents to be thorough" | One context. The agent chain is the token sink, not thoroughness. |
| "'Improve the hook' is a fix" | Name the exact change and location. Vague fixes send it back to trial and error. |
