"""Validate canonical files and compare them exactly with source aggregates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from preprocess.schema import validate_dataset


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_against_source(dataset_dir: Path, source_cutflow_path: Path) -> dict[str, Any]:
    manifest = _load(dataset_dir / "manifest.json")
    cuts = _load(dataset_dir / "cuts.json")
    summary = _load(dataset_dir / "summary.json")
    source = _load(source_cutflow_path)
    validate_dataset(manifest, cuts, summary)

    source_stages = {stage["id"]: stage for stage in source["stages"]}
    checks: list[dict[str, Any]] = []
    denominator = summary["cutflow"]["denominator"]["weighted_events"]
    expected_denominator = source["denominators"]["our_reproduction"]["weighted_events"]
    checks.append(
        {
            "name": "weighted_denominator_exact",
            "expected": expected_denominator,
            "observed": denominator,
            "passed": denominator == expected_denominator,
        }
    )
    for stage in summary["cutflow"]["stages"]:
        source_stage = source_stages[stage["cut_id"]]
        authors = source_stage["authors_recast_efficiency_pct"]
        expected_relative = None if authors in (None, 0) else (
            source_stage["our_efficiency_pct"] - authors
        ) / authors
        checks.extend(
            [
                {
                    "name": f"{stage['cut_id']}.weighted_events_exact",
                    "expected": source_stage["our_weighted_events"],
                    "observed": stage["n_after"],
                    "passed": stage["n_after"] == source_stage["our_weighted_events"],
                },
                {
                    "name": f"{stage['cut_id']}.efficiency_pct_exact",
                    "expected": source_stage["our_efficiency_pct"],
                    "observed": stage["cumulative_efficiency_pct"],
                    "passed": stage["cumulative_efficiency_pct"]
                    == source_stage["our_efficiency_pct"],
                },
                {
                    "name": f"{stage['cut_id']}.authors_reference_exact",
                    "expected": authors,
                    "observed": stage["reference"]["authors_recast_efficiency_pct"],
                    "passed": stage["reference"]["authors_recast_efficiency_pct"] == authors,
                },
                {
                    "name": f"{stage['cut_id']}.relative_difference_exact",
                    "expected": expected_relative,
                    "observed": stage["reference"][
                        "relative_difference_reproduction_vs_authors"
                    ],
                    "passed": stage["reference"][
                        "relative_difference_reproduction_vs_authors"
                    ]
                    == expected_relative,
                },
            ]
        )
    passed = all(check["passed"] for check in checks)
    report = {
        "dataset_id": manifest["dataset_id"],
        "schema_version": manifest["schema_version"],
        "internal_adapter_validation": "PASSED" if passed else "FAILED",
        "reference_reproduction_validation": "PASSED" if passed else "FAILED",
        "comparison_contract": "exact serialization agreement; no tolerance",
        "checks": checks,
        "external_reference_validation": summary["external_validation"],
        "capability_consistency": {
            "events_file_present": (dataset_dir / "events.json").exists(),
            "atomic_event_cuts": manifest["capabilities"]["atomic_event_cuts"],
            "jet_what_if": manifest["capabilities"]["jet_what_if"],
        },
    }
    if report["capability_consistency"]["events_file_present"]:
        raise ValueError("reference aggregate dataset must not contain events.json")
    if not passed:
        failed = [check["name"] for check in checks if not check["passed"]]
        raise ValueError(f"source/canonical disagreement: {failed}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--source-cutflow", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate_against_source(args.dataset_dir, args.source_cutflow)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
