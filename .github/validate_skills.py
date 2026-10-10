#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_skills.py — CI gate for a skills repository.

A skills repo ships no compiled artifact, so its tests are structural: every
SKILL.md must be loadable, and loadable means it carries frontmatter a harness
can parse. A skill with a broken frontmatter is invisible to every agent that
would otherwise use it — the failure is silent at authoring time and total at
use time. That is precisely the class of defect a CI gate exists to catch.

Checks, per SKILL.md:
  1. a `---` frontmatter fence at the very top
  2. a closing fence
  3. parseable key/value frontmatter (PyYAML if present, else a strict fallback)
  4. a non-empty `name`
  5. a non-empty `description`, and one long enough to be a usable trigger
  6. the declared name matches the containing directory
  7. no duplicate skill names across the repo

Stdlib only. Exits non-zero on failure, printing every failure — not just the
first, because a CI that reports one problem per run wastes a run per problem.
"""

from __future__ import annotations

import os
import re
import sys

MIN_DESC_CHARS = 20


def parse_frontmatter(text):
    """Return (dict, error). Uses PyYAML when available, else a strict fallback."""
    if not text.startswith("---"):
        return None, "does not start with a '---' frontmatter fence"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "frontmatter fence is never closed"
    block = text[3:end].strip("\n")
    try:
        import yaml  # noqa: PLC0415 — optional
        data = yaml.safe_load(block)
        if not isinstance(data, dict):
            return None, "frontmatter did not parse to a mapping"
        return data, None
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        return None, "frontmatter is not valid YAML: %s" % exc

    # fallback: require top-level `key: value` lines, allow multi-line scalars
    data, key = {}, None
    for raw in block.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1] not in (" ", "\t") and ":" in raw:
            key, _, val = raw.partition(":")
            key = key.strip()
            data[key] = val.strip()
        elif key and raw[:1] in (" ", "\t", "|", ">"):
            data[key] = (str(data.get(key, "")) + " " + raw.strip()).strip()
    return data, (None if data else "frontmatter has no parseable keys")


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures, checked, seen = [], 0, {}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            if fn != "SKILL.md":
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            checked += 1
            try:
                text = open(path, encoding="utf-8").read()
            except Exception as exc:  # noqa: BLE001
                failures.append("%s: unreadable (%s)" % (rel, exc))
                continue

            data, err = parse_frontmatter(text)
            if err or data is None:
                failures.append("%s: %s" % (rel, err or "frontmatter is empty"))
                continue

            name = str(data.get("name", "")).strip()
            desc = str(data.get("description", "")).strip()
            folder = os.path.basename(dirpath)

            if not name:
                failures.append("%s: frontmatter has no 'name'" % rel)
            elif name != folder:
                failures.append("%s: name '%s' != directory '%s'" % (rel, name, folder))

            if not desc:
                failures.append("%s: frontmatter has no 'description'" % rel)
            elif len(desc) < MIN_DESC_CHARS:
                failures.append("%s: description is %d chars (< %d) — too short to "
                                "be a reliable trigger" % (rel, len(desc), MIN_DESC_CHARS))

            if name:
                if name in seen:
                    failures.append("%s: duplicate skill name '%s' (already at %s)"
                                    % (rel, name, seen[name]))
                else:
                    seen[name] = rel

    print("validate_skills: checked %d SKILL.md file(s) under %s" % (checked, root))
    if not checked:
        print("FAIL: no SKILL.md files found — is this the right directory?")
        return 1
    for f in failures:
        print("FAIL: " + f)
    print("validate_skills: %d failure(s)" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
