#!/usr/bin/env python3
"""Layer 1 provider: dependency metrics (the `deps.*` metric family).

Manifest/lockfile parsing is fully local. `eol_components`,
`median_majors_behind`, and `known_vuln_count_by_severity` all require
querying an external database (endoflife.date, package registries, an
advisory database) — real network access this plugin never assumes by
default, and exactly the kind of provider `--policy` is meant to gate. All
three are reported `unavailable` with that reason rather than guessed at.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MANIFEST_FILES = [
    "package.json", "requirements.txt", "pyproject.toml", "Gemfile", "go.mod",
    "pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "Cargo.toml",
]


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _unavailable(notes: str) -> dict:
    return _envelope(None, "", "", "unavailable", None, notes)


def count_manifests(repo_path: Path) -> int:
    return sum(1 for f in MANIFEST_FILES if (repo_path / f).exists())


def _direct_count_npm(repo_path: Path) -> int | None:
    path = repo_path / "package.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return len(data.get("dependencies", {})) + len(data.get("devDependencies", {}))
    except (OSError, ValueError):
        return None


def _direct_count_python(repo_path: Path) -> int | None:
    req = repo_path / "requirements.txt"
    if req.exists():
        try:
            lines = req.read_text(errors="replace").splitlines()
            return sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#") and not ln.strip().startswith("-"))
        except OSError:
            pass
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
            data = tomllib.loads(pyproject.read_text())
            deps = data.get("project", {}).get("dependencies", [])
            poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            count = len(deps) + max(0, len(poetry_deps) - (1 if "python" in poetry_deps else 0))
            if count:
                return count
        except Exception:
            pass
    return None


def _direct_count_go(repo_path: Path) -> int | None:
    path = repo_path / "go.mod"
    if not path.exists():
        return None
    try:
        text = path.read_text(errors="replace")
        return len(re.findall(r"^\s*[\w./-]+\s+v[\d.]+", text, re.MULTILINE))
    except OSError:
        return None


def _direct_count_ruby(repo_path: Path) -> int | None:
    path = repo_path / "Gemfile"
    if not path.exists():
        return None
    try:
        text = path.read_text(errors="replace")
        return len(re.findall(r"^\s*gem\s+['\"]", text, re.MULTILINE))
    except OSError:
        return None


def _direct_count_cargo(repo_path: Path) -> int | None:
    path = repo_path / "Cargo.toml"
    if not path.exists():
        return None
    try:
        import tomllib
        data = tomllib.loads(path.read_text())
        return len(data.get("dependencies", {}))
    except Exception:
        return None


def direct_count(repo_path: Path) -> tuple[int | None, str]:
    for fn, label in [
        (_direct_count_npm, "package.json"), (_direct_count_python, "requirements.txt/pyproject.toml"),
        (_direct_count_go, "go.mod"), (_direct_count_ruby, "Gemfile"), (_direct_count_cargo, "Cargo.toml"),
    ]:
        result = fn(repo_path)
        if result is not None:
            return result, label
    return None, ""


def _npm_lockfile_packages(repo_path: Path) -> dict[str, list[str]] | None:
    """Returns {package_name: [resolved_versions_seen]} from package-lock.json,
    or None if no npm lockfile / unparseable."""
    path = repo_path / "package-lock.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None

    packages: dict[str, list[str]] = {}
    for key, entry in data.get("packages", {}).items():
        if not key or not isinstance(entry, dict):
            continue
        name = key.rsplit("node_modules/", 1)[-1]
        version = entry.get("version")
        if name and version:
            packages.setdefault(name, []).append(version)
    if packages:
        return packages

    def walk(deps: dict):
        for name, entry in (deps or {}).items():
            if isinstance(entry, dict):
                version = entry.get("version")
                if version:
                    packages.setdefault(name, []).append(version)
                walk(entry.get("dependencies", {}))
    walk(data.get("dependencies", {}))
    return packages or None


def _python_lockfile_packages(repo_path: Path) -> dict[str, list[str]] | None:
    """poetry.lock or uv.lock — both are TOML with a top-level array of [[package]]."""
    for filename in ["uv.lock", "poetry.lock"]:
        path = repo_path / filename
        if not path.exists():
            continue
        try:
            import tomllib
            data = tomllib.loads(path.read_text())
        except Exception:
            continue
        packages: dict[str, list[str]] = {}
        for pkg in data.get("package", []):
            name, version = pkg.get("name"), pkg.get("version")
            if name and version:
                packages.setdefault(name, []).append(version)
        if packages:
            return packages
    return None


def transitive_and_duplicates(repo_path: Path, direct: int | None) -> tuple[int | None, list[dict], str]:
    packages = _npm_lockfile_packages(repo_path) or _python_lockfile_packages(repo_path)
    if packages is None:
        return None, [], ""

    total = len(packages)
    transitive = max(0, total - (direct or 0))

    duplicates = []
    for name, versions in packages.items():
        distinct = sorted(set(versions))
        majors = sorted({v.split(".")[0] for v in distinct if v and v[0].isdigit()})
        if len(majors) > 1:
            duplicates.append({"name": name, "versions": distinct, "majors": majors})

    source = "package-lock.json" if _npm_lockfile_packages(repo_path) is not None else "poetry.lock/uv.lock"
    return transitive, duplicates, source


def collect(repo_path: Path) -> dict[str, dict]:
    repo_path = Path(repo_path)
    manifest_count = count_manifests(repo_path)
    direct, direct_source = direct_count(repo_path)
    transitive, duplicates, lock_source = transitive_and_duplicates(repo_path, direct)

    metrics = {
        "deps.manifest_count": _envelope(manifest_count, "count", "deps_probe", "measured", 100, ""),
    }

    if direct is not None:
        metrics["deps.direct_count"] = _envelope(direct, "count", "deps_probe", "measured", 100, f"from {direct_source}")
    else:
        metrics["deps.direct_count"] = _unavailable("no recognized manifest with a parseable dependency list")

    if transitive is not None:
        metrics["deps.transitive_count"] = _envelope(transitive, "count", "deps_probe", "derived", 100,
                                                        f"resolved package count from {lock_source} minus direct_count")
        metrics["deps.duplicate_framework_versions"] = _envelope(
            duplicates, "list", "deps_probe", "derived", 100,
            "any package name resolving to 2+ distinct major versions simultaneously in the lockfile",
        )
    else:
        reason = "no parseable lockfile found (package-lock.json, poetry.lock, or uv.lock)"
        metrics["deps.transitive_count"] = _unavailable(reason)
        metrics["deps.duplicate_framework_versions"] = _unavailable(reason)

    metrics["deps.eol_components"] = _unavailable(
        "requires querying an EOL database (e.g. endoflife.date) — network access, gated by client policy, not implemented in Phase 0's default local-only pass")
    metrics["deps.median_majors_behind"] = _unavailable(
        "requires querying package registries for latest versions — network access, not implemented in Phase 0's default local-only pass")
    metrics["deps.known_vuln_count_by_severity"] = _unavailable(
        "requires a vulnerability database (OSV/GitHub Advisory/npm audit/pip-audit) — network access, not implemented in Phase 0's default local-only pass")

    return metrics
