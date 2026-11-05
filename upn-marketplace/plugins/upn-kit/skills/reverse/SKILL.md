---
name: reverse
description: Log a disagreement with the judge (or with Claude's design call) into the person's reversal log, so future judging learns their taste. Use when the user types /reverse, or says "the judge is wrong", "I disagree", "it passed but I hate it", "that's actually fine", "send that back", or overrules a verdict.
---

# Reverse

One sentence from the person becomes one row in `<home>/taste/REVERSAL-LOG.md` (`home` is in
`~/.claude/upn-kit/config.json`).

Usage: `/reverse <page or part>, <what the judge said>, <what I say and why>`
Example: `/reverse home hero, judge passed it, too generic, looks like a template`

## Steps

1. Work out the project (the folder you are in, or ask), the page or part, what the judge said (read the
   newest `judge/*/verdict.md` if the person did not say), and what the person says.
2. **Keep their words.** The "Why" column quotes them as they said it. Do not tidy it into a rule.
3. Add the row at the TOP of the table (newest first). Never edit or delete an old row.
4. Also add one line to that project's `DESIGN-NOTES.md`, so the fix for this project is recorded.
5. Reply in one line: what was logged. Do not argue, and do not turn it into a general rule. If it is the
   third time a similar reversal has been logged, mention it once and suggest `/taste-review`.
