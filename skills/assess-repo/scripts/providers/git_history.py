#!/usr/bin/env python3
"""Layer 1 provider: git history metrics (the `vcs.*` metric family).

Pure stdlib, no network. Shells out to the system `git` binary only. If the
target isn't a git repository at all, every `vcs.*` metric is returned as
`unavailable` rather than raising — a non-git local folder is an explicitly
supported degrade path (see the `--quick`-style graceful-degradation
constraint in SKILL.md).

Public entry points:
    probe_target_info(repo_path) -> dict     # for the `target` section of assessment-inputs.json
    collect(repo_path, quick=False) -> dict  # the 13 `vcs.*` metric envelopes

Determinism note: several of these metrics (commits_last_90d/365d,
active_authors_last_90d, stale_branch_count) are computed relative to wall-clock
run time, not just the checked-out commit. Re-running against the same commit
on a different calendar date can legitimately change these values — that is
expected of a VCS metric, not a bug, and is recorded in each metric's `notes`.
This is unrelated to score.py's determinism contract, which concerns score.py
being a pure function of a fixed assessment-inputs.json + rubric.yaml.
"""
from __future__ import annotations

import math
import re
import subprocess
import time
from pathlib import Path

RS = "\x1e"  # record separator
FS = "\x1f"  # field separator

STALE_BRANCH_DAYS = 90
RECENT_WINDOW_DAYS = (90, 365)
ISSUE_REF_PATTERN = re.compile(r"(#\d+)|([A-Z][A-Z0-9]{1,9}-\d+)")

SHALLOW_AFFECTED_METRICS = {
    "history_days", "commits_last_90d", "commits_last_365d", "active_authors_last_90d",
    "total_authors", "author_concentration_gini", "single_author_file_pct",
    "merge_commit_ratio", "commit_msg_issue_ref_pct", "hotspots",
}


def _run(repo: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, errors="replace",
    )


def _ok(cp: subprocess.CompletedProcess) -> bool:
    return cp.returncode == 0


def is_git_repo(repo_path: Path) -> bool:
    cp = _run(repo_path, ["rev-parse", "--is-inside-work-tree"])
    return _ok(cp) and cp.stdout.strip() == "true"


def _resolved_commit(repo_path: Path) -> str:
    cp = _run(repo_path, ["rev-parse", "HEAD"])
    return cp.stdout.strip() if _ok(cp) else ""


def _is_shallow(repo_path: Path) -> bool:
    cp = _run(repo_path, ["rev-parse", "--is-shallow-repository"])
    return _ok(cp) and cp.stdout.strip() == "true"


def _default_branch(repo_path: Path) -> str:
    cp = _run(repo_path, ["symbolic-ref", "refs/remotes/origin/HEAD"])
    if _ok(cp) and cp.stdout.strip():
        return cp.stdout.strip().rsplit("/", 1)[-1]
    cp = _run(repo_path, ["branch", "--show-current"])
    if _ok(cp) and cp.stdout.strip():
        return cp.stdout.strip()
    return ""


def probe_target_info(repo_path: Path) -> dict:
    """Facts needed for assessment-inputs.json's `target` section."""
    if not is_git_repo(repo_path):
        return {
            "resolved_commit": "", "default_branch": "", "history_complete": False,
        }
    return {
        "resolved_commit": _resolved_commit(repo_path),
        "default_branch": _default_branch(repo_path),
        "history_complete": not _is_shallow(repo_path),
    }


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {
        "value": value, "unit": unit, "source": source,
        "confidence": confidence, "coverage_pct": coverage_pct, "notes": notes,
    }


def _unavailable(notes: str) -> dict:
    return _envelope(None, "", "", "unavailable", None, notes)


def _head_file_set(repo_path: Path) -> set[str]:
    cp = _run(repo_path, ["ls-tree", "-r", "--name-only", "HEAD"])
    if not _ok(cp):
        return set()
    return {line for line in cp.stdout.splitlines() if line}


def _count_lines(path: Path) -> int:
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return 0
    if b"\x00" in data[:8192]:
        return 0  # looks binary, don't count
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def _gini(counts: list[int]) -> float:
    n = len(counts)
    if n == 0:
        return 0.0
    total = sum(counts)
    if total == 0:
        return 0.0
    ordered = sorted(counts)
    weighted_sum = sum((i + 1) * c for i, c in enumerate(ordered))
    return round((2 * weighted_sum) / (n * total) - (n + 1) / n, 4)


