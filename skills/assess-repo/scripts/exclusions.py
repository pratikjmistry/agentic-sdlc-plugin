#!/usr/bin/env python3
"""Shared exclusion-set infrastructure used by collect.py and every provider
that needs to know "is this file part of the codebase being analyzed."

Exclusion accounting happens exactly once, before any other counting, per
SKILL.md's Exclusion Handling section — every metric downstream is garbage if
this step is wrong. This module owns that single pass.

LOC estimation strategy (documented so a reviewer can judge the tradeoff):
- Generated-code files are usually a small subset — always read precisely.
- Included (non-excluded) files are the actual point of the analysis — always
  read precisely.
- Other excluded files (vendored/build-output/node_modules/etc.) can be huge
  and are the least interesting bucket to get exactly right — read precisely
  by default, but under `quick=True`, sample a bounded subset and extrapolate,
  recording `confidence: "estimated"` rather than pretending precision.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_EXCLUSIONS_ASSET = Path(__file__).resolve().parent.parent / "assets" / "default-exclusions.txt"
ALWAYS_SKIP_DIRS = {".git", ".svn", ".hg"}
QUICK_SAMPLE_SIZE = 200


@dataclass
class Patterns:
    general: list[str] = field(default_factory=list)   # includes generated patterns too
    generated: list[str] = field(default_factory=list)  # subset tracked separately


def _parse_exclusion_lines(lines: list[str]) -> Patterns:
    general: list[str] = []
    generated: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("generated:"):
            pattern = line[len("generated:"):]
            generated.append(pattern)
            general.append(pattern)
        else:
            general.append(line)
    return Patterns(general=general, generated=generated)


def load_patterns(default_path: Path = DEFAULT_EXCLUSIONS_ASSET, extra_path: Path | None = None) -> Patterns:
    lines = Path(default_path).read_text().splitlines()
    patterns = _parse_exclusion_lines(lines)
    if extra_path is not None and Path(extra_path).exists():
        extra_lines = Path(extra_path).read_text().splitlines()
        extra = _parse_exclusion_lines(extra_lines)
        patterns.general.extend(extra.general)
        patterns.generated.extend(extra.generated)
    return patterns


def _matches_any(relpath: str, patterns: list[str]) -> bool:
    posix_path = relpath.replace("\\", "/")
    return any(fnmatch.fnmatch(posix_path, pat) for pat in patterns)


def classify_path(relpath: str, patterns: Patterns) -> tuple[bool, bool]:
    """Returns (is_excluded, is_generated)."""
    if _matches_any(relpath, patterns.generated):
        return True, True
    if _matches_any(relpath, patterns.general):
        return True, False
    return False, False


def _count_lines(path: Path) -> int:
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return 0
    if b"\x00" in data[:8192]:
        return 0  # looks binary
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


@dataclass
class ClassificationResult:
    included_files: list[str]              # relpaths, POSIX separators
    excluded_file_count: int
    excluded_loc: int
    excluded_loc_confidence: str           # "measured" | "estimated"
    generated_file_count: int
    generated_loc: int


def walk_and_classify(repo_path: Path, patterns: Patterns, quick: bool = False) -> ClassificationResult:
    repo_path = Path(repo_path)
    included: list[str] = []
    other_excluded: list[str] = []
    generated: list[str] = []

    for root, dirnames, filenames in _os_walk_no_vcs(repo_path):
        for name in filenames:
            abspath = Path(root) / name
            relpath = str(abspath.relative_to(repo_path)).replace("\\", "/")
            excluded, is_generated = classify_path(relpath, patterns)
            if is_generated:
                generated.append(relpath)
            elif excluded:
                other_excluded.append(relpath)
            else:
                included.append(relpath)

    generated_loc = sum(_count_lines(repo_path / f) for f in generated)

    if quick and len(other_excluded) > QUICK_SAMPLE_SIZE:
        step = max(1, len(other_excluded) // QUICK_SAMPLE_SIZE)
        sample = other_excluded[::step][:QUICK_SAMPLE_SIZE]
        sample_loc = sum(_count_lines(repo_path / f) for f in sample)
        avg = sample_loc / len(sample) if sample else 0
        excluded_loc = int(avg * len(other_excluded))
        confidence = "estimated"
    else:
        excluded_loc = sum(_count_lines(repo_path / f) for f in other_excluded)
        confidence = "measured"

    return ClassificationResult(
        included_files=included,
        excluded_file_count=len(other_excluded) + len(generated),
        excluded_loc=excluded_loc + generated_loc,
        excluded_loc_confidence=confidence,
        generated_file_count=len(generated),
        generated_loc=generated_loc,
    )


def _os_walk_no_vcs(repo_path: Path):
    import os
    for root, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in ALWAYS_SKIP_DIRS]
        yield root, dirnames, filenames
