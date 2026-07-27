#!/usr/bin/env python3
"""Layer 1 provider for the `context.*` and `ops.*` metric families.

Lives at scripts/ root rather than scripts/providers/, mirroring exclusions.py:
both families are cheap, local, marker-file/keyword heuristics that don't fit
the stack-specific "provider" shape (build/test/ci/deps/debt/structure) the
providers/ directory otherwise holds one file per. Folding them into any one
of those would have been an arbitrary fit; this keeps the boundary honest.
"""
from __future__ import annotations

import re
from pathlib import Path

ADR_DIR_NAMES = ["docs/adr", "docs/decisions", "adr", "doc/adr"]
API_SPEC_MARKERS = ["openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.json"]
DB_SCHEMA_MARKERS = ["schema.sql", "docs/schema.md", "docs/database.md", "ERD.md"]
GLOSSARY_MARKERS = ["GLOSSARY.md", "glossary.md", "docs/glossary.md"]

OBSERVABILITY_KEYWORDS = [r"\bsentry\b", r"@sentry/", r"\bdatadog\b", r"\bnewrelic\b",
                           r"\bopentelemetry\b", r"\bprometheus\b", r"\bhoneycomb\b"]
FEATURE_FLAG_KEYWORDS = [r"launchdarkly", r"flagsmith", r"\bunleash\b", r"split\.io", r"\bgrowthbook\b"]
DEPLOY_AUTOMATION_MARKERS = ["Procfile", "app.yaml", "serverless.yml", "serverless.yaml"]
DEPLOY_KEYWORDS = [r"\bdeploy\b", r"\brelease\b"]
STAGING_KEYWORDS = [r"\bstaging\b", r"\bstage\b"]
ROLLBACK_MARKERS = ["ROLLBACK.md", "docs/rollback.md", "docs/runbook.md", "RUNBOOK.md"]
ROLLBACK_KEYWORDS = [r"\brollback\b", r"blue.?green", r"\bcanary\b"]


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _any_exists(repo_path: Path, names: list[str]) -> bool:
    return any((repo_path / n).exists() for n in names)


def _readme_text(repo_path: Path) -> str:
    for name in ["README.md", "README.rst", "README.txt", "readme.md"]:
        path = repo_path / name
        if path.exists():
            try:
                return path.read_text(errors="replace")
            except OSError:
                pass
    return ""


def readme_quality_score(repo_path: Path) -> int:
    text = _readme_text(repo_path)
    if not text.strip():
        return 0
    lines = text.splitlines()
    score = 0
    if len(lines) > 20:
        score += 20
    if len(lines) > 100:
        score += 20
    if re.search(r"^#{1,3}\s*(install|installation|setup)", text, re.IGNORECASE | re.MULTILINE):
        score += 20
    if re.search(r"^#{1,3}\s*(usage|getting started|quickstart|quick start)", text, re.IGNORECASE | re.MULTILINE):
        score += 20
    if "```" in text:
        score += 20
    return min(100, score)


def count_adrs(repo_path: Path, included_files: list[str]) -> int:
    count = 0
    for f in included_files:
        parts = f.lower().rsplit("/", 1)
        directory = parts[0] if len(parts) > 1 else ""
        if directory in ADR_DIR_NAMES and f.lower().endswith(".md"):
            count += 1
    return count


def docs_loc(repo_path: Path, included_files: list[str]) -> int:
    from exclusions import _count_lines
    total = 0
    for f in included_files:
        lower = f.lower()
        if lower.startswith("docs/") or lower.startswith("doc/") or lower.startswith("documentation/"):
            total += _count_lines(repo_path / f)
    return total


