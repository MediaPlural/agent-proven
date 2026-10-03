---
name: agent-regression
description: "Gate agent-stack changes on replayed golden tasks."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [regression, agent-behavior, model-swap, prompt-change, replay, manifest]
    related_skills: [verification-gates, probe-first, measure-first]
---

# Agent Regression

Code has CI. The agent stack — model, prompts, skills, tools, config — has
vibes. Any of those changes behavior silently: a model swap breaks one lane's
hard tasks, a prompt edit drops a sentence users needed, a skill patch reroutes
a workflow. This suite treats the stack as a system under test: **manifest
everything that affects behavior, keep golden tasks from real work, replay
before and after any change, gate on drift.**

Evidence this bites (observed, from our records): a provider/model swap
passed easy tasks and silently returned empty answers on hard ones
(`finish_reason=length`, zero chars) — caught only because a bench happened
to run; a harness update left in-flight work stranded mid-migration; skill
patches shipped with no history to compare behavior against.

## When to Use

- **Before any single-variable stack change:** model or provider swap, prompt
  edit, skill add/update/remove, tool schema or config change, harness
  release bump
- After a production agent failure: capture the trace, make it a golden case
  (the suite grows from real work, not imagined scenarios)
- Periodically: re-run goldens against live tools to catch the world moving
  under an unchanged stack

Don't use for: new capabilities with no prior behavior to compare (nothing
golden yet — record the first baseline), or stacks with zero production
traffic (record first, gate later).

## The Four Layers

**1. MANIFEST — capture what affects behavior.** A stack version is more
than the model name: model+provider, prompts/SOUL/skills (hashed), tool
list + schemas, config hash, backend/harness revision, timeouts, profile
seed. Hash files, not names — "skills" can drift while the label stays.
Runnable: `tools/stack_manifest.py` in this repo.

**2. GOLDENS — real tasks, frozen.** 10-20 cases from production work:
fixed input, fixed fixtures (recorded tool responses), fixed initial state,
declared allowed tools, known-good outcome. Cases are JSON
(`schemas/golden-case.schema.json`). Small and high-confidence beats large
and synthetic: goldens protect behavior you actually rely on.

**3. REPLAY — one variable at a time.** Baseline run on the current stack;
apply exactly ONE change (model OR prompt OR skill — never two); candidate
run on the same cases, same fixtures, same state seed. Grading criteria live
in the case, and come in two families:

- **Deterministic (carry the gate):** tool called/not-called, structured
  field values, forbidden patterns, file-changed, exit code. Zero flake.
- **Judged (review, don't block, by default):** entailment (required fact
  present), rubric 1-5. Median of ≥3 trials; compare against the baseline
  mean, not an absolute bar; a case that flips with no change twice in a
  month gets quarantined and rewritten.

**4. GATE.** Hard criterion flips pass→fail = block (the change did it —
inputs were frozen). Judged drift beyond threshold = review, not auto-block.
New behavior that's *right* (stale expectation) = update the case in its own
reviewed commit, one criterion at a time — never re-bless a whole run.

## Procedure

1. Capture manifest (`stack_manifest.py`) → baseline manifest digest.
2. Run goldens, ≥1 trial for deterministic-only, ≥3 for judged. Save traces.
3. Apply ONE change. Capture manifest again — confirm exactly one field
   family moved, or the test is invalid.
4. Re-run goldens identically. Diff per-criterion (table: case, criterion,
   old, new, direction).
5. Gate: block on hard flips; review judged drift; ship on green.
6. Production failure later → capture trace → new golden case → the gate
   grows teeth.

**Completion criterion:** both manifest digests + both run reports exist;
every criterion row is classified (regression / expected change / flake /
improvement); the change ships only on green-or-accepted.

## Comparison engine integration

Deterministic trace comparison doesn't need reinventing:
[behaviorlock](https://github.com/christian140903-sudo/behaviorlock) takes
recorded observations and contracts them (sequence/set/rank/delta matchers,
CI gate, SARIF). Emit goldens as its trace format where you use it — this
suite supplies the manifest/replay/case layers behaviorlock deliberately
leaves to your harness. Criterion families adapted from
[Runtype's regression guide](https://www.runtype.com/guides/prompt-change-regression-testing);
manifest completeness from
[Latitude's Hermes-update practice](https://latitude.so/blog/catch-regressions-after-a-hermes-update);
golden-replay from [agentpatterns' simulation testing](https://www.agentpatterns.ai/workflows/simulation-replay-testing/).

## Pitfalls

- **The plausible-answer trap:** the final message looks fine while the
  trajectory rots (wrong tool, more retries, higher cost). Grade outcome AND
  tool path.
- **Two variables at once:** model + prompt changed together = the failure
  is unattributable. One change per replay, always.
- **Exact-match on prose:** goes red on every harmless rephrase and teaches
  the team to ignore the suite. Deterministic criteria assert behavior
  (calls, fields, patterns), not wording.
- **Goldens that never see production:** synthetic-only suites test the
  behavior you imagined. Every real failure becomes a case.
- **Re-bless-all:** an "accept all" button turns the suite into a recording
  of current behavior. One criterion, one reviewed commit.

## Verification

**Runnable check:** the manifest tool itself, twice — digests are the drift
detector, so compare DIGESTS (the manifest carries an informational
`captured_at`; full-file diffs would false-red on it):

```bash
python tools/stack_manifest.py --root <cfg> --model X --provider Y --out m1.json
python tools/stack_manifest.py --root <cfg> --model X --provider Y --out m2.json
# digests identical on unchanged stack: expect SAME manifest_digest
# touch any hashed file (or change --model): expect DIFFERENT manifest_digest
```

**Expected:** clean tree → identical digests; any behavior-affecting file
touched → different digest. The manifest must detect drift — that IS its job.

**Evidence to capture:** baseline + candidate manifest digests, per-criterion
diff table, trial counts, and the gate decision (ship/block/accepted-with-reasons).