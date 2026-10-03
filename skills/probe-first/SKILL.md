---
name: probe-first
description: "Reproduce bugs with a probe before fixing — red proof first."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, debugging, reproduction, probes, red-proof]
    related_skills: [verification-gates, systematic-debugging]
---

# Probe First

Before fixing any reported bug — yours, a reviewer's, a user's — build a
minimal probe that reproduces it, watch it go RED, and only then fix. A fix
without a red reproduction is a guess wearing a patch's clothes. Born from a
real review cycle: an external review reported three bugs; probes reproduced
two exactly and exposed a deeper root cause behind the third that the
reporter's symptom had masked.

Composes with `verification-gates` (the red proof IS its Gate 1, made
executable) and `systematic-debugging` (probe-after-root-cause narrows the
reproduction to the mechanism, not the symptom).

## When to Use

- Any bug fix, in any language, from any source (reviewer, user, CI, self)
- Reviewer/reports with reproduction claims — verify them, don't trust them
- Before refactoring "fragile" code with no known failing behavior

Don't use for: features (no bug exists yet), cosmetic-only changes, or when
an existing failing test already covers the report.

## The Three Probe Archetypes

1. **Concurrency probe** — hammer the code from N threads/processes, count
   survivors. Losses that appear only under contention are invisible to
   single-threaded tests.
2. **Ordering probe** — force the edge condition (tiny sizes, boundary
   values), tag records, read back through the public API, compare observed
   vs expected order.
3. **Environment probe** — run the same operation under the hostile
   environment (different OS, locale, filesystem, permissions) where the
   report says it breaks.

## Procedure

1. **Read the report, write the claim.** One sentence: "X does Y when Z."
   If you can't state the claim, you can't falsify it.
2. **Write the smallest probe** that exercises the claim through the public
   API — not internals. One file, stdlib only, runnable directly.
3. **Run it on the unfixed code. Capture the RED.** Exit code + output.
   A probe that won't go red is testing nothing — fix the probe first.
4. **Fix. Run the probe: GREEN.** Same probe, same command.
5. **Keep the probe as the regression test** (port it into the suite's test
   conventions) or attach both outputs to the task record.

**Completion criterion:** RED output and GREEN output from the identical
command exist, and the probe's exit code flipped.

## Pitfalls

- **Trust-but-verify reviewer claims:** reviewer reproductions are evidence,
  not truth. Re-run them; one real case had a report's corruption profile
  point to a deeper root cause (text-mode file translation) than the reported
  one.
- **The probe that fixes nothing:** if the fix lands and the probe is still
  red, the fix is wrong or partial — this shipped once (a sort-key function
  that was never wired into `sorted()`). Never mark done on a still-red probe.
- **Tautology probes:** passes before AND after = tests nothing.
- **Over-built probes:** a probe that needs the full app running is a test,
  not a probe. Shrink until it fails alone.

## Verification

**Runnable check:** the probe command, run twice:

```bash
python3 probe.py --module <unfixed>   # expect: exit non-zero, RED verdict
python3 probe.py --module <fixed>     # expect: exit 0, PASS verdict
```

**Expected:** first invocation exits non-zero with the failure signature;
second exits 0 with the pass signature. Same command, flipped outcome.

**Evidence to capture:** both outputs with exit codes, the probe file path,
and the claim sentence it falsifies.