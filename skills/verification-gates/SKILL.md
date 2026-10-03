---
name: verification-gates
description: "Prove changes work before done — five gates, with evidence."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, verification, quality, red-proof, baseline]
    related_skills: [test-driven-development, requesting-code-review]
---

# Verification Gates

A battery of five checkable gates that separates "the agent said done" from
"the change is proven." Distilled from a real defect inventory: a probe build
with ~14 defects across 6 model-revision cycles, where every escape traced to
a skipped gate. Run them before reporting any non-trivial change done. This
skill defines gates; TDD defines test discipline, and a code-review loop
defines reviewer coverage — they compose.

Inspired by obra/superpowers `verification-before-completion`; these gates
extend it with baseline-delta attribution, finding spot-checks, and
count-verification, drawn from real escape analysis.

## When to Use

- Any non-trivial code change: bug fix, new tool, analyzer, parser, refactor
- Re-running after reviewer feedback (gates re-apply to the response)
- Before filing audit findings or analysis results anywhere public

Don't use for: pure-read tasks, single-line docs edits, config tweaks with an
immediate observable effect.

## The Five Gates

### Gate 1 — Red-proof every bug fix

A fix without its failing test on the unmodified base is unverified. Write
the invariant test, run it against pristine code, capture the failure output,
then fix. A probe that never went red proves nothing — and a fix that doesn't
flip its own probe red→green isn't a fix (this exact case shipped once: a
patch added a sort-key function but never passed `key=` to `sorted()`, and
only the probe's still-red verdict exposed it).

**Check:** the invariant test's failure output on base exists in the task
record, and the same test passes after the change.

### Gate 2 — Baseline before change

Run the affected test files on the pristine base BEFORE changing anything and
record the pass/fail set. A failure discovered only after your change is
unattributable — you will chase environmental ghosts or wrongly blame your
own diff. Re-run after; only the delta is yours.

**Check:** baseline output saved; post-change failure set is a subset of
baseline (minus the failures your change fixes).

### Gate 3 — Lint is a reviewer, read its output

Lint/diagnostics are not decoration. They catch a class of defects cheaper
than runtime does. Never report done with unread lint errors — and never
batch-fix them blindly: each error is a design question, answer it.

**Check:** lint output on changed files is clean, or every remaining finding
is triaged with a written reason.

### Gate 4 — Spot-check every finding

Any audit or analysis output gets verified against source before being stated
as fact — one spot-check pass on a real findings list found four
false-positive classes worth 90% of the entries. Verify declared counts
programmatically too: an enumerated list that disagrees with a declared total
is a bug in your report, not a rounding error.

**Check:** for every finding, the source line exists and says what the finding
claims; counts match enumeration.

### Gate 5 — Independent verification

No agent verifies its own work as the only check. A fresh-context reviewer
(separate session or subagent, seeing only the diff) or a mechanical checker
the code didn't author must confirm. Fail-closed: an unparseable verdict is a
fail.

**Check:** an independent pass exists with a named verdict; security and logic
lists are empty or addressed.

## Quick Reference

```text
Gate 1  invariant test RED on base → capture → fix → GREEN
Gate 2  suite baseline on base → change → suite again → delta only
Gate 3  lint changed files → clean or triaged
Gate 4  every finding read against source → counts verified
Gate 5  fresh-context reviewer → verdict recorded
```

## Pitfalls

- **The pre-existing failure trap:** a test failing after your change may have
  failed before it. Gate 2's baseline is the only honest attribution; without
  it, "environmental" is a guess.
- **Tautology probes:** a test that passes before AND after the fix tests
  nothing. If the red proof won't go red, the test is wrong — fix the test
  first.
- **Counting your own output:** declared totals ("found 12 issues") are hard
  assertions. Re-count programmatically; never finalize on "close enough."
- **Static-analyzer findings on long-lived files:** run the tool on the
  pristine base AND your branch; only the delta is yours. Findings matching
  the file's established safe patterns are informational — but verify the
  pattern, don't assume it.

## Contributing

This skill is part of the **agent-proven** library — improvements welcome.
See the repo root's CONTRIBUTING.md. The bar for changes: each gate must
trace to an observed failure mode (attach the evidence), and new gates must
name the check that falsifies them.

## Verification

**Runnable check (this skill's headline invariant):** after any fix, re-run
its invariant test against the unmodified base using a control checkout and
confirm it still fails there while passing on your branch:

```bash
git -C <repo> archive <base-ref> | tar -x -C <control-dir>
bash <control-dir>/scripts/run_tests.sh <invariant-test> -- -q
```

**Expected:** non-zero exit with the invariant's failure in the control tree;
exit 0 with the same test passing in your working tree.

**Evidence to capture:** both outputs (control FAIL, branch PASS) plus exit
codes, pasted into the task record with the test path.