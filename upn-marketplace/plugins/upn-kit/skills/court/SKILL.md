---
name: court
description: Use when the person wants a decision stress-tested, a call argued both ways, a devil's advocate, a claim or research finding cross-examined, or says "court of Claude", "put this on trial", "argue me out of this", "steelman both sides", "is this actually true", "should I do X or Y". For strategy forks, contested claims, or judging an artefact hard. 
---

# /court , the court of Claude

## Overview
Adversarial reasoning. One side builds the strongest case FOR, one side builds the strongest case
AGAINST, a judge rules with reasons and a confidence level. Default runs as a bench trial in one
context. Verdict first.

## When to use
- **A decision:** a real strategy fork , pricing, positioning, build-vs-buy, content direction,
  "should I do X or Y". Where the person is weighing a call and wants it stress-tested, not validated.
- **A claim:** a contested fact or a research finding , "is this actually true", "can I rely on
  this". Evidence for, evidence against, verdict on what you can actually stand on.
- **An artefact, judged hard:** when a score is not enough and the borderline calls need arguing.

Do NOT use for a settled call the person has already made (that is not a fork). Do NOT use to author a
standard (`/rubric`) or to run a routine score (`/score`).

## The three roles (one context, run all three)
1. **Advocate** , the strongest honest case FOR the option / claim / artefact-as-good. Best version,
   not a strawman. If the person leans one way, the advocate takes their side and makes it airtight.
2. **Devil's advocate** , the strongest honest case AGAINST. This is the point of the whole exercise:
   attack the idea properly, surface the risk they are not seeing, name the failure mode. Do not soften.
   If they are wrong, this is where it shows.
3. **Judge** , rules. Weighs both, decides, gives the reasons, states a confidence level (high /
   medium / low) and what would change the ruling. The judge is allowed to say "neither , here is the
   third option both sides missed."

## By type
- **Decision:** advocate and devil's advocate argue the fork; judge rules on the call, names the risk
  that survives, gives the next step.
- **Claim / research:** advocate marshals the evidence for, devil's advocate marshals the evidence
  against and the holes in the sourcing; judge rules on what is actually reliable and at what
  confidence. Lean on evidence, not vibes. If a claim rests on something checkable and thin, say so.
- **Artefact:** pull the relevant rubric (`<brain>/shared/rubrics/REGISTRY.md`) and run `/score` for the
  numbers first , do NOT re-derive a standard here. Then the two sides argue the borderline criteria
  the score left contestable. **REQUIRED:** `/score` for the scoring; court only argues the margins.

## The output
Verdict first, then the reasoning, then the risks. the usual strategic format: recommendation first.
```
VERDICT: <the ruling, one line>   (confidence: medium)

FOR
  , <strongest points>
AGAINST
  , <strongest points, the real risk named>
WHY THIS WAY
  , <the judge's reasoning>
WHAT WOULD CHANGE IT
  , <the thing that flips the ruling>
NEXT STEP
  , <one clear move>
```
British English, no em dashes, no hype. Hold a view and defend it , no bland on-the-one-hand hedging.

## Two rules
**Bench trial by default, one context.** All three roles run here, in this context, near-zero extra
cost. Do NOT fan out agents for a normal court run. The whole value is one clear adversarial pass, not
a committee.

**--jury is opt-in, cost stated first.** For a genuinely big call the person can pass `--jury`: fan out a
few independent judges in parallel and reconcile their rulings. Before doing it, state the rough token
cost and offer the bench trial first (keep research lean). Never fire the jury unasked.

## Common mistakes
| Thought | Reality |
|---|---|
| "They lean this way, I'll make the case for it and go light on the against" | The devil's advocate is the point. Attack it properly or the court is theatre. |
| "Judging the artefact means re-deriving the standard here" | No. `/score` does the numbers; court argues the borderline criteria only. |
| "Big decision, I'll fan out a jury to be safe" | Bench trial first. Jury is opt-in and cost-stated. Fan-out is the person's call, not the default. |
| "The judge should stay neutral and present both sides" | The judge RULES, with confidence and a next step. Neutrality that dodges the call is a non-answer. |
