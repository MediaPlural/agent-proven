---
name: repo-organize
description: "Score module debt, fix worst-first with gates."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [organization, architecture, tech-debt, refactoring, audit]
    related_skills: [verification-gates, dead-code-sweep, dedup-sweep]
---

# Repo Organize

Map the codebase into functional modules, score each for technical debt, and
pay the debt down incrementally — worst module first, one commit at a time,
every fix regression-gated. The sweep skills (`dead-code-sweep`,
`dedup-sweep`, `verbose-code-trim`) are the tools this skill aims.

Adapts the module-map/score model of Asixa/codemap-skill (MIT) — functional
modules not files, 0-100 debt scoring, per-module independent audit — as a
portable procedure with this library's gate battery wired in.

## When to Use

- "This codebase is a mess — where do we even start?"
- Pre-hiatus hygiene: leave the repo better-organized for the next session
- Before a big feature lands on shaky ground
- Post-merge drift: several features in, the map has changed

Don't use for: greenfield (no debt to score), or when a repo owner imposes
an architecture — their map wins.

## Procedure

**Phase 1 — MAP:**

1. **Decompose into functional modules** — the capabilities that matter
   (a store, a handler group, a feature, a plugin), not files. Lay them out
   along real data-flow. 10-40 modules for a typical repo; more means the
   granularity is wrong.
2. **Record the map** as a committed artifact (`modules.json` or a markdown
   table): module, purpose, key files, dependencies. The map is diffable
   and survives sessions.

**Phase 2 — SCORE (per module, independently):**

3. **Audit each module against a fixed rubric** — same criteria for every
   module, evidence as file:line findings, not vibes. Score 0-100 (100 =
   healthy) + grade A-F:
   - dead/legacy paths · monkeypatches · silent fallbacks · swallowed errors
   - duplication (cross-ref `dedup-sweep` families)
   - god-module symptoms (too many responsibilities, tangled imports)
   - test coverage posture · comment-code trust
   - dependency direction violations (imports pointing against the data-flow)
4. **Independence matters:** score each module in a fresh context
   (subagent or cold session) so one bad module doesn't anchor the whole
   audit.

**Phase 3 — FIX (worst-first, gated):**

5. **Rank by score × blast-radius weighting.** Cheapest wins first inside
   the worst tier: dead-code-sweep a module before redesigning it.
6. **One module, one commit series.** Each fix: baseline green → change →
   green → re-score the module. The loop only exits on an independent
   acceptance check, not the fixer's word.
7. **Re-run the map incrementally:** changed modules re-audited; scores are
   the trend line. Debt pay-down is visible or it isn't happening.

**Completion criterion:** every module has a score + findings; the worst
tier has commits with per-commit green runs; the map artifact reflects
current reality; re-scores improved or the reason is recorded.

## Pitfalls

- **The map is a means:** don't spend the whole session perfecting modules
   .json. A rough map that fixes real debt beats a beautiful map.
- **Score theater:** numbers without file:line evidence are decoration.
   The rubric demands findings; empty findings = re-audit.
- **Big-bang urges:** "reorganize everything this pass" is how refactors
   die. Worst-first incremental is slower per day and survivable per
   month.
- **Independence collapse:** scoring 30 modules in one context turns into
   one rubber stamp. Fresh context per module, or per batch at minimum.
- **Fixing what scores well:** tempting cleanups in A-grade modules are
   procrastination from the D-grade one. The ranking exists to resist.

## Verification

**Runnable check:** the map artifact + a re-scored worst module after its
fix series:

```bash
test -s <map-artifact> && grep -c '"module"' <map-artifact>
bash <repo>/scripts/run_tests.sh <worst-module-tests> -- -q   # green post-fix
```

**Expected:** map artifact exists with N modules; the fixed module's tests
green; its re-score is higher than its prior score in the artifact.

**Evidence to capture:** the map artifact, per-module score tables with
findings, per-commit test runs, and the before/after scores of fixed
modules.