---
name: hermes-cron-stuck-job-recovery
description: "Kill a wedged hermes cron run; no cancel verb exists."
version: 0.1.0
author: Justin Sharpe (justinsharpe), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cron, process-kill, process-groups, scheduler, incidents, timeouts]
    related_skills: [verification-gates, live-probe]
---

# Hermes Cron Stuck-Job Recovery

`hermes cron` has no cancel/kill/abort verb, and its other safety rails have
sharp edges an operator meets only at 3 a.m. This skill is the packaged
procedure for stopping a wedged cron run safely — and for the root-cause
check that must follow, because the scheduler is usually not the thing that
broke.

## When to Use

- A `hermes cron` job (especially a no-agent script-mode job) has been
  running far past its expected duration and needs to be stopped now.
- A gateway restart did not clear a wedged nightly job and it is still
  burning its full timeout window, night after night.
- `hermes cron doctor` is flagging N-failures-in-a-row on a job and the
  temptation is to keep killing it instead of reading why it wedges.
- Before touching process trees: confirming which PID actually belongs to
  the job (vs. the gateway or a bash wrapper).

## The Verb Map (read this first)

`hermes cron` verbs are: `list`, `create`/`add`, `edit`, `pause`, `resume`,
`run`, `remove`/`rm`/`delete`, `status`, `runs`/`history`, `incidents`,
`notepad`, `doctor`, `tick`.

Two facts that surprise operators:

- **There is no cancel/kill/abort verb.** Stopping an in-flight run is a
  manual process-group kill (below) or waiting out the scheduler's own
  timeout.
- **`pause` only stops future fires.** It does nothing to a run already in
  flight — pausing a wedged job leaves the current run burning.
- **A gateway restart does not save you.** The restart's drain will not
  auto-exclude a long script job within its wedge-allowance window
  (observed: 48h), so a wedged nightly script can survive a restart
  untouched.

## What You Are Actually Killing

A no-agent script-mode cron job runs as a REAL subprocess tree — a bash
wrapper spawning child processes — in its own process group under the
gateway PID. It is not a thread you can cancel; it is a process tree you
must signal.

Confirm before touching anything:

```bash
ps -eo pid,ppid,pgid,etime,stat,command | grep -i <job-name>
pgrep -P <script_pid>          # enumerate the children you are about to kill
```

## Kill Procedure

1. **Identify the SCRIPT's own PID** — not the gateway PID, not the bash
   wrapper's parent. `ps -eo pid,ppid,pgid,etime,stat,command` with the
   job name is the ground truth.
2. **`kill -TERM -PGID`** — the negative PID targets the whole process
   group, so children die too. Signaling only the script PID leaves
   orphans.
3. **Wait a few seconds; `kill -KILL -PGID` only if TERM is ignored.**
4. **Know the fallback:** the scheduler's own `HERMES_CRON_TIMEOUT`
   (default 3600s) will eventually SIGTERM the group on its own — a manual
   kill only shortcuts the wait.
5. **Close the record:** afterward, `hermes cron incidents` shows the run
   as timeout or exit -15; once root-caused, `hermes cron incidents ack
   INCIDENT_ID` clears it.

## Root-Cause Check (the actual point)

`hermes cron doctor` flags N-failures-in-a-row — that is the signal to find
root cause, not to keep killing the nightly.

Real incident (2026-10-04): a no-agent script hardcoded a local LLM model
name (`MNEMOSYNE_LLM_MODEL` pointed at a local ollama); the model was
rotated out of ollama, so every nightly run retried a dead model for the
full 3600s timeout — three nights running. The scheduler was fine; the
job's dependency had rotted.

**Before assuming the scheduler is broken, check hardcoded model and
dependency names against what is actually installed.** A job that
references a rotated-out model, a renamed binary, or a moved path will
wedge on every fire, forever, and no amount of killing fixes it.

## Method Rules

- **Never signal the gateway PID** — kill the job's process group, and only
  after `ps`/`pgrep` confirm which PIDs belong to the job.
- **TERM before KILL** — give the tree a few seconds to clean up; KILL is
  the escalation, not the opener.
- **A count of wedged nights is a diagnostic, not a badge** — two nights
  of the same wedge means the job's environment drifted; check the
  dependency before blaming `hermes cron` itself.
- **Verify the kill took** — re-run the `ps` command after signaling;
  don't trust the shell's exit code alone.

## Provenance

Born from a live incident (2026-10-04): a three-night wedged-cron
investigation where the scheduler was innocent, the hardcoded model name
was guilty, and the kill procedure had to be discovered from first
principles because no cancel verb exists.