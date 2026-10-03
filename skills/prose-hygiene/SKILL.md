---
name: prose-hygiene
description: "Sweep grammar, typos, and clarity in comments and docs."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [grammar, typos, documentation, comments, prose-quality]
    related_skills: [verification-gates]
---

# Prose Hygiene

A gate battery for the *words* in a codebase: comments, docstrings, commit
messages, PR descriptions, README and docs pages. Code quality tooling
ignores prose; agents writing prose at speed accumulate grammar drift, typos,
and unclear antecedents that make the next reader (human or model) mistrust
the comment — or worse, follow it into the wrong behavior.

Distinct from stale-comment cleanup (see Peers: `code-hygiene-skills`
handles *expired* comments; this skill handles *broken* prose — grammar,
spelling, clarity — in comments that should stay).

## When to Use

- After any agent-authored batch of comments/docstrings
- Before committing docs, README changes, or PR descriptions
- Sweeping a repo's comment grammar before a public release
- Post-review: reviewers flagging "this comment doesn't parse"

Don't use for: deleting stale/expired comments (that's stale-cleanup,
a peer skill); rewriting code; changing technical content (only its
expression).

## The Sweep

1. **Collect** — the changed files' comments, docstrings, and the commit
   message/PR description. (For full-repo sweeps: docs pages + comment
   inventory.)
2. **Check, per finding class:**
   - **Grammar** — broken sentences, subject/verb disagreement, tense drift
   - **Spelling** — typos, wrong homophones (their/there, it's/its), casing
     of identifiers (identifiers themselves are NEVER "corrected" — see
     Pitfalls)
   - **Clarity** — ambiguous pronouns ("it updates it"), double negatives,
     sentences whose subject changes mid-stream
   - **Consistency** — mixed voice (imperative vs descriptive), mixed number
     agreement, Oxford-comma drift *within one file's comments*
3. **Fix minimally.** Preserve meaning exactly; prose fixes never change
   what the comment claims about the code. If a comment's *content* is wrong,
   that's a code bug — file it separately, don't silently rewrite it.
4. **Verify** — re-read every changed line; grammar fixes that alter meaning
   are regressions.

**Completion criterion:** every finding fixed or triaged; changed files'
comments read clean; no identifier was touched.

## Pitfalls

- **Never "fix" identifiers.** A finding that is actually a variable name,
  flag, path, or quoted output is correct as-is. Check before changing —
  this is the #1 false-positive class.
- **Meaning-preservation is absolute.** "Its not caching" → "It's not
  caching" is a fix; "It's not caching" → "It caches" is a *content change*
  smuggled through a grammar edit. Never.
- **Don't restyle.** Fixing grammar ≠ imposing a style guide. If the file's
  comments are casual, fixed-casual; don't convert to formal.
- **Quoted output and literals:** strings the code prints, error messages,
  and fixture literals are functional. Leave them unless the *task* includes
  them.

## Verification

**Runnable check:** spell-check the changed files with the identifiers
excluded (example: `codespell` with the repo's ignore file, or a targeted
pass), and diff-review that only prose lines changed:

```bash
git diff --unified=0 -- <changed-files> | grep -E '^[+-]' | grep -v -E '^[+-]{3}'
```

**Expected:** exit 0; every +/- line pair is comment/docstring/commit-prose;
zero identifier or code lines in the diff.

**Evidence to capture:** the prose-only diff, and the spell-check output
before/after.