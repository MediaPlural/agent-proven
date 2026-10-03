---
name: dead-code-sweep
description: "Prove code unconsumed before deleting — and unnecessary."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [dead-code, cleanup, unused, refactoring, deletion]
    related_skills: [verification-gates, dedup-sweep]
---

# Dead Code Sweep

Find and remove code nothing needs — in two escalating proofs. Most
dead-code checks stop at "has zero references." Real cleanup starts there:

1. **Unconsumed** — nothing references it (the easy proof).
2. **Unnecessary** — it's *referenced* but shouldn't be: wrappers that only
   forward calls, compatibility APIs kept for history, defensive branches
   hiding impossible states, stale defaults, duplicate state sources, public
   surfaces nobody should depend on.

Adapts the used-vs-necessary distinction of danhuaxiansheng/claude-code-cleanup-skills
(MIT) with this library's baseline gates: every deletion lands with the suite
proven green before AND after.

## When to Use

- Post-refactor residue: old paths a migration left behind
- "Is this module still needed?" — audits before big refactors
- Wrappers/compat layers that only exist because other wrappers exist
- Review comments: "nobody calls this anymore" — verify, then delete

Don't use for: features behind flags scheduled for enable, plugin/extension
surfaces consumed externally (check the ecosystem, not just the repo), or
anything exported by a public API contract (semver constraints).

## Procedure

**Tier 1 — Unconsumed:**

1. **Enumerate candidates** — exports, functions, files, components, types:
   `search_files` for each identifier; vulture/`knip`/language-native
   analyzers for breadth. Record every reference site.
2. **Check the indirect consumption vectors** before trusting zero: string
   references (dynamic dispatch, DI registration, reflection), re-exports,
   test fixtures, codegen targets, scripts/CI files, documentation examples.
3. **Delete in one commit per tier-1 batch.** Run the full suite before and
   after (`verification-gates` Gate 2). Lint the touched files.

**Tier 2 — Unnecessary (referenced but hollow):**

4. **Wrapper audit:** a function that only forwards calls with no added
   value (no validation, no defaults, no logging, no naming) — inline it.
   One exception: intentional seams for testing or future dispatch.
5. **Compatibility audit:** APIs kept "for history" with zero external
   consumers — delete with the changelog note, or file for a deprecation
   cycle if the repo is a library.
6. **Defensive-branch audit:** branches guarding impossible states (post-
   validation re-validation, can't-happen type checks). Prove impossibility
   from the call graph before removing — if the proof needs a comment longer
   than the branch, keep the branch.
7. **Duplicate state:** two sources claiming the same fact — one becomes
   canonical, the other derived or deleted.

**Completion criterion:** every deletion has its consumption proof recorded
(zero references, or the necessity analysis); suite green before/after;
nothing behind a public-API contract was touched without a deprecation note.

## Pitfalls

- **Dynamic references are invisible to grep:** string-keyed dispatch,
  reflection, DI containers, `__getattr__`, codegen. Search strings too.
- **"Referenced" ≠ "needed":** tier 2 is where the real debt lives —
  but it's also where wrong deletions hurt. Prove necessity per finding,
  never batch-delete tier 2.
- **External consumers:** plugins, extensions, downstream forks. A public
  export's reference count inside the repo proves nothing about the world.
- **Test-only consumers count as dead-adjacent:** a function only tests
  exercise is a candidate for deletion WITH its tests — but only after
  confirming no production path was about to adopt it.

## Verification

**Runnable check:** full suite before and after each deletion batch, plus a
reference re-scan of the deleted identifiers:

```bash
search_files --pattern '<deleted-identifier>' . # expect: zero non-history hits
```

**Expected:** suite green both sides; re-scan returns zero live references
(git history/changelog hits don't count).

**Evidence to capture:** per-batch before/after suite outputs, the
consumption proofs, and the post-delete re-scan.