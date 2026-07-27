#!/usr/bin/env python3
"""Orchestrator + provider dispatch for /assess-repo.

Builds the exclusion set once, resolves the target (git URL -> temp clone, or
local path), runs each provider, and assembles a full assessment-inputs.json
covering all 80 required metric IDs. Degrades per-provider, never per-run: a
provider that can't run reports its metrics `unavailable` with a reason, it
never crashes the whole collection.

Usage:
    python3 collect.py <git-url-or-local-path> [--quick] [--depth N]
                        [--out DIR] [--policy PATH] [--extra-exclusions PATH]
                        [--attempt-build] [--attempt-test]
                        [--providers git,language_census,build_probe,...]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import context_ops_probe  # noqa: E402
import exclusions  # noqa: E402
import validate as validate_mod  # noqa: E402
from providers import (  # noqa: E402
    build_probe, ci_probe, debt_probe, deps_probe, git_history,
    language_census, structure_graphify, test_probe,
)

GIT_URL_PATTERN = re.compile(
    r"^(https?://|git@|ssh://).+\.git$|^(https?://)(github|gitlab|bitbucket|dev\.azure)\.com/"
)

ALL_PROVIDER_NAMES = [
    "git", "language_census", "build_probe", "test_probe", "ci_probe",
    "deps_probe", "debt_probe", "structure_graphify", "context_ops_probe",
]


def _unavailable(notes: str) -> dict:
    return {"value": None, "unit": "", "source": "", "confidence": "unavailable", "coverage_pct": None, "notes": notes}


def _skip_metrics(metric_ids: list[str], reason: str) -> dict[str, dict]:
    return {mid: _unavailable(reason) for mid in metric_ids}


def is_git_url(target: str) -> bool:
    return bool(GIT_URL_PATTERN.match(target.strip()))


def resolve_target(target: str, depth: int | None) -> tuple[Path, str, bool, str]:
    """Returns (local_path, mode, is_temp_clone, source_string)."""
    if is_git_url(target):
        tmp_dir = Path(tempfile.mkdtemp(prefix="assess-repo-"))
        clone_args = ["git", "clone"]
        if depth is not None:
            clone_args += ["--depth", str(depth)]
        clone_args += [target, str(tmp_dir)]
        result = subprocess.run(clone_args, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed for {target}:\n{result.stderr}")
        return tmp_dir, "git_url", True, target
    local = Path(target).expanduser().resolve()
    if not local.exists():
        raise RuntimeError(f"local path does not exist: {local}")
    return local, "local_path", False, str(local)


def slugify(text: str) -> str:
    text = re.sub(r"\.git$", "", text.strip())
    text = text.rsplit("/", 1)[-1] or "repo"
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-").lower() or "repo"


BUILD_METRIC_IDS = ["build." + n for n in [
    "detected_systems", "containerized", "devcontainer_present", "one_command_build_documented",
    "lockfiles_present", "required_env_var_count", "external_service_deps", "attempt"]]
TEST_METRIC_IDS = ["test." + n for n in [
    "frameworks_detected", "test_file_count", "test_to_source_ratio", "coverage_pct", "coverage_source",
    "suite_executes", "suite_duration_s", "pass_rate", "flake_indicators", "unit_present",
    "integration_present", "e2e_present", "fixture_or_seed_data_present"]]
CI_METRIC_IDS = ["ci." + n for n in [
    "systems_detected", "runs_on_pr", "gates", "success_rate_recent", "avg_duration_s"]]
DEPS_METRIC_IDS = ["deps." + n for n in [
    "manifest_count", "direct_count", "transitive_count", "duplicate_framework_versions",
    "eol_components", "median_majors_behind", "known_vuln_count_by_severity"]]
DEBT_METRIC_IDS = ["debt." + n for n in [
    "analyzer_used", "violations_total", "violations_per_kloc", "violations_by_severity",
    "todo_fixme_hack_count", "baselineable"]]
STRUCTURE_METRIC_IDS = ["structure." + n for n in [
    "parser_coverage_pct", "module_count", "community_count", "god_nodes",
    "cyclic_dependency_count", "avg_fan_out", "max_fan_out", "cross_stack_edge_count"]]
CONTEXT_OPS_METRIC_IDS = ["context." + n for n in [
    "readme_quality_score", "adr_count", "docs_loc", "api_spec_present",
    "db_schema_docs_present", "domain_glossary_present", "ai_context_present"]] + ["ops." + n for n in [
    "deploy_automation_present", "staging_env_declared", "observability_present",
    "feature_flag_system_present", "rollback_mechanism_documented"]]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Collect Layer 1/2 metrics for /assess-repo")
    parser.add_argument("target", help="git URL or local filesystem path")
    parser.add_argument("--quick", action="store_true", default=False)
    parser.add_argument("--depth", type=int, default=None)
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--policy", type=str, default=None)
    parser.add_argument("--extra-exclusions", type=str, default=None)
    parser.add_argument("--attempt-build", action="store_true", default=False)
    parser.add_argument("--attempt-test", action="store_true", default=False)
    parser.add_argument("--providers", type=str, default=None,
                         help="comma-separated subset of: " + ",".join(ALL_PROVIDER_NAMES))
    args = parser.parse_args(argv)

    if args.attempt_test and not args.attempt_build:
        print("✗ --attempt-test requires --attempt-build", file=sys.stderr)
        return 2

    if args.attempt_build:
        print(
            "⚠️  --attempt-build executes build commands from the target repository. "
            "This runs untrusted code. Recommended: run this inside a disposable container.",
            file=sys.stderr,
        )

    enabled = set(args.providers.split(",")) if args.providers else set(ALL_PROVIDER_NAMES)
    unknown = enabled - set(ALL_PROVIDER_NAMES)
    if unknown:
        print(f"✗ unknown provider(s) in --providers: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2

    local_path, mode, is_temp_clone, source = resolve_target(args.target, args.depth)
    providers_report: list[dict] = []
    metrics: dict[str, dict] = {}

    # --- git / vcs.* ---
    is_repo = git_history.is_git_repo(local_path)
    if "git" in enabled:
        providers_report.append({
            "name": "git", "version": "", "reason": "" if is_repo else "not a git repository",
            "status": "ok" if is_repo else "unavailable",
        })
    else:
        providers_report.append({"name": "git", "version": "", "status": "skipped_by_policy",
                                   "reason": "excluded via --providers"})

    # --- exclusion classification (always runs — needed by every downstream provider) ---
    patterns = exclusions.load_patterns(
        extra_path=Path(args.extra_exclusions) if args.extra_exclusions else None,
    )
    classification = exclusions.walk_and_classify(local_path, patterns, quick=args.quick)
    included_files = classification.included_files

    # --- codebase.* ---
    if "language_census" in enabled:
        census_metrics = language_census.collect(local_path, classification)
        census_source = next(iter(census_metrics.values()))["source"]
        providers_report.append({"name": f"language-census:{census_source}", "version": "", "status": "ok", "reason": ""})
    else:
        census_metrics = _skip_metrics(
            ["codebase." + n for n in ["total_loc", "file_count", "language_census", "distinct_stacks_count",
                                         "generated_loc_pct", "largest_file_loc", "avg_file_loc", "p95_file_loc"]],
            "excluded via --providers",
        )
        providers_report.append({"name": "language_census", "version": "", "status": "skipped_by_policy", "reason": "excluded via --providers"})
    metrics.update(census_metrics)
    total_loc = census_metrics.get("codebase.total_loc", {}).get("value") or 0

    # --- vcs.* ---
    if "git" in enabled:
        vcs_metrics = git_history.collect(local_path, quick=args.quick, included_files=set(included_files))
    else:
        vcs_metrics = _skip_metrics(
            ["vcs." + n for n in ["history_days", "commits_last_90d", "commits_last_365d",
                                    "active_authors_last_90d", "total_authors", "author_concentration_gini",
                                    "single_author_file_pct", "default_branch", "branch_count",
                                    "stale_branch_count", "merge_commit_ratio", "commit_msg_issue_ref_pct", "hotspots"]],
            "excluded via --providers",
        )
    metrics.update(vcs_metrics)
    target_info = git_history.probe_target_info(local_path)

    # --- policy gate (applies to providers that could transmit data off-machine;
    #     of the ones implemented so far, none actually do — deps_probe/debt_probe/
    #     structure_graphify are all local-only. Kept here so a real off-machine
    #     provider added later has a single, obvious place to check.) ---
    policy_third_party_allowed = True
    if args.policy:
        try:
            policy_doc = json.loads(Path(args.policy).read_text())
            policy_third_party_allowed = policy_doc.get("third_party_tooling_allowed", True)
        except (OSError, ValueError) as exc:
            print(f"⚠️  could not parse --policy file ({exc}); assuming tooling is permitted", file=sys.stderr)

    def _dispatch(name: str, metric_ids: list[str], fn):
        if name not in enabled:
            providers_report.append({"name": name, "version": "", "status": "skipped_by_policy", "reason": "excluded via --providers"})
            return _skip_metrics(metric_ids, "excluded via --providers")
        if not policy_third_party_allowed:
            providers_report.append({"name": name, "version": "", "status": "skipped_by_policy",
                                       "reason": "client data policy forbids third-party tooling"})
            return _skip_metrics(metric_ids, "skipped: client data policy forbids third-party tooling")
        try:
            result = fn()
            providers_report.append({"name": name, "version": "", "status": "ok", "reason": ""})
            return result
        except Exception as exc:  # a single provider failing must never fail the whole run
            providers_report.append({"name": name, "version": "", "status": "failed", "reason": str(exc)})
            return _skip_metrics(metric_ids, f"provider raised an exception: {exc}")

    metrics.update(_dispatch("build_probe", BUILD_METRIC_IDS,
                               lambda: build_probe.collect(local_path, attempt=args.attempt_build)))
    metrics.update(_dispatch("test_probe", TEST_METRIC_IDS,
                               lambda: test_probe.collect(local_path, included_files, attempt=args.attempt_test)))
    metrics.update(_dispatch("ci_probe", CI_METRIC_IDS, lambda: ci_probe.collect(local_path)))
    metrics.update(_dispatch("deps_probe", DEPS_METRIC_IDS, lambda: deps_probe.collect(local_path)))
    metrics.update(_dispatch("debt_probe", DEBT_METRIC_IDS,
                               lambda: debt_probe.collect(local_path, included_files, total_loc)))
    metrics.update(_dispatch("structure_graphify", STRUCTURE_METRIC_IDS,
                               lambda: structure_graphify.collect(local_path, len(included_files))))
    metrics.update(_dispatch("context_ops_probe", CONTEXT_OPS_METRIC_IDS,
                               lambda: context_ops_probe.collect(local_path, included_files)))

    resolved_commit = target_info["resolved_commit"]
    short_sha = resolved_commit[:7] if resolved_commit else "nogit"
    repo_slug = slugify(source)
    now = datetime.now(timezone.utc)
    assessment_id = f"{repo_slug}-{short_sha}-{now.strftime('%Y%m%dT%H%M%SZ')}"

    document = {
        "schema_version": "1.0",
        "rubric_version": "1.0",
        "assessment_id": assessment_id,
        "generated_at": now.isoformat(),
        "target": {
            "mode": mode,
            "source": source,
            "resolved_commit": resolved_commit,
            "default_branch": target_info["default_branch"],
            "history_complete": target_info["history_complete"],
            "analyzed_path": str(local_path),
            "is_monorepo": False,
            "detected_projects": [],
            "submodules": [],
        },
        "providers": providers_report,
        "exclusions": {
            "patterns": patterns.general,
            "excluded_loc": classification.excluded_loc,
            "excluded_file_count": classification.excluded_file_count,
        },
        "human_inputs": {},
        "metrics": metrics,
    }

    errors = validate_mod.validate(document)
    if errors:
        print("✗ collected document failed schema validation:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else Path.cwd() / ".assessment" / f"{repo_slug}-{short_sha}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "assessment-inputs.json"
    out_path.write_text(json.dumps(document, indent=2) + "\n")

    print(f"✅ wrote {out_path}")
    print(f"   codebase.total_loc = {metrics['codebase.total_loc']['value']} "
          f"({metrics['codebase.total_loc']['source']})")
    print(f"   vcs.history_days = {vcs_metrics.get('vcs.history_days', {}).get('value')}")
    print(f"   exclusions: {classification.excluded_file_count} files, "
          f"{classification.excluded_loc} loc ({classification.excluded_loc_confidence})")
    n_ok = sum(1 for p in providers_report if p["status"] == "ok")
    print(f"   providers: {n_ok}/{len(providers_report)} ok")

    if is_temp_clone:
        print(f"   (cloned to temp dir {local_path} — not cleaned up automatically)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