def _parse_log(repo_path: Path) -> dict:
    """One full traversal of history from HEAD. Builds every per-commit and
    per-file aggregate the vcs.* family needs, in a single git invocation."""
    fmt = f"{RS}%H{FS}%an{FS}%at{FS}%P{FS}%s"
    cp = _run(repo_path, ["log", "--name-only", f"--format={fmt}", "HEAD"])

    now = time.time()
    cutoffs = {days: now - days * 86400 for days in RECENT_WINDOW_DAYS}

    total_commits = 0
    merge_commits = 0
    issue_ref_commits = 0
    author_counts: dict[str, int] = {}
    active_authors: dict[int, set[str]] = {days: set() for days in RECENT_WINDOW_DAYS}
    commits_in_window: dict[int, int] = {days: 0 for days in RECENT_WINDOW_DAYS}
    file_authors: dict[str, set[str]] = {}
    file_commits_365d: dict[str, int] = {}
    min_ts, max_ts = None, None

    raw = cp.stdout if _ok(cp) else ""
    for record in raw.split(RS):
        record = record.strip("\n")
        if not record:
            continue
        lines = record.split("\n")
        header = lines[0]
        parts = header.split(FS)
        if len(parts) < 5:
            continue
        _commit_hash, author, at_str, parents, subject = parts[0], parts[1], parts[2], parts[3], FS.join(parts[4:])
        try:
            at = int(at_str)
        except ValueError:
            continue

        total_commits += 1
        author_counts[author] = author_counts.get(author, 0) + 1
        min_ts = at if min_ts is None else min(min_ts, at)
        max_ts = at if max_ts is None else max(max_ts, at)

        if len(parents.split()) > 1:
            merge_commits += 1
        if ISSUE_REF_PATTERN.search(subject):
            issue_ref_commits += 1

        for days, cutoff in cutoffs.items():
            if at >= cutoff:
                commits_in_window[days] += 1
                active_authors[days].add(author)

        touched_files = [ln for ln in lines[1:] if ln.strip()]
        is_recent_365 = at >= cutoffs[365]
        for f in touched_files:
            file_authors.setdefault(f, set()).add(author)
            if is_recent_365:
                file_commits_365d[f] = file_commits_365d.get(f, 0) + 1

    return {
        "total_commits": total_commits,
        "merge_commits": merge_commits,
        "issue_ref_commits": issue_ref_commits,
        "author_counts": author_counts,
        "active_authors": active_authors,
        "commits_in_window": commits_in_window,
        "file_authors": file_authors,
        "file_commits_365d": file_commits_365d,
        "min_ts": min_ts,
        "max_ts": max_ts,
    }


def _branch_facts(repo_path: Path) -> dict:
    cp = _run(repo_path, [
        "for-each-ref", "--format=%(refname) %(committerdate:unix)",
        "refs/heads", "refs/remotes",
    ])
    if not _ok(cp):
        return {"branch_count": 0, "stale_branch_count": 0}

    now = time.time()
    stale_cutoff = now - STALE_BRANCH_DAYS * 86400
    branches = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line or line.endswith("/HEAD"):
            continue
        try:
            ref, ts = line.rsplit(" ", 1)
            branches.append(int(ts))
        except ValueError:
            continue

    stale = sum(1 for ts in branches if ts < stale_cutoff)
    return {"branch_count": len(branches), "stale_branch_count": stale}


def _hotspots(repo_path: Path, file_commits_365d: dict[str, int], head_files: set[str], file_authors: dict[str, set[str]], top_n: int = 50, candidate_pool: int = 150) -> list[dict]:
    candidates = [f for f in file_commits_365d if f in head_files]
    candidates.sort(key=lambda f: file_commits_365d[f], reverse=True)
    candidates = candidates[:candidate_pool]

    rows = []
    for f in candidates:
        loc = _count_lines(repo_path / f)
        commits = file_commits_365d[f]
        rows.append({
            "path": f,
            "commits_365d": commits,
            "loc": loc,
            "authors": len(file_authors.get(f, set())),
            "hotspot_score": commits * loc,
        })
    rows.sort(key=lambda r: r["hotspot_score"], reverse=True)
    return rows[:top_n]


