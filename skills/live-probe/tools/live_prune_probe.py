#!/usr/bin/env python3
"""live_prune_probe.py — run the REAL scratch-prune code against a REAL live worker.

Born from the #132401 maintainer triage (teknium1): a 30-second live probe — a
real, non-orphan worker (parent alive, computing, not writing) cwd'd inside an
aged scratch entry, then the real prune call — caught what our 24/24 test suite
could not: the reap path still TERMs the live worker before the quarantine
move. Simulated-fixture tests share the author's mental model; a live process
shares none. This probe is that capability, packaged.

Per run it reports every observable:
  * worker fate    — alive / exit code (POSIX: -15 SIGTERM, -9 SIGKILL)
  * entry fate     — in-root / quarantined / deleted
  * logging trail  — records captured at INFO+, including the ones the default
                     WARNING root logger hides (the "reaped N" line lives there)
  * departure log  — <root>/../scratch-prune.log lines, when the code writes them
  * quarantine dir — created or not (differentiates fix vs main instantly)
  * return value   — exactly what the real caller would see

Usage:
  python live_prune_probe.py --checkout <repo-with-hermes_constants_scratch.py> \
      [--idle-hours 25] [--keep-marker]

Stdlib only. Run with an interpreter that can import the TARGET module's own
deps (e.g. the checkout's venv python, for psutil). Exit 0 always: the report
is the payload, not a pass/fail bit — the verdict is yours to read.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WORKER_CODE = (
    "import os, time\n"
    "hb = os.environ['PROBE_HEARTBEAT']\n"
    "with open(hb, 'a', encoding='utf-8') as fh:\n"
    "    while True:\n"
    "        fh.write('1')\n"
    "        fh.flush()\n"
    "        time.sleep(0.2)\n"
)
QUARANTINE_SUFFIX = "-quarantine"


class _Capture(logging.Handler):
    """Collect every log record at INFO+ so invisible-by-default lines are seen."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.records: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(
            {"level": record.levelname, "name": record.name, "msg": record.getMessage()}
        )


def age(path: Path, hours: float) -> None:
    """Push an mtime back in time — the 25-hour idle wait, compressed to a stat call."""
    t = time.time() - hours * 3600
    os.utime(path, (t, t))


def import_scratch_module(checkout: Path):
    """Import the REAL hermes_constants_scratch straight from the checkout, no install."""
    import importlib.util

    src = checkout / "hermes_constants_scratch.py"
    if not src.exists():
        raise SystemExit(f"no hermes_constants_scratch.py under {checkout}")
    spec = importlib.util.spec_from_file_location("probe_target_scratch", src)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot build import spec for {src}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def worker_alive(heartbeat: Path) -> bool:
    """Ground truth: a live worker appends every 0.2s — measure growth across a
    0.6s window. The heartbeat file lives OUTSIDE the doomed tree, so neither
    the reap nor the rmtree can hide it, and file existence alone is not
    evidence (files outlive processes); growth is."""
    try:
        before = heartbeat.stat().st_size
    except OSError:
        return False  # no file: the worker never started
    time.sleep(0.6)
    try:
        return heartbeat.stat().st_size > before
    except OSError:
        return False


def entry_fate(root: Path, name: str) -> str:
    if (root / name).exists():
        return "in-root"
    quarantine = root.parent / (root.name + QUARANTINE_SUFFIX)
    if quarantine.exists():
        for p in quarantine.iterdir():
            if p.name.split(".prior-")[0] == name:
                return "quarantined"
    return "deleted"


def main() -> int:
    ap = argparse.ArgumentParser(description="Live-probe the real prune against a real worker.")
    ap.add_argument("--checkout", required=True, type=Path)
    ap.add_argument("--idle-hours", type=float, default=25.0)
    ap.add_argument("--keep-marker", action="store_true",
                    help="drop a .scratch-keep in the entry (the fix's opt-out contract)")
    ap.add_argument("--wait-seconds", type=float, default=10.0,
                    help="max wait for worker fate (reap grace is TERM then up to 3s then KILL)")
    args = ap.parse_args()

    cap = _Capture()
    logging.getLogger().addHandler(cap)
    logging.getLogger().setLevel(logging.INFO)

    scratch = Path.home() / ".hermes" / "cache" / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="live-prune-probe.", dir=str(scratch)))
    root = base / "scratch"
    entry = root / "lane-parked-work"
    entry.mkdir(parents=True)
    (entry / "deliverable.md").write_text("multi-day work product\n", encoding="utf-8")
    age(entry, args.idle_hours)
    age(entry / "deliverable.md", args.idle_hours)
    if args.keep_marker:
        (entry / ".scratch-keep").write_text("parked\n", encoding="utf-8")
        age(entry / ".scratch-keep", args.idle_hours)

    report: dict = {
        "checkout": str(args.checkout),
        "idle_hours": args.idle_hours,
        "keep_marker": args.keep_marker,
    }

    # A REAL worker: parent alive (this probe), computing, never writing.
    # Heartbeat file lives OUTSIDE the entry under test — the reap kills the
    # process, and the reaper waits on the child in-process, consuming the
    # exit status Popen.poll() would see; the heartbeat is ground truth.
    heartbeat = root.parent / "probe-heartbeat.txt"
    heartbeat.unlink(missing_ok=True)
    env = dict(os.environ, PROBE_HEARTBEAT=str(heartbeat))
    worker = subprocess.Popen([sys.executable, "-c", WORKER_CODE], cwd=str(entry), env=env)
    report["worker_pid"] = worker.pid
    time.sleep(0.5)  # let it settle into its cwd and write its first beat

    try:
        mod = import_scratch_module(args.checkout)
        ret = mod.prune_idle_entries(root, args.idle_hours, frozenset())
        report["prune_return"] = ret
    except Exception as exc:  # noqa: BLE001 — the probe reports, it never hides
        report["probe_error"] = f"{type(exc).__name__}: {exc}"
        ret = None

    # The reaper waits on the child in-process, consuming Popen's exit status
    # (poll() stays None forever on a reaped worker) — heartbeat growth is the
    # only ground truth, on every platform. The TERM→grace→KILL all happens
    # synchronously inside the prune call, so a short settle suffices.
    time.sleep(0.8)
    alive = worker_alive(heartbeat)
    report["worker_fate"] = "alive" if alive else "reaped"
    report["entry_fate"] = entry_fate(root, entry.name)
    report["quarantine_dir_created"] = (root.parent / (root.name + QUARANTINE_SUFFIX)).exists()
    dep_log = root.parent / "scratch-prune.log"
    report["departure_log"] = dep_log.read_text(encoding="utf-8").splitlines() if dep_log.exists() else []
    report["log_records"] = cap.records

    print(json.dumps(report, indent=2))
    print("── human read ──")
    print(f"worker: {report['worker_fate']} | entry: {report['entry_fate']} | "
          f"return: {ret} | quarantine-dir: {report['quarantine_dir_created']}")

    if alive:
        worker.terminate()
        try:
            worker.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait(timeout=3)
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())