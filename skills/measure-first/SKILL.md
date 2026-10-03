---
name: measure-first
description: "No performance claim without a before/after measurement."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [performance, benchmarking, optimization, measurement]
    related_skills: [verification-gates, probe-first]
---

# Measure First

No optimization ships without a before/after measurement. "It feels faster"
and "this should reduce load" are unverified claims, and agents make them
constantly. This skill is the measurement contract: any change whose
justification contains a performance word (faster, lighter, fewer, smaller,
reduced) must produce a benchmark delta — the same measurement run on base
and branch.

Composes with `verification-gates`: measurement is its Gate 1 (red proof)
applied to performance claims — the "red" is the base measurement, the
"green" is the improved one.

## When to Use

- Any change justified by performance: algorithm swap, caching, batching,
  index, startup trim, bundle size, query count
- Reviewer suggestions of the form "this would be faster if..."
- Post-hoc: your PR description says "faster" and you haven't measured yet —
  stop, measure, or delete the word

Don't use for: correctness changes with no performance claim attached.

## Procedure

1. **Name the metric and the unit** before writing code: latency (p50/p95),
   throughput (ops/s), allocations (bytes), queries (count), binary size
   (bytes), startup (ms). One primary metric; others are context.
2. **Choose the instrument** — the cheapest honest one:
   - Micro: `timeit` / criterion / language-native bench
   - Macro: a realistic workload script with N repetitions, wall-clock
   - Counting: query counters, allocation profilers, byte diffs
3. **Measure the BASE first.** Same machine, same command, multiple runs
   (≥3; report median and spread). Save raw output.
4. **Change. Measure the BRANCH** with the identical command. One variable:
   the change.
5. **Report the delta honestly:** "p50 84ms → 61ms (-27%), n=5, spread
   ±3ms" — or report "no significant change" if that's what you measured.
   A null result reported honestly beats a fictional win.
6. **Regression-test it** where the suite supports it: a benchmark smoke
   threshold, or at minimum the measurement script committed alongside.

**Completion criterion:** base + branch raw outputs exist, same command,
the delta computed from them — and the PR description's performance claims
match the measured numbers exactly.

## Pitfalls

- **Benchmarking the wrong side:** measuring after writing the "optimized"
  code, then eyeballing what the base *would have* done. Base measurement
  happens before the change, always.
- **One-run deltas:** single measurements are noise. ≥3 runs, report
  median + spread; a delta inside the spread is "no significant change."
- **Microbenching a macro problem:** a 10x micro win nobody hits in
  practice. State the workload's realism; prefer macro unless the hot path
  is proven.
- **Improving the benchmark instead of the code:** tuning the measurement
  until it flatters the branch. Instrument changes invalidate both sides —
  re-measure the base too.
- **Unstated units:** "improved by 30%" of what? Name the metric, the
  units, and the workload in the same sentence as the number.

## Verification

**Runnable check:** the benchmark script committed, run twice:

```bash
python bench.py --ref <base-ref>    # base measurement, n>=3
python bench.py --ref HEAD          # branch measurement, n>=3
```

**Expected:** both exit 0 and print median + spread; the branch claim in
the PR/commit message equals the computed delta (or states "no significant
change").

**Evidence to capture:** both raw outputs (all runs), the bench script
path, and the delta statement as it appears in the PR description.