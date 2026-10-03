---
name: verbose-code-trim
description: "Cut verbosity without losing behavior — same, shorter."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [refactoring, verbosity, cleanup, simplification, readability]
    related_skills: [verification-gates, prose-hygiene, dead-code-sweep]
---

# Verbose Code Trim

Cut bloat: verbose constructs, redundant ceremony, over-guarded logic,
boilerplate a language idiom already covers. Every trim must preserve
behavior *exactly* — the contract is "shorter says the same," verified by
tests and by diff-reading. This is not about cleverness; compressed code
must stay the MOST readable option, not the least.

## When to Use

- Agent-generated batches: models pad code with ceremony (over-explicit
  checks, re-stated invariants, wrapper noise)
- Before reviews: reviewers spend budget on verbosity instead of substance
- Post-migration: old-style idioms a newer language version makes redundant
- "This function is 60 lines and I can't find the logic"

Don't use for: hot paths without a measurement (see `measure-first` —
"shorter is faster" is a claim), public API signatures, security-critical
validation (explicit > terse, always), or code that's long because the
domain is long.

## The Trim Targets

| Target | Verbose form | Trimmed form |
|---|---|---|
| Manual loops | 5-line accumulate loop | comprehension / sum / itertools |
| Re-stated invariants | re-checking a precondition already guaranteed upstream | trust the contract, delete the re-check (prove it) |
| Over-exception | try/except around code that can't raise | delete the wrapper (prove it can't) |
| Boolean ceremony | `if x: return True else: return False` | `return x` |
| Chain-of-elif | elif ladder mapping values | dict dispatch / match |
| Wrapper passthrough | function that forwards args unchanged | call directly (see dead-code-sweep) |
| Overbuilt classes | class with state used once | function |
| Comment-code echo | comment restating the next line | delete the comment (prose-hygiene) |
| Defensive defaults | default parameter never exercised | delete or assert |

## Procedure

1. **Pick a unit** (function or module) and establish the green baseline:
   tests passing on it, lint clean.
2. **Mark the logic lines** — the lines that DO the thing. Everything else
   is candidate ceremony.
3. **Trim one target at a time.** After each: the same tests, the same lint.
   If a trim needs a behavioral argument ("this can't raise because..."),
   write that proof as a comment or a test — the proof is the trim's license.
4. **Re-read the result.** The trimmed code must be MORE readable, not
   denser. If you have to unpack it mentally, un-trim — the target was
   wrong, not the code.
5. **Diff-verify:** the final diff shows no logic-line changes — only
   ceremony removal. (`git diff` should read like subtraction.)

**Completion criterion:** tests green before/after; lint clean; the diff is
pure subtraction or idiom replacement; a cold reader picks the trimmed
version.

## Pitfalls

- **Cleverness creep:** comprehensions nested 3 deep "save lines" by
  spending readability. Rule: if the trim needs a comment to explain, it
  isn't a trim.
- **Silent behavior change:** deleting "redundant" checks that weren't
  (order-of-evaluation, side effects in the removed expression). The
  baseline gate catches these — never skip it for "obviously safe" trims.
- **Trimming the explanation with the bloat:** a long function may be long
  because it carries WHY-comments. Those move to `prose-hygiene` for
  tightening, not deletion.
- **Public contracts:** signatures, exception surface, and return types are
  behavior. Trims that change call sites aren't trims — they're refactors.

## Verification

**Runnable check:** the unit's tests before and after, plus a line-count
delta:

```bash
bash <repo>/scripts/run_tests.sh <unit-tests> -- -q   # green, both sides
git diff --stat                                       # net subtraction
```

**Expected:** identical pass set both sides; net negative diff (or neutral
where a comment moved); no logic-line additions in the diff.

**Evidence to capture:** both test outputs, the diff, and the line-count
delta (before → after).