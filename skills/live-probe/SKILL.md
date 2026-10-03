---
name: live-probe
description: "Run the real code against real live processes — the capability fixtures lack."
version: 1.0.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [probes, live-processes, blast-radius, retention, deletion, move-safety]
    related_skills: [probe-first, verification-gates, coding-agent-quality-gates]
---

# Live Probe

Simulated-fixture tests share the author's mental model of the system. Live
processes share none. This suite is the packaged capability that settles
what fixtures cannot: run the REAL target code (imported straight from a
checkout, no install, no mock) against a REAL process doing REAL work, and
read every observable the code leaves behind.

Born from upstream hermes-agent issue #132401 (2026-10-03): a maintainer's
30-second live probe — a real worker (parent alive, computing, not writing)
cwd'd inside an aged scratch entry, then the real prune call — caught what
our own 24/24 fixture test suite could not: the fix's quarantine move did
not stop the reap path from killing the live worker. The test battery was
green; the truth required a live process.

## When to Use

- Retention/deletion/reaping code paths (pruners, garbage collectors,
  cleanup loops, watchdogs) — anything whose blast radius includes
  *processes and registrations*, not just files.
- Move/rename designs (quarantines, trash, migration) — a move breaks
  external back-pointers that no in-process fixture holds.
- Any code whose failure mode is invisible to its own tests: silent sweeps,
  cleanup paths, "the log line nobody sees" failures.
- Verifying a maintainer's/reviewer's live-probe claim before replying
  (trust-but-verify, with the same weapon class).

Don't use for: pure-function logic, fixture-testable behavior, or when a
red proof already exists in the suite (that's `probe-first`'s lane).

## The Two Probes

### 1. `tools/live_prune_probe.py` — the real prune vs. a real worker

Runs the target module's own `prune_idle_entries` (imported from a checkout
via `importlib`) against a scratch root containing an aged entry with a
LIVE worker cwd'd inside (a real child process: parent alive, computing,
never writing to the tree — the exact profile that distinguishes a live
worker from an orphan). Reports every observable:

- **worker fate** — alive / reaped, via heartbeat-growth ground truth
  (a heartbeat FILE outlives a process, and the reaper consumes Popen's
  exit status by waiting in-process; only heartbeat GROWTH across a
  measured window is truth, on every platform)
- **entry fate** — in-root / quarantined / deleted
- **the log trail** — every captured record at INFO+, including the ones
  the default WARNING root logger hides (where the "reaped N" line lives)
- **departure log** — `<root>/../scratch-prune.log` lines, when the code
  writes them
- **return value** — exactly what the real boot caller would see

```bash
python tools/live_prune_probe.py --checkout <dir-with-target-module> [--idle-hours 25] [--keep-marker]
```

Run on the unfixed base first (RED), then the candidate fix (truth), then
any opt-out contract (`--keep-marker`).

### 2. `tools/tree_move_blast_radius.py` — what breaks if this tree moves?

Prices the blast radius of any move/quarantine/delete design BEFORE it
ships:

- linked-worktree registrations with a move-breaks verdict per
  registration (the `.git` file's `gitdir:` back-pointer names the OLD
  path — moving the tree orphans it, and `git worktree prune` drops it
  later anyway)
- plain repos (move-safe, listed)
- live processes cwd'd inside (psutil lane, skipped with a note when
  unavailable — stdlib-only law)
- total bytes and the measured cost of walking the tree — so "cheap log
  line" claims about doomed trees get honest numbers

```bash
python tools/tree_move_blast_radius.py --path <dir> [--path <dir> ...]
```

### 3. `tools/midflight_write_race_probe.py` — does a write landing mid-prune survive?

The concurrency-gap method (andrexibiza's C1/F1 reproduction on #132401,
packaged): stage a REAL writer that fires at a controlled moment relative
to the REAL prune call — cwd outside scratch (so the reap never targets
it), writing fresh content into a doomed entry AFTER selection, BEFORE
deletion. Observe: did the fresh write survive?

