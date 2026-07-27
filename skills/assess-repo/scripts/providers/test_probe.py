#!/usr/bin/env python3
"""Layer 1 provider: test capability (the `test.*` metric family).

Default mode is detect-only. `collect(..., attempt=True)` actually runs the
detected test command — only when the skill was run with --attempt-test
(which itself requires --attempt-build), after the caller has warned about
executing untrusted code.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

TEST_FILE_PATTERNS = [
    re.compile(r"(^|/)test_[^/]+\.py$"), re.compile(r"(^|/)[^/]+_test\.py$"),
    re.compile(r"(^|/)[^/]+\.test\.[jt]sx?$"), re.compile(r"(^|/)[^/]+\.spec\.[jt]sx?$"),
    re.compile(r"(^|/)[^/]+Test\.java$"), re.compile(r"(^|/)[^/]+Tests?\.cs$"),
    re.compile(r"(^|/)[^/]+_test\.go$"), re.compile(r"(^|/)[^/]+_spec\.rb$"),
    re.compile(r"(^|/)[^/]+Test\.php$"), re.compile(r"(^|/)test[^/]*\.php$"),
]

UNIT_DIR_HINTS = ["test", "tests", "spec", "specs", "__tests__"]
INTEGRATION_DIR_HINTS = ["integration", "integ", "it"]
E2E_DIR_HINTS = ["e2e", "cypress", "playwright", "features", "acceptance"]
FIXTURE_HINTS = ["fixtures", "factories", "seeds", "conftest.py"]

FLAKY_MARKER_PATTERN = re.compile(r"@flaky|@pytest\.mark\.flaky|pytest\.mark\.skip|xfail|\.retry\(|@Retry")


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _unavailable(notes: str) -> dict:
    return _envelope(None, "", "", "unavailable", None, notes)


def detect_frameworks(repo_path: Path, included_files: list[str]) -> list[str]:
    found = set()
    markers = {
        "pytest": ["pytest.ini", "conftest.py"],
        "jest": ["jest.config.js", "jest.config.ts", "jest.config.json"],
        "mocha": [".mocharc.json", ".mocharc.yml", ".mocharc.js"],
        "vitest": ["vitest.config.ts", "vitest.config.js"],
        "rspec": [".rspec"],
        "phpunit": ["phpunit.xml", "phpunit.xml.dist"],
    }
    for name, files in markers.items():
        if any((repo_path / f).exists() for f in files):
            found.add(name)

    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for candidate in ["jest", "mocha", "vitest", "cypress", "@playwright/test", "ava", "tape"]:
                if candidate in deps:
                    found.add(candidate)
        except (OSError, ValueError):
            pass

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
            data = tomllib.loads(pyproject.read_text())
            if "pytest" in json.dumps(data).lower():
                found.add("pytest")
        except Exception:
            pass

    if any(f.endswith("_test.go") for f in included_files):
        found.add("go test")
    if any(re.search(r"Test\.java$", f) for f in included_files):
        found.add("junit")
    if (repo_path / "Gemfile").exists() and "rspec" not in found:
        try:
            if "rspec" in (repo_path / "Gemfile").read_text(errors="replace"):
                found.add("rspec")
        except OSError:
            pass

    return sorted(found)


def count_test_files(included_files: list[str]) -> int:
    return sum(1 for f in included_files if any(p.search(f) for p in TEST_FILE_PATTERNS))


def _has_dir_hint(included_files: list[str], hints: list[str]) -> bool:
    for f in included_files:
        parts = f.lower().split("/")
        if any(h in parts for h in hints):
            return True
    return False


def detect_fixture_or_seed_data(repo_path: Path, included_files: list[str]) -> bool:
    if any((repo_path / "conftest.py").exists() for _ in [0]):
        return True
    return _has_dir_hint(included_files, FIXTURE_HINTS)


def count_flake_indicators(repo_path: Path, included_files: list[str], test_files: list[str]) -> int:
    count = 0
    for f in test_files[:500]:  # bounded — this is a heuristic signal, not exhaustive
        try:
            text = (repo_path / f).read_text(errors="replace")
        except OSError:
            continue
        count += len(FLAKY_MARKER_PATTERN.findall(text))
    return count


def _find_existing_coverage_report(repo_path: Path) -> tuple[float | None, str]:
    candidates = {
        "coverage.xml": "coverage.xml",
        ".coverage": ".coverage (sqlite, not parsed for a pct)",
        "coverage/lcov.info": "lcov.info",
        "coverage/coverage-summary.json": "coverage-summary.json",
    }
    for rel, label in candidates.items():
        path = repo_path / rel
        if not path.exists():
            continue
        if rel == "coverage.xml":
            try:
                text = path.read_text(errors="replace")
                m = re.search(r'line-rate="([\d.]+)"', text)
                if m:
                    return round(float(m.group(1)) * 100, 2), label
            except OSError:
                pass
        elif rel.endswith("coverage-summary.json"):
            try:
                data = json.loads(path.read_text())
                pct = data.get("total", {}).get("lines", {}).get("pct")
                if pct is not None:
                    return float(pct), label
            except (OSError, ValueError):
                pass
        return None, label  # found a report but couldn't parse a number out of it
    return None, ""


def attempt_test(repo_path: Path, frameworks: list[str]) -> dict:
    command: list[str] | None = None
    if "pytest" in frameworks:
        command = ["pytest", "-q", "--timeout=300"]
    elif "jest" in frameworks:
        command = ["npx", "jest", "--silent"]
    elif "go test" in frameworks:
        command = ["go", "test", "./..."]

    if command is None:
        return {"executes": False, "duration_s": None, "pass_rate": None, "stderr_tail": "no recognized test command to attempt"}

    start = time.monotonic()
    try:
        result = subprocess.run(command, cwd=repo_path, capture_output=True, text=True, timeout=540)
        duration = round(time.monotonic() - start, 1)
        return {"executes": True, "exit_code": result.returncode, "duration_s": duration,
                "stderr_tail": result.stderr[-2000:], "stdout_tail": result.stdout[-2000:]}
    except subprocess.TimeoutExpired:
        return {"executes": False, "duration_s": 540.0, "stderr_tail": "test run timed out after 540s"}
    except OSError as exc:
        return {"executes": False, "duration_s": None, "stderr_tail": str(exc)}


def collect(repo_path: Path, included_files: list[str], attempt: bool = False) -> dict[str, dict]:
    repo_path = Path(repo_path)
    frameworks = detect_frameworks(repo_path, included_files)
    test_files = [f for f in included_files if any(p.search(f) for p in TEST_FILE_PATTERNS)]
    test_count = len(test_files)
    non_test_count = max(1, len(included_files) - test_count)
    ratio = round(test_count / non_test_count, 3)

    metrics = {
        "test.frameworks_detected": _envelope(frameworks, "list", "test_probe", "derived", 100,
                                                "detect-only: config/manifest markers, not execution"),
        "test.test_file_count": _envelope(test_count, "count", "test_probe", "measured", 100, ""),
        "test.test_to_source_ratio": _envelope(ratio, "ratio", "test_probe", "derived", 100, ""),
        "test.unit_present": _envelope(_has_dir_hint(included_files, UNIT_DIR_HINTS) or test_count > 0,
                                         "bool", "test_probe", "derived", 100, ""),
        "test.integration_present": _envelope(_has_dir_hint(included_files, INTEGRATION_DIR_HINTS),
                                                "bool", "test_probe", "derived", 100,
                                                "directory-name heuristic (integration/, integ/, it/) — may undercount"),
        "test.e2e_present": _envelope(_has_dir_hint(included_files, E2E_DIR_HINTS),
                                        "bool", "test_probe", "derived", 100,
                                        "directory-name heuristic (e2e/, cypress/, playwright/, features/, acceptance/)"),
        "test.fixture_or_seed_data_present": _envelope(
            detect_fixture_or_seed_data(repo_path, included_files), "bool", "test_probe", "derived", 100, ""),
        "test.flake_indicators": _envelope(
            count_flake_indicators(repo_path, included_files, test_files), "count", "test_probe", "derived",
            min(100, round(100 * min(len(test_files), 500) / len(test_files), 2)) if test_files else 100,
            "static heuristic: @flaky/@pytest.mark.flaky/xfail/.retry(/@Retry markers in test source, bounded to first 500 test files",
        ),
    }

    coverage_pct, coverage_source = _find_existing_coverage_report(repo_path)
    if coverage_pct is not None:
        metrics["test.coverage_pct"] = _envelope(coverage_pct, "pct", "test_probe", "measured", 100,
                                                   f"parsed from a committed {coverage_source}")
        metrics["test.coverage_source"] = _envelope(coverage_source, "", "test_probe", "measured", 100, "")
    else:
        reason = (f"found a {coverage_source} but couldn't parse a percentage from it" if coverage_source
                   else "no committed coverage report found — requires --attempt-test to measure live")
        metrics["test.coverage_pct"] = _unavailable(reason)
        metrics["test.coverage_source"] = _unavailable(reason)

    if attempt:
        result = attempt_test(repo_path, frameworks)
        metrics["test.suite_executes"] = _envelope(result["executes"], "bool", "test_probe", "measured", 100, "")
        metrics["test.suite_duration_s"] = (
            _envelope(result["duration_s"], "seconds", "test_probe", "measured", 100, "")
            if result.get("duration_s") is not None else _unavailable("test run did not complete")
        )
        if result["executes"]:
            metrics["test.pass_rate"] = _unavailable(
                "exit code captured, but per-framework pass/fail parsing isn't implemented yet — "
                "see stderr_tail/stdout_tail in build.attempt-equivalent raw output for now"
            )
        else:
            metrics["test.pass_rate"] = _unavailable("suite did not execute")
    else:
        note = "detect-only mode — re-run with --attempt-test (requires --attempt-build) for a real signal"
        metrics["test.suite_executes"] = _unavailable(note)
        metrics["test.suite_duration_s"] = _unavailable(note)
        metrics["test.pass_rate"] = _unavailable(note)

    return metrics
