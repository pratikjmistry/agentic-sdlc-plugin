#!/usr/bin/env python3
"""Layer 1 provider: language census (the `codebase.*` metric family).

Preference order: tokei > scc > cloc > in-house pure-Python counter. The
in-house counter is the tested, guaranteed-available default — none of tokei/
scc/cloc are hard dependencies (per SKILL.md's "no graph tool, no hard
external dependency" constraint), and this module falls back to it silently
on any failure from the optional accelerants (not installed, non-zero exit,
unparseable output). The in-house path is what "a language counter" in the
skill's own default-run guarantee refers to.

Consumes a pre-computed `exclusions.ClassificationResult` (see exclusions.py)
rather than re-walking the tree — exclusion accounting happens exactly once,
owned by collect.py, and every provider that needs "what's actually in the
codebase" reads from that single result.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from exclusions import ClassificationResult, _count_lines  # sibling module, see collect.py's sys.path setup

# Extension -> language name. Deliberately broad but not exhaustive — full
# parser-grade language detection is structure_graphify.py's job (Phase 2),
# not this cheap census. Legacy stacks are included explicitly since they're
# named in this plugin's brownfield scope.
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".cs": "C#", ".vb": "VB.NET",
    ".cshtml": "Razor", ".vbhtml": "Razor",
    ".aspx": "ASP.NET WebForms", ".ascx": "ASP.NET WebForms", ".asmx": "ASP.NET WebForms",
    ".asp": "Classic ASP", ".vbs": "VBScript",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
    ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C++",
    ".pas": "Delphi/Pascal", ".dpr": "Delphi/Pascal", ".dfm": "Delphi/Pascal", ".dproj": "Delphi/Pascal",
    ".frm": "VB6", ".bas": "VB6", ".cls": "VB6", ".vbp": "VB6",
    ".sql": "SQL", ".pls": "PL/SQL", ".pks": "PL/SQL", ".pkb": "PL/SQL",
    ".pl": "Perl", ".pm": "Perl",
    ".sh": "Shell", ".bash": "Shell", ".ps1": "PowerShell", ".psm1": "PowerShell",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "SCSS", ".less": "Less",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".xml": "XML", ".xaml": "XAML",
    ".md": "Markdown", ".rst": "reStructuredText",
    ".tf": "Terraform", ".dockerfile": "Dockerfile",
    ".r": "R", ".jl": "Julia", ".lua": "Lua", ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir",
    ".clj": "Clojure", ".cljs": "Clojure", ".erl": "Erlang", ".hs": "Haskell", ".fs": "F#",
    ".gradle": "Gradle", ".groovy": "Groovy",
}


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {
        "value": value, "unit": unit, "source": source,
        "confidence": confidence, "coverage_pct": coverage_pct, "notes": notes,
    }


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    idx = min(len(sorted_values) - 1, int(round((pct / 100) * (len(sorted_values) - 1))))
    return sorted_values[idx]


def _in_house_census(repo_path: Path, included_files: list[str]) -> tuple[list[dict], int, int, int, int]:
    """Returns (language_rows, total_loc, largest, avg (as int-rounded via caller), p95)."""
    per_file_loc: list[int] = []
    lang_loc: dict[str, int] = {}
    lang_files: dict[str, int] = {}

    for relpath in included_files:
        loc = _count_lines(repo_path / relpath)
        per_file_loc.append(loc)
        ext = Path(relpath).suffix.lower()
        language = EXTENSION_LANGUAGE_MAP.get(ext, f"Other ({ext or 'no extension'})")
        lang_loc[language] = lang_loc.get(language, 0) + loc
        lang_files[language] = lang_files.get(language, 0) + 1

    total_loc = sum(per_file_loc)
    rows = []
    for language, loc in sorted(lang_loc.items(), key=lambda kv: kv[1], reverse=True):
        pct = round(100 * loc / total_loc, 2) if total_loc else 0
        rows.append({"language": language, "loc": loc, "pct": pct, "files": lang_files[language]})

    per_file_loc.sort()
    largest = per_file_loc[-1] if per_file_loc else 0
    p95 = _percentile(per_file_loc, 95)
    return rows, total_loc, largest, p95, len(per_file_loc)


def _try_tokei(repo_path: Path) -> list[dict] | None:
    """Best-effort accelerator. Not exercised against a real tokei binary in
    this environment (none installed) — falls back silently on any failure,
    by design. Treat this path as unverified until run against a real install."""
    if shutil.which("tokei") is None:
        return None
    try:
        cp = subprocess.run(
            ["tokei", "--output", "json", str(repo_path)],
            capture_output=True, text=True, timeout=120,
        )
        if cp.returncode != 0:
            return None
        data = json.loads(cp.stdout)
        rows = []
        for language, stats in data.items():
            if not isinstance(stats, dict) or "code" not in stats:
                continue
            reports = stats.get("reports", [])
            rows.append({
                "language": language,
                "loc": stats["code"],
                "pct": 0.0,  # filled in by caller once total is known
                "files": len(reports) if reports else stats.get("stats", {}).get("files", 0),
            })
        return rows or None
    except Exception:
        return None


def collect(repo_path: Path, classification: ClassificationResult) -> dict[str, dict]:
    repo_path = Path(repo_path)
    included_files = classification.included_files

    tokei_rows = _try_tokei(repo_path)
    if tokei_rows is not None:
        total_loc = sum(r["loc"] for r in tokei_rows)
        for r in tokei_rows:
            r["pct"] = round(100 * r["loc"] / total_loc, 2) if total_loc else 0
        tokei_rows.sort(key=lambda r: r["loc"], reverse=True)
        # tokei doesn't give us per-file LOC directly in this shape, so
        # largest/avg/p95 still come from the in-house pass for consistency.
        _, _, largest, p95, file_count = _in_house_census(repo_path, included_files)
        rows, source = tokei_rows, "tokei"
    else:
        rows, total_loc, largest, p95, file_count = _in_house_census(repo_path, included_files)
        source = "in-house"

    avg = round(total_loc / file_count, 1) if file_count else 0
    distinct_stacks = len(rows)

    gross_total = total_loc + classification.excluded_loc
    generated_pct = round(100 * classification.generated_loc / gross_total, 2) if gross_total else 0
    generated_conf = "measured" if classification.generated_loc >= 0 else "unavailable"

    return {
        "codebase.total_loc": _envelope(total_loc, "loc", source, "measured", 100, ""),
        "codebase.file_count": _envelope(file_count, "count", source, "measured", 100, ""),
        "codebase.language_census": _envelope(
            rows, "per_language", source, "measured", 100,
            "sorted descending by LOC" + ("; tokei-derived, cross-check against in-house counter recommended until verified" if source == "tokei" else ""),
        ),
        "codebase.distinct_stacks_count": _envelope(
            distinct_stacks, "count", source, "derived", 100,
            "count of distinct languages detected — a coarser notion than 'framework stack'",
        ),
        "codebase.generated_loc_pct": _envelope(
            generated_pct, "pct", "exclusions", generated_conf, 100,
            "generated LOC / (included + all excluded LOC) — see exclusions.generated_file_count",
        ),
        "codebase.largest_file_loc": _envelope(largest, "loc", "in-house", "measured", 100, ""),
        "codebase.avg_file_loc": _envelope(avg, "loc", "in-house", "measured", 100, ""),
        "codebase.p95_file_loc": _envelope(p95, "loc", "in-house", "measured", 100, ""),
    }
