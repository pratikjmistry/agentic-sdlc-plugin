#!/usr/bin/env python3
"""Layer 1 provider: build capability (the `build.*` metric family).

Default mode is detect-only, per SKILL.md: infer capability from marker files
rather than executing anything. `collect(..., attempt=True)` actually runs the
detected build command — only ever invoked when the skill was run with
--attempt-build, which the caller is responsible for warning about (untrusted
code execution) before calling this with attempt=True.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

BUILD_SYSTEM_MARKERS = {
    "npm/yarn/pnpm": ["package.json"],
    "poetry": ["pyproject.toml"],  # refined further by content check below
    "pip/setuptools": ["setup.py", "setup.cfg"],
    "make": ["Makefile", "makefile", "GNUmakefile"],
    "maven": ["pom.xml"],
    "gradle": ["build.gradle", "build.gradle.kts"],
    "cargo": ["Cargo.toml"],
    "bundler": ["Gemfile"],
    "composer": ["composer.json"],
    "cmake": ["CMakeLists.txt"],
    "go": ["go.mod"],
    "dotnet": [],  # detected via glob below (*.csproj/*.sln), not a fixed name
}

LOCKFILE_NAMES = [
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
    "Pipfile.lock", "Gemfile.lock", "Cargo.lock", "composer.lock", "go.sum",
]

BUILD_HEADING_PATTERN = re.compile(r"^#{1,4}\s*(build|install|setup|getting started|quickstart)", re.IGNORECASE)


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _exists(repo_path: Path, *names: str) -> bool:
    return any((repo_path / n).exists() for n in names)


def _glob_any(repo_path: Path, pattern: str) -> bool:
    try:
        return next(repo_path.glob(pattern), None) is not None
    except OSError:
        return False


def detect_systems(repo_path: Path) -> list[str]:
    found = []
    for name, markers in BUILD_SYSTEM_MARKERS.items():
        if markers and _exists(repo_path, *markers):
            found.append(name)
    if _glob_any(repo_path, "*.csproj") or _glob_any(repo_path, "*.sln"):
        found.append("dotnet")
    if _glob_any(repo_path, "*.dproj") or _glob_any(repo_path, "*.dpr"):
        found.append("delphi")
    return sorted(set(found))


def is_containerized(repo_path: Path) -> bool:
    return _exists(repo_path, "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
                    "compose.yml", "compose.yaml")


def has_devcontainer(repo_path: Path) -> bool:
    return (repo_path / ".devcontainer").is_dir() or (repo_path / ".devcontainer.json").exists()


def has_lockfiles(repo_path: Path) -> bool:
    return _exists(repo_path, *LOCKFILE_NAMES)


def _readme_documents_one_command_build(repo_path: Path) -> bool:
    for name in ["README.md", "README.rst", "README.txt", "readme.md"]:
        path = repo_path / name
        if not path.exists():
            continue
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        in_relevant_section = False
        for i, line in enumerate(lines):
            if line.startswith("#"):
                in_relevant_section = bool(BUILD_HEADING_PATTERN.match(line))
                continue
            if in_relevant_section and line.strip().startswith("```"):
                # a fenced code block appearing under a build/install/setup heading
                # is treated as "a documented command", regardless of line count —
                # multi-line fences are still "documented", just not scored as high.
                return True
    return False


def one_command_build_documented(repo_path: Path, containerized: bool, devcontainer: bool) -> bool:
    if containerized or devcontainer:
        return True  # `docker build .` / devcontainer CLI is itself the one command
    if (repo_path / "Makefile").exists() or (repo_path / "makefile").exists():
        return True  # `make` alone
    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            import json
            data = json.loads(package_json.read_text())
            if "build" in data.get("scripts", {}):
                return True
        except (OSError, ValueError):
            pass
    return _readme_documents_one_command_build(repo_path)


def required_env_var_count(repo_path: Path) -> int:
    for name in [".env.example", ".env.sample", ".env.template", ".env.dist"]:
        path = repo_path / name
        if path.exists():
            try:
                lines = path.read_text(errors="replace").splitlines()
            except OSError:
                continue
            return sum(1 for ln in lines if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", ln.strip()))
    return 0


def external_service_deps(repo_path: Path) -> list[str]:
    for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
        path = repo_path / name
        if not path.exists():
            continue
        try:
            import yaml
            data = yaml.safe_load(path.read_text())
            services = list((data or {}).get("services", {}).keys())
            return sorted(services)
        except Exception:
            return []
    return []


def attempt_build(repo_path: Path, systems: list[str], containerized: bool) -> dict:
    """Only called when the caller has already warned about untrusted code
    execution and the user passed --attempt-build."""
    command: list[str] | None = None
    if containerized and (repo_path / "Dockerfile").exists():
        command = ["docker", "build", "."]
    elif "make" in systems:
        command = ["make"]
    elif "npm/yarn/pnpm" in systems:
        command = ["npm", "install"]
    elif "poetry" in systems:
        command = ["poetry", "install"]

    if command is None:
        return {"attempted": False, "exit_code": None, "duration_s": None,
                "stderr_tail": "no recognized one-command build path to attempt"}

    import time
    start = time.monotonic()
    try:
        result = subprocess.run(command, cwd=repo_path, capture_output=True, text=True, timeout=540)
        duration = round(time.monotonic() - start, 1)
        return {"attempted": True, "exit_code": result.returncode, "duration_s": duration,
                "stderr_tail": result.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {"attempted": True, "exit_code": None, "duration_s": 540.0, "stderr_tail": "build timed out after 540s"}
    except OSError as exc:
        return {"attempted": True, "exit_code": None, "duration_s": None, "stderr_tail": str(exc)}


def collect(repo_path: Path, attempt: bool = False) -> dict[str, dict]:
    repo_path = Path(repo_path)
    systems = detect_systems(repo_path)
    containerized = is_containerized(repo_path)
    devcontainer = has_devcontainer(repo_path)
    one_command = one_command_build_documented(repo_path, containerized, devcontainer)
    lockfiles = has_lockfiles(repo_path)

    attempt_result = (
        attempt_build(repo_path, systems, containerized) if attempt
        else {"attempted": False, "exit_code": None, "duration_s": None, "stderr_tail": ""}
    )

    detect_note = "detect-only: inferred from marker files, not executed" if not attempt else "build was attempted"

    return {
        "build.detected_systems": _envelope(systems, "list", "build_probe", "derived", 100, detect_note),
        "build.containerized": _envelope(containerized, "bool", "build_probe", "measured", 100, ""),
        "build.devcontainer_present": _envelope(devcontainer, "bool", "build_probe", "measured", 100, ""),
        "build.one_command_build_documented": _envelope(
            one_command, "bool", "build_probe", "derived", 100,
            "heuristic: containerized/devcontainer, a bare Makefile, an npm 'build' script, or a "
            "fenced code block under a Build/Install/Setup/Getting Started README heading",
        ),
        "build.lockfiles_present": _envelope(lockfiles, "bool", "build_probe", "measured", 100, ""),
        "build.required_env_var_count": _envelope(
            required_env_var_count(repo_path), "count", "build_probe", "derived", 100,
            "counted from .env.example/.env.sample/.env.template if present; 0 if none found (not necessarily 'zero env vars needed')",
        ),
        "build.external_service_deps": _envelope(
            external_service_deps(repo_path), "list", "build_probe", "derived", 100,
            "service names from docker-compose.yml, if present",
        ),
        "build.attempt": _envelope(attempt_result, "object", "build_probe",
                                     "measured" if attempt else "measured", 100, detect_note),
    }
