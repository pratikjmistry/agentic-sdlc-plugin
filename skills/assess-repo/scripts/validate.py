#!/usr/bin/env python3
"""Validate an assessment-inputs.json document against its JSON Schema.

Usage:
    python3 validate.py <path-to-assessment-inputs.json> [--schema <path>]

Exit code 0 and no output on success. Exit code 1 and one error per line on
stderr on failure. Importable as a module (see `validate()`) so collect.py and
score.py can validate in-process without shelling out.

Prefers the `jsonschema` package when installed (richer, path-qualified error
messages). Falls back to a dependency-free structural check covering the same
invariants (required top-level keys, all 80 required metric IDs present, each
metric envelope's required fields, confidence enum, and the
confidence=="unavailable" <=> value is None invariant) so this script never
hard-requires a pip install to run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCHEMA_PATH = SCRIPT_DIR / "schema" / "assessment-inputs.schema.json"

REQUIRED_TOP_LEVEL_KEYS = [
    "schema_version", "rubric_version", "assessment_id", "generated_at",
    "target", "providers", "exclusions", "human_inputs", "metrics",
]
REQUIRED_ENVELOPE_KEYS = ["value", "unit", "source", "confidence", "coverage_pct", "notes"]
VALID_CONFIDENCE = {"measured", "derived", "estimated", "unavailable"}


def _load_schema(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text())


def _required_metric_ids(schema: dict) -> list[str]:
    return list(schema.get("properties", {}).get("metrics", {}).get("required", []))


def _validate_with_jsonschema(data: dict, schema: dict) -> list[str]:
    import jsonschema  # type: ignore

    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]


def _validate_without_jsonschema(data: dict, schema: dict) -> list[str]:
    errors: list[str] = []

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            errors.append(f"<root>: missing required key '{key}'")

    metrics = data.get("metrics", {})
    if not isinstance(metrics, dict):
        errors.append("metrics: expected an object")
        return errors

    required_ids = _required_metric_ids(schema)
    for metric_id in required_ids:
        if metric_id not in metrics:
            errors.append(f"metrics: missing required metric '{metric_id}'")
            continue

        envelope = metrics[metric_id]
        if not isinstance(envelope, dict):
            errors.append(f"metrics/{metric_id}: expected an object envelope")
            continue

        for field in REQUIRED_ENVELOPE_KEYS:
            if field not in envelope:
                errors.append(f"metrics/{metric_id}: missing envelope field '{field}'")

        confidence = envelope.get("confidence")
        if confidence not in VALID_CONFIDENCE:
            errors.append(
                f"metrics/{metric_id}/confidence: '{confidence}' is not one of {sorted(VALID_CONFIDENCE)}"
            )

        if confidence == "unavailable":
            if envelope.get("value") is not None:
                errors.append(
                    f"metrics/{metric_id}: confidence is 'unavailable' but value is not null "
                    "— missing data must never look like measured data"
                )
            if envelope.get("coverage_pct") is not None:
                errors.append(
                    f"metrics/{metric_id}: confidence is 'unavailable' but coverage_pct is not null"
                )
        elif confidence in VALID_CONFIDENCE and envelope.get("value") is None:
            errors.append(
                f"metrics/{metric_id}: confidence is '{confidence}' but value is null "
                "— use confidence='unavailable' instead"
            )

    # Flag metric IDs present but not part of the required set — this schema is closed,
    # a stray key usually means a typo'd metric ID that will silently never be scored.
    for metric_id in metrics:
        if metric_id not in required_ids:
            errors.append(f"metrics/{metric_id}: not a recognized metric ID (possible typo)")

    return errors


def validate(data: dict, schema: dict | None = None) -> list[str]:
    """Return a list of human-readable error strings; empty list means valid."""
    schema = schema or _load_schema(DEFAULT_SCHEMA_PATH)
    try:
        return _validate_with_jsonschema(data, schema)
    except ImportError:
        return _validate_without_jsonschema(data, schema)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: validate.py <path-to-assessment-inputs.json> [--schema <path>]", file=sys.stderr)
        return 2

    target_path = Path(argv[0])
    schema_path = DEFAULT_SCHEMA_PATH
    if "--schema" in argv:
        schema_path = Path(argv[argv.index("--schema") + 1])

    data = json.loads(target_path.read_text())
    schema = _load_schema(schema_path)
    errors = validate(data, schema)

    if errors:
        print(f"✗ {target_path} failed validation ({len(errors)} error(s)):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
