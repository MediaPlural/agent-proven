#!/usr/bin/env python3
"""stack_manifest.py — capture everything that affects agent behavior.

The manifest layer of the agent-regression suite: a stack "version" is more
than the model name. Hash the files that shape behavior (prompts, SOUL,
skills, tool schemas, config), record the runtime knobs (model, provider,
backend revision, timeouts, seed), and emit one JSON manifest whose digest
changes exactly when behavior-affecting state changes.

Usage:
    python3 tools/stack_manifest.py --root <agent-config-root> \
        --model <name> --provider <name> --out manifest.json

Exit 0 always (a manifest is a recording, not a verdict); validity is in the
digest diff between two manifests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# Behavior-affecting file families. Keys are family names; values are glob
# patterns relative to --root. Extend per-runtime as needed.
DEFAULT_FAMILIES: dict[str, list[str]] = {
    "prompts": ["prompts/**/*", "*.md", "SOUL.md"],
    "skills": ["skills/**/SKILL.md", "skills/**/*.md"],
    "tools": ["tools/**/*.json", "mcp*.json", ".mcp.json"],
    "config": ["config.yaml", "config.json", "*.toml"],
}

EXCLUDE_NAMES = {"__pycache__", ".git", "node_modules", ".venv", "__MACOSX"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def family_digest(paths: list[Path]) -> str:
    """Order-independent digest over a file family (sorted relpath:hash)."""
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: str(x).lower()):
        rel = str(p).replace(os.sep, "/").lower()
        h.update(f"{rel}:{sha256_file(p)}\n".encode())
    return h.hexdigest()


def collect(root: Path, patterns: list[str]) -> list[Path]:
    out: set[Path] = set()
    for pat in patterns:
        for p in root.glob(pat):
            if not p.is_file():
                continue
            if any(part in EXCLUDE_NAMES for part in p.parts):
                continue
            out.add(p)
    return sorted(out)


def build_manifest(args: argparse.Namespace) -> dict:
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: root not a directory: {root}", file=sys.stderr)
        sys.exit(2)

    families: dict[str, dict] = {}
    all_files: list[Path] = []
    for name, patterns in DEFAULT_FAMILIES.items():
        files = collect(root, patterns)
        all_files.extend(files)
        families[name] = {
            "files": [str(p.relative_to(root)) for p in files],
            "digest": family_digest(files),
        }

    manifest = {
        "schema": "agent-regression.stack-manifest/1",
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runtime": {
            "model": args.model,
            "provider": args.provider,
            "harness_revision": args.harness_revision or os.environ.get("HARMANIFEST_HARNESS", "unknown"),
            "seed": args.seed,
        },
        "families": families,
    }

    # Manifest digest: every family digest + runtime knobs. The point:
    # touching any behavior-affecting file (or changing any knob) changes it.
    digest_input = json.dumps(
        {k: v["digest"] for k, v in sorted(families.items())}
        | {"runtime": manifest["runtime"]},
        sort_keys=True,
    )
    manifest["manifest_digest"] = hashlib.sha256(
        digest_input.encode()
    ).hexdigest()
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Capture everything that affects agent behavior."
    )
    ap.add_argument("--root", required=True, help="agent config root")
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", required=True)
    ap.add_argument("--harness-revision", default=None)
    ap.add_argument("--seed", default="0")
    ap.add_argument("--out", type=Path, default=Path("stack-manifest.json"))
    args = ap.parse_args()

    manifest = build_manifest(args)
    args.out.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"manifest: {args.out}")
    print(f"manifest_digest: {manifest['manifest_digest']}")
    print(f"families: " + ", ".join(
        f"{k}({len(v['files'])})" for k, v in manifest["families"].items()
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())