def collect(repo_path: Path, quick: bool = False, included_files: set[str] | None = None) -> dict[str, dict]:
    """`included_files`, when given, scopes single_author_file_pct and hotspots to the
    analyzed codebase (post-exclusion) rather than every path git ever tracked —
    without it, vendored/generated files git still has history for would pollute
    both metrics. Pass `exclusions.ClassificationResult.included_files` as a set."""
    repo_path = Path(repo_path)

    if not is_git_repo(repo_path):
        reason = "not a git repository — vcs.* metrics require git history"
        return {f"vcs.{name}": _unavailable(reason) for name in [
            "history_days", "commits_last_90d", "commits_last_365d", "active_authors_last_90d",
            "total_authors", "author_concentration_gini", "single_author_file_pct",
            "default_branch", "branch_count", "stale_branch_count", "merge_commit_ratio",
            "commit_msg_issue_ref_pct", "hotspots",
        ]}

    shallow = _is_shallow(repo_path)
    branch_facts = _branch_facts(repo_path)
    default_branch = _default_branch(repo_path)

    metrics: dict[str, dict] = {
        "vcs.default_branch": _envelope(default_branch, "", "git", "measured", 100, ""),
        "vcs.branch_count": _envelope(branch_facts["branch_count"], "count", "git", "measured", 100, ""),
        "vcs.stale_branch_count": _envelope(
            branch_facts["stale_branch_count"], "count", "git", "measured", 100,
            f"stale = no commits in the last {STALE_BRANCH_DAYS} days",
        ),
    }

    if shallow:
        reason = "shallow clone (--depth override) — full history required for this metric"
        for name in sorted(SHALLOW_AFFECTED_METRICS):
            metrics[f"vcs.{name}"] = _unavailable(reason)
        return metrics

    if quick:
        reason = "skipped under --quick — full-history log traversal exceeds the quick-pass budget"
        for name in ["single_author_file_pct", "hotspots"]:
            metrics[f"vcs.{name}"] = _unavailable(reason)
        parsed = _parse_log(repo_path)  # still cheap enough for the aggregate counters
    else:
        parsed = _parse_log(repo_path)

    total_commits = parsed["total_commits"]
    if total_commits == 0:
        reason = "git repository has no commits reachable from HEAD"
        for name in sorted(SHALLOW_AFFECTED_METRICS):
            metrics.setdefault(f"vcs.{name}", _unavailable(reason))
        return metrics

    history_days = 0
    if parsed["min_ts"] is not None and parsed["max_ts"] is not None:
        history_days = int((parsed["max_ts"] - parsed["min_ts"]) / 86400)

    metrics["vcs.history_days"] = _envelope(history_days, "days", "git", "measured", 100, "")
    metrics["vcs.commits_last_90d"] = _envelope(
        parsed["commits_in_window"][90], "count", "git", "measured", 100,
        "relative to run time, not just the checked-out commit — will differ if re-run on a later date",
    )
    metrics["vcs.commits_last_365d"] = _envelope(
        parsed["commits_in_window"][365], "count", "git", "measured", 100,
        "relative to run time — see notes on commits_last_90d",
    )
    metrics["vcs.active_authors_last_90d"] = _envelope(
        len(parsed["active_authors"][90]), "count", "git", "measured", 100, "",
    )
    metrics["vcs.total_authors"] = _envelope(
        len(parsed["author_counts"]), "count", "git", "measured", 100, "",
    )
    metrics["vcs.author_concentration_gini"] = _envelope(
        _gini(list(parsed["author_counts"].values())), "gini", "git", "derived", 100,
        "0 = commits spread evenly across authors, 1 = one author owns everything",
    )
    metrics["vcs.merge_commit_ratio"] = _envelope(
        round(parsed["merge_commits"] / total_commits, 4), "ratio", "git", "measured", 100, "",
    )
    metrics["vcs.commit_msg_issue_ref_pct"] = _envelope(
        round(100 * parsed["issue_ref_commits"] / total_commits, 2), "pct", "git", "derived", 100,
        r"matches /(#\d+)|([A-Z]{2,10}-\d+)/ in the commit subject — a heuristic, not a PMS integration",
    )

    head_files = _head_file_set(repo_path)
    if included_files is not None:
        head_files = head_files & included_files
        scope_note = "scoped to the analyzed (post-exclusion) codebase"
    else:
        scope_note = "scoped to all files git tracks at HEAD — pass included_files to exclude vendored/generated paths"

    if "vcs.single_author_file_pct" not in metrics:
        tracked = [f for f in head_files if f in parsed["file_authors"]]
        if tracked:
            single_author = sum(1 for f in tracked if len(parsed["file_authors"][f]) == 1)
            pct = round(100 * single_author / len(tracked), 2)
            coverage = round(100 * len(tracked) / len(head_files), 2) if head_files else 0
            metrics["vcs.single_author_file_pct"] = _envelope(
                pct, "pct", "git", "derived", coverage,
                f"{scope_note}; renamed/moved files may undercount authorship",
            )
        else:
            metrics["vcs.single_author_file_pct"] = _unavailable("no in-scope files with resolvable history")

    if "vcs.hotspots" not in metrics:
        rows = _hotspots(repo_path, parsed["file_commits_365d"], head_files, parsed["file_authors"])
        metrics["vcs.hotspots"] = _envelope(
            rows, "ranked_list", "git", "derived", 100,
            f"hotspot_score = commits_365d * current LOC; ranked descending, top 50 kept; {scope_note}",
        )

    return metrics
