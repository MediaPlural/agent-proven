---
name: dedup-sweep
description: "Detect clone families, decide, execute gated merges."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [duplication, refactoring, dry, clone-detection, cleanup]
    related_skills: [verification-gates, dead-code-sweep]
---

# Dedup Sweep

Detect duplicate and near-duplicate code ("clones"), group them into families,
decide per family — merge or keep, with reasons — then execute the merges with
regression gates. Two-phase discipline: **analysis and execution are separate
steps with different failure modes; never merge them.** A typo in an inventory
must never become a bad code edit.

Adapts the clone-family model of niuma996/code-hygiene-skills
(`find-duplication`, MIT) — detect/decide/execute with drift classification —
and wires in this library's verification gates at the execution step.

## When to Use

- Copy-pasted helpers, try/catch wrappers, structurally similar functions
- Before refactors: shrink the duplication surface first
- Review comments like "this is the same as X"
- Post-feature: the third time similar code appears, sweep

Don't use for: intentional parallel structures (e.g., per-platform variants
kept deliberately — record them as KEEP with the reason).

## Procedure

**Phase 1 — DETECT (inventory only; no edits):**

1. **Scan** — LLM-driven anchor-grep by default (read the code, find
   same-shape blocks); tool-assisted when token-precision is needed
   (jscpd/copydetect/pmd-cpd for exact clones, lizard for complexity).
2. **Group into clone families** — every row: files+lines, the family's
   common shape, and **drift classification**: none (identical) / minor
   (whitespace, names) / structural (same intent, diverged bodies).
3. **Assign priority:** P0 identical ≥10 lines zero drift (safe mechanical
   merge) → P3 similar-intent-different-implementation (usually KEEP).
4. **Stop.** The inventory is the deliverable of phase 1. No edits yet.

**Phase 2 — DECIDE (per family, reasons recorded):**

5. **Pick a strategy per family:** extract shared helper / parameterize /
   delete the dead copy / keep all (with reason). The decision rule:
   - drift none + both live → extract helper
   - drift minor → extract + parameterize the deltas
   - drift structural → usually keep; forcing a shared abstraction of
     diverged code creates worse coupling than the duplication
6. **Check the blast radius** for each merge: callers of every copy, tests
   covering each site, public-API exposure.

**Phase 3 — EXECUTE (gated):**

7. **One family per commit.** After each: baseline-verified test run
   (`verification-gates` Gate 2) and lint on touched files.
8. **Post-merge sweep** the new shared module: stale comments on the old
   copies' remnants, dead tests for removed variants
   (`dead-code-sweep`).

**Completion criterion:** every family has a decision + reason in the
inventory; merged families each have a green post-merge run; no KEEP family
was merged "while we were in there."

## Pitfalls

- **Premature DRY:** two things that look alike but evolve for different
  reasons (platform variants, deliberate duplication per "AHA vs rules of
  three") belong to KEEP. Wrong merges couple them forever.
- **Merge-by-inventory-typo:** phase separation exists because inventories
  carry errors. Re-verify each family's lines before executing.
- **The abstraction that ate the codebase:** if a "shared" helper needs 5+
  flags to serve its family, the code wasn't duplicates — un-merge it.
- **Structural drift forced into a mold:** P3 families stay P3. Extracting a
  common interface for diverged implementations is a redesign, not a dedup.

## Verification

**Runnable check:** the full-repo test suite before and after the sweep, plus
a duplicate-count re-scan:

```bash
jscpd --min-tokens 70 --reporters console . | tail -2   # before AND after
```

**Expected:** suite green both sides (delta = zero); the after-scan's clone
count is materially below the before-scan for the P0/P1 families merged.

**Evidence to capture:** both scan outputs, the per-family decision table,
and the per-commit test runs.