- RED on current main and on any logging-only patch: the doomed list is
  snapshotted at call time, so the deletion loop takes the entry — fresh
  work included. This is why an audit PR must never claim race closure.
- GREEN when a coordination/lease fix lands: same probe proves the fix,
  red to green.

```bash
python tools/midflight_write_race_probe.py --checkout <dir-with-target-module>
```

## Procedure

1. **State the claim to falsify** — one sentence: "the reap path kills a
   live worker before the quarantine move."
2. **Run the probe on the unfixed base — capture RED.** The live
   process makes the failure real, not theoretical.
3. **Run it on the candidate fix — read the truth, whatever it is.**
   (This is how we found our own fix still reaped the worker: fixtures
   green, live probe red.)
4. **Price the blast radius of the design itself** with the scanner
   before proposing moves/quarantines/deletes.
5. **Keep the outputs** — attach both runs (base + fix) and the scanner
   report to the task record; the probe file lives here as the reusable
   artifact.

## The Method Rules (hard-won)

- **Live-process ground truth is heartbeat growth, not file existence, not
  Popen.poll().** The reaper waits on the child in-process, consuming the
  exit status (poll stays None forever on a reaped worker); the heartbeat
  file outlives the process. Growth across a measured window is the only
  cross-platform truth. `os.kill(pid, 0)` is a Windows trap (it TERMINATES
  the process on win32) — do not use it as a liveness check.
- **A count is an audit receipt only if it claims confirmed removals.**
  `rmtree(ignore_errors=True)` swallows failures — increment a removal
  count only after the entry is confirmed gone, and record `residue` /
  `failed` states explicitly (andrexibiza's C2 on #132401: "do not turn
  the current integer into an audit receipt without fixing its meaning" —
  caught a real over-report our own review round had passed).
- **Reproduce the concurrency window, don't infer it from wreckage.** A
  mid-prune resumption race is proven by staging a controlled write at a
  controlled moment relative to the real call (midflight probe above) —
  post-hot forensics cannot distinguish "raced" from "already stale".
- **Fixtures prove intent; live probes prove behavior.** A green fixture
  suite on retention code means the author's model of the reap was wrong,
  not that the code is right. Run both: fixtures for regressions, live
  probes for truth.
- **Import the REAL module from the checkout** (`importlib` from file
  location) — no install, no mocks, no reimplementation drift. The probe
  must run the code that will ship, including its logging side effects.
- **Read the code's own log trail at INFO+** — the failure this suite
  exists for was invisible partly because the only record lived at INFO
  under a WARNING root logger. Capture records, don't grep the console.
- **Verify the sink, not just the call.** An INFO call proves nothing
  until you confirm it reaches the intended file on every boot path —
  early-boot prunes can fire before the file handler installs (verified
  on our own install: the prune records never appear in `agent.log`).
- **Moves break back-pointers** — `.git` files, `.pid` files, state files,
  any external path reference. Scan before designing any move.
- **Price the walk before logging it** — full-tree byte walks have real
  cost at boot (a 343 MB worktree priced 0.5s here); measure before
  claiming "cheap."
- **Platform-agnostic by law:** stdlib only (psutil optional and
  explicitly skipped with a note), no `os.kill(0)` liveness, no
  POSIX-only constructs in the probe path, CRLF/O_BINARY class traps
  absent by construction. Run on macOS/Linux/Windows or state the gap.

## Verification

**Runnable check (per probe run):**

```bash
python tools/live_prune_probe.py --checkout <base>    # expect: worker reaped, entry deleted (RED baseline)
python tools/live_prune_probe.py --checkout <fix>     # expect: read the truth — every claim verified
python tools/tree_move_blast_radius.py --path <dir>   # expect: registrations + processes + bytes priced
```

**Evidence to capture:** both probe runs' human-read verdicts, the JSON
report of each, the scanner report for any move design, and the claim
sentence each probe falsifies or confirms.

**Provenance:** born from NousResearch/hermes-agent#132401 (teknium1's
live triage probe, 2026-10-03) — the maintainer's probe methodology is the
capability this suite packages, with credit where the idea came from.