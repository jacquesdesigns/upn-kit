# The rubric file format

Every rubric in this library follows this shape so the `/score` and `/court` skills can read it
without guessing. A human reads it top to bottom; the skills parse the fixed section names.

Keep it lean. A rubric is a judgement instrument, not an essay. If a criterion needs a paragraph to
explain, the criterion is doing two jobs; split it.

---

## The header (required)

Every rubric file opens with this YAML block:

```
---
name: <handle>                    # the short handle /score and /court resolve, kebab-case
applies-to: <area>               # which UPN area reaches for this (bids, website, reports...)
type: weighted-100 | multiplicative | gate-only | checklist
built-from: <the references this was distilled from>
---
```

- `name` is the handle you call it by. It must match the row in `REGISTRY.md`.
- `applies-to` is navigation, not a lock. A rubric for one area can be reused by another as-is.
- `type` tells the scorer how to add it up (see below).
- `built-from` names the references the rubric was distilled FROM (the reference-evaluation rule:
  criteria come from real examples of good and bad, not from thin air).

## The body (fixed section names)

### `## Gates`
Hard pass/fail conditions a piece cannot ship without. Checked BEFORE scoring. A gate failure fails
the piece outright regardless of the score. Write each as an observable yes/no. This is the
Most expensive rounds are gate failures, not craft failures, so name the gates
plainly. A rubric may have zero gates; most have two to four.

### `## Criteria`
The scored dimensions. What each one is depends on `type`:

- **weighted-100** , each criterion carries a weight; weights sum to 100. Each line names the
  criterion, its weight, and in one clause what it tests. Example shape:
  `- Hook /15 , does slide 1 stop the scroll with a callout, not a topic label`

- **multiplicative** , each criterion is a factor scored on a small band (e.g. 0-3), and the
  criteria multiply per unit rather than sum. Name each factor, its range, and what each end means.
  Example: the audit framework's `H (0-3) × C (0-3)` per lane, summed across lanes, where the
  PATTERN matters more than the total. State the max and how the pattern reads.

- **gate-only** , no scored criteria; the whole instrument is the `## Gates` section. Use when a
  piece either clears a bar or does not, and a number would be false precision.

- **checklist** , a flat list of yes/no items with no weights; the "score" is how many pass and which
  fail. Use for pre-flight passes where every item is a must.

Mark any criterion that genuinely does not apply to a given artefact as **N/A**: it renders N/A and
drops out of the denominator, it is never scored 0. (A 0 says "present and bad"; N/A says "not in
scope for this piece".)

### `## Bands`
Score ranges mapped to a verdict label, worst to best or best to worst, your call, but be consistent
within the file. Each band gets a short instruction, not just a name.
Example: `90-100 ship + test hard · 80-89 minor refine · 70-79 useful not viral · <60 rebuild`.
For multiplicative rubrics, bands map score PATTERNS (not just totals) to verdicts, ideally as a
small table (pattern → verdict → why), the way the audit framework does.

### `## Checklist` (optional)
A fast pre-flight pass of yes/no questions, for when you want the gut-check without the full score.
Optional on any rubric type.

---

## A minimal example

```
---
name: example-standard
applies-to: both
type: weighted-100
built-from: three strong examples + two weak ones named in the brief
---

## Gates
- Says something true and checkable, not a generic claim.
- Sounds like the owner, not like a press release (British English, no em dashes, no hype).

## Criteria
- Clarity /40 , can a stranger act on it after one read
- Specificity /35 , concrete and named, not abstract
- Tension /25 , a reason to care, not just information

## Bands
85-100 ship · 70-84 sharpen the weakest criterion · 50-69 one more pass · <50 rebuild

## Checklist
- One idea per piece?
- Would the author send it to a colleague?
```

---

## Notes

