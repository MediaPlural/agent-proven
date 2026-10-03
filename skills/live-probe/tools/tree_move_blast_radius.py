#!/usr/bin/env python3
"""tree_move_blast_radius.py — what breaks if this tree moves or dies?

Born from the #132401 fix review: a quarantine MOVE breaks a hosted linked
worktree (the <repo>/.git/worktrees/<n>/gitdir back-pointer still names the
OLD path, so git inside the moved tree is dead and `git worktree prune` drops
the registration later anyway), and full-tree bytes walks have a real boot
cost when run just to log a line. This scanner prices the blast radius
BEFORE any move/quarantine/delete design ships:

  1. Linked-worktree registrations under the tree — .git files resolved to
     their back-pointers, with a move-breaks verdict per registration.
  2. Plain repos (.git dirs) — self-contained; move-safe, but listed.
  3. Live processes cwd'd inside — psutil lane; skipped with a note when
     psutil is unavailable (stdlib-only law).
  4. Bytes + the measured cost of walking the tree — so "cheap log line"
     claims about doomed trees get honest numbers.

Usage:
  python tree_move_blast_radius.py --path <dir> [--path <dir> ...]

Stdlib only. Exit 0 always: the report is the payload.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


def scan_git(root: Path) -> tuple[list[dict], int]:
    """Linked-worktree registrations and plain repos under *root*."""
    findings: list[dict] = []
    walked = 0
    for dirpath, dirnames, filenames in os.walk(root):
        walked += 1
        if ".git" in dirnames:
            findings.append({"kind": "plain-repo", "git": str(Path(dirpath) / ".git"),
                             "move_safe": True})
            dirnames.remove(".git")  # do not descend into repo internals
        elif ".git" in filenames:
            rec: dict = {"kind": "linked-worktree", "git_file": str(Path(dirpath) / ".git")}
            try:
                first = (Path(dirpath) / ".git").read_text(encoding="utf-8", errors="replace").strip()
                gitdir = first.split("gitdir:", 1)[1].strip() if "gitdir:" in first else ""
                rec["gitdir_target"] = gitdir
                back = Path(gitdir) / "gitdir"
                if back.exists():
                    rec["back_pointer"] = back.read_text(encoding="utf-8", errors="replace").strip()
                    # The back-pointer names where the worktree lives; if that is
                    # inside the scanned tree, MOVING the tree orphans it.
                    # The back-pointer names the worktree's .git file path; if that
                    # path lives under the scanned tree, moving the tree orphans it.
                    rec["move_breaks_registration"] = rec["back_pointer"].startswith(str(root) + os.sep)
                    rec["move_safe"] = not rec["move_breaks_registration"]
                else:
                    rec["move_breaks_registration"] = True
                    rec["move_safe"] = False
                    rec["note"] = "gitdir target has no back-pointer file"
            except OSError as exc:
                rec["error"] = f"{type(exc).__name__}: {exc}"
                rec["move_safe"] = False
            findings.append(rec)
    return findings, walked


def scan_processes(root: Path) -> tuple[list[dict], str | None]:
    """Live same-host processes cwd'd under *root* (psutil lane, optional)."""
    try:
        import psutil  # noqa: PLC0415 — optional lane by design
    except ImportError:
        return [], "psutil unavailable — process lane skipped (stdlib-only law)"
    hits: list[dict] = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            cwd = p.cwd()
        except Exception:  # noqa: BLE001 — races and permissions are normal here
            continue
        if cwd == str(root) or cwd.startswith(str(root) + os.sep):
            hits.append({"pid": p.pid, "name": p.info.get("name"), "cwd": cwd})
    return hits, None


def tree_cost(root: Path) -> dict:
    """Total bytes and the measured wall-time of the walk itself."""
    t0 = time.monotonic()
    files = 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for f in filenames:
            try:
                total += (Path(dirpath) / f).stat().st_size
                files += 1
            except OSError:
                continue
    return {"files": files, "bytes": total, "mb": round(total / 1e6, 2),
            "walk_seconds": round(time.monotonic() - t0, 3)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Price the blast radius of moving/deleting a tree.")
    ap.add_argument("--path", required=True, type=Path, action="append")
    args = ap.parse_args()

    report: dict = {"paths": {}}
    for p in args.path:
        p = p.resolve()
        if not p.is_dir():
            report["paths"][str(p)] = {"error": "not a directory"}
            continue
        git, walked = scan_git(p)
        procs, note = scan_processes(p)
        report["paths"][str(p)] = {
            "git_findings": git,
            "live_cwd_processes": procs,
            "process_lane_note": note,
            "tree_cost": tree_cost(p),
            "dirs_walked": walked,
        }

    print(json.dumps(report, indent=2))
    print("── human read ──")
    for p, r in report["paths"].items():
        if "error" in r:
            print(f"{p}: {r['error']}")
            continue
        wt = [g for g in r["git_findings"] if g["kind"] == "linked-worktree"]
        broken = [g for g in wt if g.get("move_breaks_registration")]
        procs = r["live_cwd_processes"]
        cost = r["tree_cost"]
        print(f"{p}:")
        print(f"  worktrees: {len(wt)} ({len(broken)} break on move) | "
              f"live cwd processes: {len(procs)} | "
              f"size: {cost['mb']} MB in {cost['files']} files, walk {cost['walk_seconds']}s")
        if r.get("process_lane_note"):
            print(f"  note: {r['process_lane_note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())