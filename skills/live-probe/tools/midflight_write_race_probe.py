#!/usr/bin/env python3
"""midflight_write_race_probe.py — does a write landing mid-prune survive?

Born from andrexibiza's independent reproduction on hermes-agent#132401
(the C1/F1 finding): a writer that resumes *while the prune is already
selecting* still loses its work, because the doomed list was snapshotted
before the write landed. Our audit-trail PR records what is deleted — it
must not claim to prevent this race, and this probe keeps that honest.

Method (theirs, packaged): don't infer the race from post-hoc wreckage.
Stage a REAL writer that writes at a controlled moment relative to the
real prune call, and observe which entries survive with fresh content.

  Phase 1 (selection):  aged entry + aged file; the prune is invoked and
                        is IN PROGRESS when...
  Phase 2 (resumption):  ...the writer (cwd OUTSIDE scratch, so the reap
                        never targets it) creates a FRESH write inside a
                        doomed entry — after selection, before deletion.
  Verdict: did the fresh write survive?

On current main it does not (the stale-candidate class, C1/F1): the write
lands after the doomed list is built, and rmtree takes the whole entry
including the just-written file. A coordination/lease fix should flip this
probe GREEN — the same probe proves the fix, red to green.

Usage:
  python midflight_write_race_probe.py --checkout <dir-with-hermes_constants_scratch.py>

Stdlib only; run with an interpreter that has the target module's deps
(psutil) available. Exit 0 always: the report is the payload.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def age(path: Path, hours: float = 30.0) -> None:
    t = time.time() - hours * 3600
    import os

    os.utime(path, (t, t))


def import_scratch_module(checkout: Path):
    src = checkout / "hermes_constants_scratch.py"
    if not src.exists():
        raise SystemExit(f"no hermes_constants_scratch.py under {checkout}")
    spec = importlib.util.spec_from_file_location("race_probe_target", src)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot build import spec for {src}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe the mid-prune write race (C1/F1 class).")
    ap.add_argument("--checkout", required=True, type=Path)
    ap.add_argument("--idle-hours", type=float, default=25.0)
    args = ap.parse_args()

    mod = import_scratch_module(args.checkout)

    base = Path(tempfile.mkdtemp(prefix="midflight-race-probe.", dir=tempfile.gettempdir()))
    root = base / "scratch"
    doomed_entry = root / "selected-lane"
    doomed_entry.mkdir(parents=True)
    (doomed_entry / "old-output.md").write_text("stale content\n", encoding="utf-8")
    age(doomed_entry)
    age(doomed_entry / "old-output.md")
    # A control entry, fresh: must survive, and proves selection ran at all.
    control = root / "control-lane"
    control.mkdir()
    (control / "fresh").write_text("just written\n", encoding="utf-8")

    fresh_path = doomed_entry / "resumed-work.md"

    # A real writer process, cwd OUTSIDE scratch (so the reap never targets
    # it — this isolates the SELECTION race from the reap). It writes a
    # fresh file into the doomed entry when the marker file appears.
    marker = base / "marker.txt"
    writer_code = (
        "import os, sys, time\n"
        "marker, target = sys.argv[1], sys.argv[2]\n"
        "for _ in range(2000):\n"
        "    if os.path.exists(marker):\n"
        "        break\n"
        "    time.sleep(0.005)\n"
        "else:\n"
        "    sys.exit(2)\n"
        "with open(target, 'w', encoding='utf-8') as fh:\n"
        "    fh.write('FRESH RESUMED WORK\\n')\n"
        "sys.exit(0)\n"
    )
    writer = subprocess.Popen(
        [sys.executable, "-c", writer_code, str(marker), str(fresh_path)],
        cwd=str(base),  # outside scratch
    )

    # We cannot hook inside prune_idle_entries, so we approximate the
    # resumption window the way the finding describes it: the doomed list
    # is snapshotted at call time. A write that lands AFTER selection but
    # BEFORE the deletion loop is what dies. To place our write in that
    # window deterministically, we patch rmtree to fire the marker (the
    # deletion loop has started; selection is long done) and wait for the
    # writer to finish BEFORE letting the real rmtree proceed.
    real_rmtree = shutil.rmtree
    fired: list[str] = []

    def rmtree_marker_then_delete(path, *a, **kw):
        if doomed_entry == Path(path):
            marker.write_text("go\n", encoding="utf-8")
            writer.wait(timeout=15)
            fired.append("mid-deletion write completed")
        return real_rmtree(path, *a, **kw)

    mod.shutil.rmtree = rmtree_marker_then_delete

    report: dict = {"checkout": str(args.checkout)}
    try:
        removed = mod.prune_idle_entries(root, args.idle_hours, frozenset())
        report["prune_return"] = removed
    finally:
        mod.shutil.rmtree = real_rmtree

    wr = writer.wait(timeout=5)
    report["writer_exit"] = wr
    report["marker_fired"] = bool(fired)
    report["fresh_write_survived"] = fresh_path.exists()
    report["doomed_entry_exists"] = doomed_entry.exists()
    report["control_survived"] = control.exists()

    print(json.dumps(report, indent=2))
    print("── human read ──")
    if report["fresh_write_survived"]:
        print("VERDICT: fresh mid-prune write SURVIVED — race closed")
    else:
        print("VERDICT: fresh mid-prune write DESTROYED — stale-candidate race present (C1/F1)")
        print("         (the write landed after selection; the deletion loop took the entry anyway)")

    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())