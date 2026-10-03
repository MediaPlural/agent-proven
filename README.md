# agent-proven

**Full-suite verification and quality tooling for AI coding agents — every claim backed by evidence.**

A complete library of agent skills covering the quality spectrum: verification
before "done," probe-first debugging, measured performance, prose hygiene,
duplication sweeps, dead-code removal, verbosity trimming, and whole-repo
organization. One install covers the scenarios; the suites compose.

Born from real escape analysis — every rule traces to a defect that actually
shipped, and the peer ecosystem's best ideas are included, credited, and
integrated rather than left for you to assemble.

## The Suites

| Suite | Skill | What it does |
|---|---|---|
| Verification | [`verification-gates`](skills/verification-gates/SKILL.md) | Five checkable gates between "agent said done" and "proven": red-proof, baseline-delta, lint-triage, finding spot-checks, independent verification. |
| Debugging | [`probe-first`](skills/probe-first/SKILL.md) | Reproduce the bug with a probe that goes RED before any fix — concurrency, ordering, and environment probe archetypes; the probe becomes the regression test. |
| Performance | [`measure-first`](skills/measure-first/SKILL.md) | No performance claim without before/after measurement — base measured first, deltas reported honestly (including null results). |
| Prose | [`prose-hygiene`](skills/prose-hygiene/SKILL.md) | Grammar, typo, and clarity sweep for comments, docstrings, commit messages, docs — meaning preserved absolutely, identifiers never "corrected." |
| Duplication | [`dedup-sweep`](skills/dedup-sweep/SKILL.md) | Detect clone families, decide per family (extract / parameterize / delete / keep, with reasons), execute one family per commit with regression gates. |
| Dead code | [`dead-code-sweep`](skills/dead-code-sweep/SKILL.md) | Two escalating proofs: unconsumed (zero references, indirect vectors checked) and unnecessary (wrappers, compat shims, defensive branches hiding impossible states). |
| Verbosity | [`verbose-code-trim`](skills/verbose-code-trim/SKILL.md) | Cut ceremony without touching logic: over-explicit checks, boolean ceremony, passthrough wrappers, comment-code echoes — diff must read like subtraction. |
| Organization | [`repo-organize`](skills/repo-organize/SKILL.md) | Map functional modules, score debt 0-100 per module with independent audits, pay debt worst-first with per-commit regression gates. |
| Agent stack | [`agent-regression`](skills/agent-regression/SKILL.md) | Treat the agent itself as a system under test: manifest every behavior-affecting file (hashed) and runtime knob, replay golden production tasks before/after any model/prompt/skill/tool change, gate on drift — with a runnable manifest tool (`tools/stack_manifest.py`) and golden-case schema. |
| Live processes | [`live-probe`](skills/live-probe/SKILL.md) | Run the REAL code against a REAL live process — imported from the checkout, no mocks — and read every observable: worker fate (heartbeat-growth ground truth), entry fate, the hidden INFO-level log trail, return values. Plus a move-blast-radius scanner: worktree back-pointers, live cwd processes, and the measured cost of full-tree walks before any quarantine/move/delete design ships. Born from a maintainer's live probe catching what our own green fixture suite could not (hermes-agent#132401). |

**How they compose:** `repo-organize` aims the sweep skills
(`dead-code-sweep`, `dedup-sweep`, `verbose-code-trim`) at the worst modules;
every sweep's edits pass through `verification-gates`; `probe-first` turns bug
reports into red proofs before any fix; `live-probe` settles what fixtures
cannot — real processes, real back-pointers — before retention/move designs
ship; `measure-first` backs every performance word; `prose-hygiene` keeps the
words between the code honest.

## Included, credited, integrated

Our CONTRIBUTING rule 1 applies to us first. Where the ecosystem already
built the right idea, these suites include it — adapted, credited in each
skill's frontmatter lineage, and wired into this library's gate battery
rather than left as seven separate installs:

- [obra/superpowers](https://github.com/obra/Superpowers) —
  `verification-before-completion` is the archetype `verification-gates`
  extends (hermes-agent itself adapts obra's TDD/debugging skills).
- [niuma996/code-hygiene-skills](https://github.com/niuma996/code-hygiene-skills) —
  the clone-family detect/decide/execute model behind `dedup-sweep`.
- [danhuaxiansheng/claude-code-cleanup-skills](https://github.com/danhuaxiansheng/claude-code-cleanup-skills) —
  the used-vs-necessary distinction behind `dead-code-sweep`'s two tiers.
- [Asixa/codemap-skill](https://github.com/Asixa/codemap-skill) — the
  module-map/scoring model behind `repo-organize`.
- [jeremylongshore/claude-code-plugins-plus-skills](https://github.com/jeremylongshore/claude-code-plugins-plus-skills) —
  the 11-dimension cleanup taxonomy informing `verbose-code-trim` targets.
- [Pablo-aps/prove-it](https://github.com/Pablo-aps/prove-it),
  [momomuchu/make-no-mistakes](https://github.com/momomuchu/make-no-mistakes),
  [jimtin/production-ai](https://github.com/jimtin/production-ai) — the
  adversarial-verification and enforcement traditions this library sits among
  and composes with (install alongside for hard enforcement machinery).

If a peer does a job better than a suite here, PR the improvement — or PR the
peer credit correction. Both are wanted.

## Installation

Skills follow the open Agent Skills standard (`SKILL.md` + frontmatter):

**Claude Code** (`~/.claude/skills/`):
```bash
git clone https://github.com/MediaPlural/agent-proven ~/.agent-proven
for s in verification-gates probe-first measure-first prose-hygiene \
         dedup-sweep dead-code-sweep verbose-code-trim repo-organize; do
  ln -s ~/.agent-proven/skills/$s ~/.claude/skills/$s
done
```

**OpenAI Codex** (`~/.agents/skills/`) and **Cursor**
(`.cursor/skills/` / `.agents/skills/`): same symlink loop into the
runtime's directory.

**Hermes Agent**: copy to
`~/.hermes/skills/software-development/<name>/` per skill.

## Design principles

- **Evidence over claims.** A gate without a check that can fail is prose.
- **The author never grades the author.** Independent verification is a gate,
  not a courtesy.
- **Delta attribution.** Failures your change didn't cause are environmental —
  proven by baseline, not asserted.
- **Counts are hard assertions.** "Found N issues" is verified by re-counting.
- **Measure or delete the word.** Performance claims carry numbers or get cut.
- **Include, credit, integrate.** The ecosystem's best ideas ship here,
  credited — completeness over purity, attribution over appropriation.

## Contributing

Improvements are the point — see [CONTRIBUTING.md](CONTRIBUTING.md). Two
rules: search-before-write (adapt+credit / extend / fill-a-named-gap) and
evidence-required (every gate change attaches the observed failure it
prevents).

## License

MIT — see [LICENSE](LICENSE).