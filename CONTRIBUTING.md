# Contributing to agent-proven

Improvements to this library are the point, not a courtesy. Two rules make
contributions strong instead of noisy:

## Rule 1 — Search before you write (don't reinvent the wheel)

Before proposing a new skill or gate, **search the ecosystem**:

- [obra/superpowers](https://github.com/obra/superpowers) — the archetype
  library (TDD, verification-before-completion, systematic-debugging)
- [prove-it](https://github.com/Pablo-aps/prove-it) — adversarial verification
- [make-no-mistakes](https://github.com/momomuchu/make-no-mistakes) —
  enforcement machinery (frozen specs, tamper detection)
- [production-ai](https://github.com/jimtin/production-ai) — gate library
- [tomwangowa/agent-skills](https://github.com/tomwangowa/agent-skills) —
  completion-gate and quality gates

Then pick ONE lane:

1. **Adapt + credit.** The behavior exists; port it with clear attribution in
   frontmatter `author:` and a Credits section. Say what you changed.
2. **Extend.** A peer skill covers part of it; your addition is a delta —
   write only the delta, and cross-reference the peer.
3. **Fill a named gap.** Nothing covers it — say what you searched and why
   the gap is real in your PR description.

Duplicate-without-credit PRs are closed, not merged.

## Rule 2 — Every gate traces to an observed failure

A gate, rule, or pitfall is only as strong as its evidence. For each change:

- **New gate/rule:** attach the observed failure it prevents (a real session
  transcript excerpt, a bug that shipped, a defect inventory line). Imagined
  problems get imagined gates — we don't take those.
- **Modifying a gate:** show the gate missed a real case (attach the escape)
  or that its check has a false-positive cost (attach the false positive).
- **New skill:** it must carry a runnable verification contract — a command
  that fails when the skill's procedure is wrong — per the standard
  skill-authoring pattern.

## Skill format

Standard Agent Skills shape: a directory with `SKILL.md`, YAML frontmatter
(`name`, `description` ≤ 60 chars ending with a period, `version`, `author`
crediting humans first, `license: MIT`, `platforms`), body sections:
When to Use / Procedure / Pitfalls / Verification. Keep skills ~100-200
lines; bulky material goes in `references/`.

## PR process

1. Fork → branch (`feat/<skill>` or `improve/<gate>`) → commit → PR.
2. PR description carries the evidence (Rule 2) and the search summary
   (Rule 1).
3. A maintainer runs the counter-check: tries to name a case where your gate
   is wrong. If they can't, it merges.
4. Improvements to existing gates that survive counter-checking get a
   `related_skills` / Credits cross-reference when they derive from a peer
   library.

## Improvement suggestions we explicitly want

- New observed failure modes (with evidence) that current gates miss
- Tighter or cheaper checks for existing gates
- Cross-runtime install patterns we haven't documented
- Empirical results: gates measured against with/without scenarios

## What we won't take

- Marketing prose ("powerful", "comprehensive") in skill bodies
- Gates without evidence
- Duplicates of ecosystem peers without credit
- Enforcement machinery that breaks on any of the three major OSes