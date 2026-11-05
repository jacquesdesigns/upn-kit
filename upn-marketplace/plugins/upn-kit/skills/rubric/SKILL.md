---
name: rubric
description: Use when the person wants to build, define, revise, or standardise a rubric, scoring standard, quality bar, evaluation criteria, checklist, or "the standard we judge X against", or says look at these references and set the bar from them. For any business () or cross-business.
---

# /rubric , build a rubric from references

## Overview
A rubric is distilled FROM real examples, never invented in the abstract. Point at references (good
ones, weak ones, an existing standard), pull the criteria out of what actually separates good from
bad, write it into the library, register it. One lean pass.

## When to use
- "Set the bar for X", "what makes a good X", "build me a standard/rubric for X", "score these
  against a consistent standard from now on", "look at these and define the criteria".
- To revise an existing rubric: same skill, keep the handle, re-distil from the references.

Do NOT use to score an artefact against an existing rubric , that is `/score`. Do NOT use to reason
through a decision , that is `/court`.

## The rule that makes this work
**Criteria come from the references, not from your head.** Read the good examples and the weak ones
FIRST; the rubric is the difference between them, made explicit. Inventing plausible-sounding
criteria and skipping the references is the failure mode this skill exists to prevent. If the person names
no references, ask for two or three (a strong example, a weak one, and what they wish existed) before
writing anything.

## Steps
1. **Gather references (lean).** Read the examples named, plus one or two more they point to. A few
   targeted reads. NO agent fan-out, no deep-research (keep research lean). If a reference is
   a live URL, one fetch each.
2. **Distil the criteria.** What separates the strong references from the weak? Each real difference
   becomes a criterion. Name what each one TESTS in a clause, not a paragraph.
3. **Pick the type** (see `_RUBRIC-FORMAT.md`, bundled in this skill's folder):
   - **weighted-100** for "how good is this" scoring where dimensions sum to a total.
   - **multiplicative** when two factors interact per unit (e.g. the audit framework's
     Hours × Carryability per lane, pattern over total).
   - **gate-only** when it either clears a bar or does not.
   - **checklist** for a flat pre-flight pass.
4. **Set weights, gates, bands.** Weights: put the heavy numbers on what actually decides quality
   (in the carousel standard, visual-proof and hook and system carry 15 each; taste only 5). Gates:
   the two to four hard pass/fail conditions a piece cannot ship without. Bands: score ranges → a
   verdict label with a short instruction, not just a name.
5. **Write the file** with the header block from `_RUBRIC-FORMAT.md`. Rubrics go in `<brain>/shared/rubrics/<name>.md` (create the folder and `REGISTRY.md` the first time).
6. **Register it.** Append the row to `<brain>/shared/rubrics/REGISTRY.md`, keep the table sorted by name.
7. **Report.** The file path, plus one short paragraph: what each criterion tests and where the
   weight went. British English, no em dashes, no hype.

## Reuse, do not reinvent
- Format contract: `_RUBRIC-FORMAT.md` in this skill's folder.
- If a rubric already exists for this kind of thing, open it first and match its shape.

## Common mistakes
| Thought | Reality |
|---|---|
| "I know what a good X looks like, I'll just list criteria" | That is the exact trap. Read the references first; the rubric is their difference. |
| "More criteria = more rigour" | A rubric with 15 flat criteria scores nothing. Weight the few that decide quality; drop the rest. |
| "Gates and criteria are the same thing" | A gate is a hard yes/no a piece cannot ship without. A criterion is a soft score. Name gates separately. |
| "I'll fan out agents to research the standard" | Lean pass only. A few reads. Fan-out is the person's opt-in, cost stated first. |
