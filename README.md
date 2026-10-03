# agent-proven

**Verification gates and quality tooling for AI coding agents — every "done" backed by evidence.**

A growing library of agent skills that make coding agents *prove* their work
before reporting done. Born from real escape analysis: a single probe build
produced ~14 defects across 6 model-revision cycles, and every escape traced
to a skipped verification step. Instead of "try harder," these skills encode
the checks that catch what rationalization misses.

## Why another skill library?

Because reinventing wheels is a quality bug. This library exists to:

1. **Distill observed failure modes** into checkable gates — every rule here
   traces to a defect that actually shipped, not an imagined one.
2. **Not duplicate the ecosystem.** Before any skill lands here, we search
   the existing landscape (obra/superpowers, prove-it, make-no-mistakes,
   production-ai, and others) and either adapt-and-credit or fill a gap we
   can name.
3. **Improve in the open.** Others' improvements are the point — see
   CONTRIBUTING.md.

## Skills

| Skill | What it does |
|---|---|
| [`verification-gates`](skills/verification-gates/SKILL.md) | Five checkable gates between "agent said done" and "proven": red-proof, baseline-delta, lint-triage, finding spot-checks, independent verification. |

## Installation

Skills here follow the open Agent Skills standard (a `SKILL.md` with
frontmatter) and install into any compatible runtime:

**Claude Code** (skills live in `~/.claude/skills/`):
```bash
git clone https://github.com/MediaPlural/agent-proven ~/.agent-proven
ln -s ~/.agent-proven/skills/verification-gates ~/.claude/skills/verification-gates
```

**OpenAI Codex** (`~/.agents/skills/`):
```bash
ln -s ~/.agent-proven/skills/verification-gates ~/.agents/skills/verification-gates
```

**Cursor** (`.cursor/skills/` or `.agents/skills/`):
```bash
ln -s ~/.agent-proven/skills/verification-gates ~/.cursor/skills/verification-gates
```

**Hermes Agent**: copy to `~/.hermes/skills/software-development/verification-gates/`
or use `hermes skills` installation if the repo is published to the catalog.

## Design principles

- **Evidence over claims.** A gate without a check that can fail is prose.
- **The author never grades the author.** Independent verification is a gate,
  not a courtesy.
- **Delta attribution.** Failures your change didn't cause are environmental —
  proven by baseline, not asserted.
- **Counts are hard assertions.** "Found N issues" is verified by re-counting.
- **Adapt, credit, or gap.** Never publish what the ecosystem already has
  without credit; never duplicate what a peer does better.

## License

MIT — see [LICENSE](LICENSE).

## Credits

- `verification-gates` extends the tradition of
  [obra/superpowers](https://github.com/obra/superpowers)'
  `verification-before-completion`, with gates drawn from observed agent
  escape analysis.
- The broader verification ecosystem this library deliberately sits among:
  [prove-it](https://github.com/Pablo-aps/prove-it),
  [make-no-mistakes](https://github.com/momomuchu/make-no-mistakes),
  [production-ai](https://github.com/jimtin/production-ai).