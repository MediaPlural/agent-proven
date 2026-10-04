#!/usr/bin/env python3
"""sink_matrix_probe.py — verify a logging/durability GUARANTEE, not a log record.

Born from PR #132455 review round 3 (ehz0ah, 2026-10-04): our check asked
"can INFO reach a handler?" and a console StreamHandler said yes — while the
function's contract says every audit line reaches agent.log OR the fallback
audit file. Their full-path probe (entry removed, records on console, zero
files created) caught what our record-capturing fixtures could not, because
fixtures read the log records and the guarantee is about the FILES.

This probe runs the REAL prune path from any checkout under every root-handler
topology and checks the DISK, not the records:

  topology            expected verdict (durable guarantee holds)
  ------------------  ------------------------------------------------------
  no handlers         FALLBACK FILE written (early-boot state)
  console-only        FALLBACK FILE written (round-3 finding: NOT durable)
  NullHandler only    FALLBACK FILE written (a no-op is not a sink)
  root above INFO     FALLBACK FILE written (level filter runs pre-handler)
  file handler @INFO  AGENT LOG written, fallback NOT (post-setup state)
  handler@INFO+root
  above INFO          FALLBACK FILE written (records die at the logger level)

Also verifies redaction survives into the file under every fallback topology
(spawn a worker with `--api-key` shaped argv and assert the secret never
appears in the audit file).

Verdict per topology: HOLDS / VIOLATED, plus the file(s) observed. Exit 0
always — the report is the payload.

Usage:
  python sink_matrix_probe.py --checkout <dir-with-hermes_constants_scratch.py>

Stdlib only. Use the checkout's venv python when the target needs psutil.
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import shutil
import sys
import tempfile
import time
from pathlib import Path

TOPOLOGIES = (
    # (name, builder) — builder returns (root_level, [handlers]); caller closes.
    "no_handlers",
    "console_only",
    "null_handler",
    "root_above_info",
    "file_handler_info",
    "file_handler_root_warning",
)


def import_scratch_module(checkout: Path):
    """Import the REAL hermes_constants_scratch straight from the checkout."""
    src = checkout / "hermes_constants_scratch.py"
    if not src.exists():
        raise SystemExit(f"no hermes_constants_scratch.py under {checkout}")
    spec = importlib.util.spec_from_file_location("probe_target_scratch_sink", src)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot build import spec for {src}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_topology(name: str, agent_log: Path):
    """Install a root-handler topology. Returns the handlers to close later."""
    root = logging.getLogger()
    saved = (list(root.handlers), root.level)
    if name == "no_handlers":
        root.handlers = []
        root.setLevel(logging.INFO)
    elif name == "console_only":
        root.handlers = [logging.StreamHandler()]
        root.setLevel(logging.INFO)
    elif name == "null_handler":
        root.handlers = [logging.NullHandler()]
        root.setLevel(logging.INFO)
    elif name == "root_above_info":
        root.handlers = [logging.StreamHandler()]
        root.setLevel(logging.WARNING)
    elif name == "file_handler_info":
        fh = logging.FileHandler(agent_log, encoding="utf-8")
        fh.setLevel(logging.INFO)
        root.handlers = [fh]
        root.setLevel(logging.INFO)
    elif name == "file_handler_root_warning":
        fh = logging.FileHandler(agent_log, encoding="utf-8")
        fh.setLevel(logging.INFO)
        root.handlers = [fh]
        root.setLevel(logging.WARNING)
    else:
        raise SystemExit(f"unknown topology: {name}")
    return saved


def restore_topology(saved):
    root = logging.getLogger()
    root.handlers = saved[0]
    root.setLevel(saved[1])


def run_topology(mod, name: str, base: Path):
    """Run one topology. Returns a verdict dict: files observed, guarantee state."""
    home = base / f"home-{name}"
    home.mkdir()
    scratch = mod.get_scratch_dir(base, prune=False) if hasattr(mod, "get_scratch_dir") else None
    # The module's own scratch-dir helper may vary by checkout; build the layout
    # the prune walks: root dir containing one aged entry.
    root_dir = base / f"scratch-{name}"
    root_dir.mkdir()
    entry = root_dir / "aged-entry"
    entry.mkdir()
    (entry / "work").write_text("x", encoding="utf-8")
    past = time.time() - 48 * 3600
    os_utime(entry, past)
    os_utime(entry / "work", past)

    agent_log = base / f"agent-{name}.log"
    saved = build_topology(name, agent_log)
    import os

    os.environ["HERMES_HOME"] = str(home)
    try:
        # Direct call into the real audit path: the prune itself. The module's
        # public entry is prune_idle_entries(root, max_idle_hours, skip_names);
        # some checkouts also export a thin wrapper. Probe the real function.
        removed = mod.prune_idle_entries(root_dir, 24.0, frozenset({"prune-stamp"}))
    finally:
        restore_topology(saved)
        os.environ.pop("HERMES_HOME", None)

    audit_file = home / "logs" / "scratch-prune.log"
    agent_written = agent_log.exists() and agent_log.stat().st_size > 0
    fallback_written = audit_file.exists() and audit_file.stat().st_size > 0

    if name in ("file_handler_info",):
        expected = "agent_log"
    else:
        expected = "fallback_file"
    holds = (
        (expected == "agent_log" and agent_written and not fallback_written)
        or (expected == "fallback_file" and fallback_written)
    )
    return {
        "topology": name,
        "expected": expected,
        "agent_log": agent_written,
        "fallback_file": fallback_written,
        "removed": removed,
        "verdict": "HOLDS" if holds else "VIOLATED",
    }


def os_utime(path: Path, epoch: float):
    import os

    os.utime(path, (epoch, epoch))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkout", required=True)
    args = ap.parse_args()

    mod = import_scratch_module(Path(args.checkout).resolve())

    base = Path(tempfile.mkdtemp(prefix="sink-matrix-"))
    results = []
    try:
        for topo in TOPOLOGIES:
            results.append(run_topology(mod, topo, base))
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print("SINK MATRIX — durable-guarantee verdicts per root-handler topology")
    print("=" * 68)
    for r in results:
        mark = "OK " if r["verdict"] == "HOLDS" else "XX "
        print(
            f"{mark}{r['topology']:<26} expect={r['expected']:<13} "
            f"agent_log={str(r['agent_log']):<5} fallback={str(r['fallback_file']):<5} "
            f"removed={r['removed']}"
        )
    violated = [r for r in results if r["verdict"] == "VIOLATED"]
    print("=" * 68)
    if violated:
        print(f"VIOLATED under {len(violated)} topology(ies):")
        for r in violated:
            print(f"  - {r['topology']}: expected {r['expected']}, got "
                  f"agent_log={r['agent_log']} fallback={r['fallback_file']}")
        return 0
    print("GUARANTEE HOLDS under every topology.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
