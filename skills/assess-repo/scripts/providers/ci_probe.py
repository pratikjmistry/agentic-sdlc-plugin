#!/usr/bin/env python3
"""Layer 1 provider: CI capability (the `ci.*` metric family).

Fully local and detect-only: parses committed CI config files. Does not call
any CI provider's API — `success_rate_recent` and `avg_duration_s` would
require that (GitHub Actions API, GitLab API, etc.), which means real
authenticated network access this plugin never assumes by default. Both are
reported `unavailable` with that reason; a future revision could wire them in
as an explicitly opt-in, policy-gated provider.
"""
from __future__ import annotations

import re
from pathlib import Path

GATE_KEYWORDS = {
    "lint": [r"\blint\b", r"\beslint\b", r"\bruff\b", r"\bflake8\b", r"\bpylint\b", r"\bstylelint\b"],
    "test": [r"\btest\b", r"\bpytest\b", r"\bjest\b", r"\bunit[- ]?test\b"],
    "coverage": [r"\bcoverage\b", r"\bcodecov\b", r"\bcoveralls\b"],
    "security": [r"\bsecurity\b", r"\baudit\b", r"\bsnyk\b", r"\bsemgrep\b", r"\bcodeql\b", r"\btrivy\b"],
    "build": [r"\bbuild\b", r"\bcompile\b", r"\bpackage\b"],
}


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _unavailable(notes: str) -> dict:
    return _envelope(None, "", "", "unavailable", None, notes)


def detect_systems(repo_path: Path) -> list[str]:
    found = []
    if (repo_path / ".github" / "workflows").is_dir() and any((repo_path / ".github" / "workflows").glob("*.y*ml")):
        found.append("github-actions")
    if (repo_path / ".gitlab-ci.yml").exists():
        found.append("gitlab-ci")
    if (repo_path / "azure-pipelines.yml").exists():
        found.append("azure-pipelines")
    if (repo_path / "Jenkinsfile").exists():
        found.append("jenkins")
    if (repo_path / ".circleci" / "config.yml").exists():
        found.append("circleci")
    if (repo_path / ".travis.yml").exists():
        found.append("travis-ci")
    if (repo_path / "bitbucket-pipelines.yml").exists():
        found.append("bitbucket-pipelines")
    return found


def _github_actions_configs(repo_path: Path) -> list[str]:
    workflows_dir = repo_path / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    texts = []
    for path in workflows_dir.glob("*.y*ml"):
        try:
            texts.append(path.read_text(errors="replace"))
        except OSError:
            continue
    return texts


def runs_on_pr(repo_path: Path, systems: list[str]) -> bool | None:
    if "github-actions" in systems:
        try:
            import yaml
            for text in _github_actions_configs(repo_path):
                doc = yaml.safe_load(text) or {}
                on = doc.get("on") or doc.get(True)  # PyYAML may parse bare `on:` as boolean True key
                if isinstance(on, str) and "pull_request" in on:
                    return True
                if isinstance(on, list) and any("pull_request" in str(x) for x in on):
                    return True
                if isinstance(on, dict) and any("pull_request" in str(k) for k in on):
                    return True
        except Exception:
            # fall through to the substring heuristic below
            pass
        for text in _github_actions_configs(repo_path):
            if "pull_request" in text:
                return True
        return False

    if "gitlab-ci" in systems:
        try:
            text = (repo_path / ".gitlab-ci.yml").read_text(errors="replace")
            return "merge_request" in text
        except OSError:
            return None

    for filename in ["azure-pipelines.yml", "Jenkinsfile", ".circleci/config.yml", ".travis.yml",
                      "bitbucket-pipelines.yml"]:
        path = repo_path / filename
        if path.exists():
            try:
                text = path.read_text(errors="replace")
                return bool(re.search(r"pull.?request|merge.?request|pr[_ -]?trigger", text, re.IGNORECASE))
            except OSError:
                return None

    return None


def detect_gates(repo_path: Path, systems: list[str]) -> dict[str, bool]:
    combined_text = ""
    for text in _github_actions_configs(repo_path):
        combined_text += text + "\n"
    for filename in [".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile", ".circleci/config.yml", ".travis.yml"]:
        path = repo_path / filename
        if path.exists():
            try:
                combined_text += path.read_text(errors="replace") + "\n"
            except OSError:
                pass

    lowered = combined_text.lower()
    return {gate: any(re.search(p, lowered) for p in patterns) for gate, patterns in GATE_KEYWORDS.items()}


def collect(repo_path: Path) -> dict[str, dict]:
    repo_path = Path(repo_path)
    systems = detect_systems(repo_path)

    if not systems:
        reason = "no CI configuration file detected"
        return {
            "ci.systems_detected": _envelope([], "list", "ci_probe", "measured", 100, ""),
            "ci.runs_on_pr": _envelope(False, "bool", "ci_probe", "measured", 100, reason),
            "ci.gates": _envelope({"lint": False, "test": False, "coverage": False, "security": False, "build": False},
                                    "object", "ci_probe", "measured", 100, reason),
            "ci.success_rate_recent": _unavailable("no CI system detected"),
            "ci.avg_duration_s": _unavailable("no CI system detected"),
        }

    on_pr = runs_on_pr(repo_path, systems)
    gates = detect_gates(repo_path, systems)

    return {
        "ci.systems_detected": _envelope(systems, "list", "ci_probe", "measured", 100, ""),
        "ci.runs_on_pr": (
            _envelope(on_pr, "bool", "ci_probe", "derived", 100, "parsed trigger config where possible; substring heuristic otherwise")
            if on_pr is not None else _unavailable("could not parse trigger configuration for this CI system")
        ),
        "ci.gates": _envelope(gates, "object", "ci_probe", "derived", 100,
                                "keyword heuristic over job/step names — a job named unusually won't be detected"),
        "ci.success_rate_recent": _unavailable("requires the CI provider's API (network, out of scope for the default local-only pass)"),
        "ci.avg_duration_s": _unavailable("requires the CI provider's API (network, out of scope for the default local-only pass)"),
    }