def _search_manifests_and_config(repo_path: Path, included_files: list[str], patterns: list[str], max_files: int = 300) -> bool:
    combined = ""
    manifest_like = [f for f in included_files if any(
        f.endswith(ext) for ext in [".json", ".yml", ".yaml", ".toml", ".txt", ".lock"]
    )][:max_files]
    for f in manifest_like:
        try:
            combined += (repo_path / f).read_text(errors="replace") + "\n"
        except OSError:
            continue
    return any(re.search(p, combined, re.IGNORECASE) for p in patterns)


def collect(repo_path: Path, included_files: list[str]) -> dict[str, dict]:
    repo_path = Path(repo_path)

    ai_context_present = (repo_path / "ai-context").is_dir()
    api_spec = _any_exists(repo_path, API_SPEC_MARKERS) or any(f.endswith(".proto") for f in included_files)
    db_schema = _any_exists(repo_path, DB_SCHEMA_MARKERS)
    glossary = _any_exists(repo_path, GLOSSARY_MARKERS)
    adr_count = count_adrs(repo_path, included_files)

    deploy_automation = (
        _any_exists(repo_path, DEPLOY_AUTOMATION_MARKERS)
        or (repo_path / "terraform").is_dir()
        or _search_manifests_and_config(repo_path, included_files, DEPLOY_KEYWORDS + [r"\.github/workflows.*deploy"])
    )
    staging_declared = _search_manifests_and_config(repo_path, included_files, STAGING_KEYWORDS)
    observability = _search_manifests_and_config(repo_path, included_files, OBSERVABILITY_KEYWORDS)
    feature_flags = _search_manifests_and_config(repo_path, included_files, FEATURE_FLAG_KEYWORDS)
    rollback = _any_exists(repo_path, ROLLBACK_MARKERS) or _search_manifests_and_config(
        repo_path, included_files, ROLLBACK_KEYWORDS)

    return {
        "context.readme_quality_score": _envelope(
            readme_quality_score(repo_path), "pct", "context_ops_probe", "derived", 100,
            "heuristic: length + presence of install/usage headings + code fences, out of 100"),
        "context.adr_count": _envelope(adr_count, "count", "context_ops_probe", "measured", 100,
                                          "counts .md files under docs/adr, docs/decisions, or adr/"),
        "context.docs_loc": _envelope(docs_loc(repo_path, included_files), "loc", "context_ops_probe", "measured", 100, ""),
        "context.api_spec_present": _envelope(api_spec, "bool", "context_ops_probe", "measured", 100,
                                                  "openapi/swagger/*.proto marker files"),
        "context.db_schema_docs_present": _envelope(db_schema, "bool", "context_ops_probe", "measured", 100, ""),
        "context.domain_glossary_present": _envelope(glossary, "bool", "context_ops_probe", "measured", 100, ""),
        "context.ai_context_present": _envelope(ai_context_present, "bool", "context_ops_probe", "measured", 100,
                                                    "this plugin's own ai-context/ directory convention"),

        "ops.deploy_automation_present": _envelope(
            deploy_automation, "bool", "context_ops_probe", "derived", 100,
            "Procfile/app.yaml/serverless.yml/terraform/, or a deploy-named CI job — keyword heuristic"),
        "ops.staging_env_declared": _envelope(
            staging_declared, "bool", "context_ops_probe", "derived", 100,
            "keyword heuristic over manifests/config — a hard L4 trust-level gate, see ralph-agent-spec.md"),
        "ops.observability_present": _envelope(
            observability, "bool", "context_ops_probe", "derived", 100,
            "sentry/datadog/newrelic/opentelemetry/prometheus keyword heuristic over manifests"),
        "ops.feature_flag_system_present": _envelope(
            feature_flags, "bool", "context_ops_probe", "derived", 100,
            "launchdarkly/flagsmith/unleash/split.io/growthbook keyword heuristic"),
        "ops.rollback_mechanism_documented": _envelope(
            rollback, "bool", "context_ops_probe", "derived", 100,
            "ROLLBACK.md/runbook marker file, or blue-green/canary/rollback keyword in CI config"),
    }
