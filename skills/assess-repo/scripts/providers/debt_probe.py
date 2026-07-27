#!/usr/bin/env python3
"""Layer 1 provider: static debt signals (the `debt.*` metric family).

`todo_fixme_hack_count` is fully local and tool-free (a regex sweep) — always
available. `violations_total`/`violations_per_kloc`/`violations_by_severity`/
`analyzer_used` need an actual static analyzer on PATH: semgrep first (broad,
multi-language, matches the spec's own preference), falling back to a
stack-native analyzer (ruff for Python) if semgrep isn't installed, else
`unavailable`. Neither semgrep nor ruff is installed in this development
environment, so this integration is best-effort / not exercised against a
real binary here — the graceful-fallback path (todo/fixme/hack only) is what's
actually been run and verified.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
TEXT_LIKE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".vb", ".go", ".rb", ".php",
    ".c", ".h", ".cpp", ".hpp", ".rs", ".swift", ".kt", ".scala", ".sql", ".sh",
}


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _unavailable(notes: str) -> dict:
    return _envelope(None, "", "", "unavailable", None, notes)


def count_todo_fixme_hack(repo_path: Path, included_files: list[str]) -> int:
    count = 0
    for relpath in included_files:
        if Path(relpath).suffix.lower() not in TEXT_LIKE_EXTENSIONS:
            continue
        try:
            text = (repo_path / relpath).read_text(errors="replace")
        except OSError:
            continue
        count += len(TODO_PATTERN.findall(text))
    return count


def _try_semgrep(repo_path: Path) -> dict | None:
    """Best-effort — not exercised against a real semgrep binary in this
    environment (none installed). Falls back silently on any failure."""
    if shutil.which("semgrep") is None:
        return None
    try:
        cp = subprocess.run(
            ["semgrep", "--config=auto", "--json", "--quiet", str(repo_path)],
            capture_output=True, text=True, timeout=300,
        )
        data = json.loads(cp.stdout)
        results = data.get("results", [])
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for r in results:
            sev = (r.get("extra", {}).get("severity") or "medium").lower()
            mapped = {"error": "high", "warning": "medium", "info": "low"}.get(sev, sev)
            if mapped not in by_severity:
                mapped = "medium"
            by_severity[mapped] += 1
        return {"analyzer": "semgrep", "total": len(results), "by_severity": by_severity}
    except Exception:
        return None


def _try_ruff(repo_path: Path) -> dict | None:
    """Best-effort Python-native fallback — same caveat as _try_semgrep."""
    if shutil.which("ruff") is None:
        return None
    try:
        cp = subprocess.run(
            ["ruff", "check", "--output-format=json", str(repo_path)],
            capture_output=True, text=True, timeout=300,
        )
        data = json.loads(cp.stdout) if cp.stdout.strip() else []
        by_severity = {"critical": 0, "high": 0, "medium": len(data), "low": 0}
        return {"analyzer": "ruff", "total": len(data), "by_severity": by_severity}
    except Exception:
        return None


def collect(repo_path: Path, included_files: list[str], total_loc: int) -> dict[str, dict]:
    repo_path = Path(repo_path)
    todo_count = count_todo_fixme_hack(repo_path, included_files)

    result = _try_semgrep(repo_path) or _try_ruff(repo_path)

    metrics = {
        "debt.todo_fixme_hack_count": _envelope(
            todo_count, "count", "debt_probe", "measured", 100,
            "regex sweep for TODO/FIXME/HACK/XXX across text-like included files",
        ),
    }

    if result is not None:
        per_kloc = round(1000 * result["total"] / total_loc, 2) if total_loc else 0
        metrics["debt.analyzer_used"] = _envelope(result["analyzer"], "", "debt_probe", "measured", 100, "")
        metrics["debt.violations_total"] = _envelope(result["total"], "count", "debt_probe", "measured", 100, "")
        metrics["debt.violations_per_kloc"] = _envelope(per_kloc, "ratio", "debt_probe", "derived", 100, "")
        metrics["debt.violations_by_severity"] = _envelope(result["by_severity"], "object", "debt_probe", "measured", 100, "")
        metrics["debt.baselineable"] = _envelope(
            True, "bool", "debt_probe", "derived", 100,
            f"{result['analyzer']} ran successfully, giving a concrete baseline to ratchet against",
        )
    else:
        reason = "no static analyzer available (semgrep or ruff not found on PATH); install one to enable this family"
        metrics["debt.analyzer_used"] = _unavailable(reason)
        metrics["debt.violations_total"] = _unavailable(reason)
        metrics["debt.violations_per_kloc"] = _unavailable(reason)
        metrics["debt.violations_by_severity"] = _unavailable(reason)
        metrics["debt.baselineable"] = _unavailable(reason)

    return metrics
