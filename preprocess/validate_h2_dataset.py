"""Validate an H2 mass-control dataset against the campaign's own artifacts.

Two things are checked with exact equality (no tolerance, since both sides
recompute from the identical serialized event CSVs):

1. The canonical ``summary.json`` cutflow at s=1.0 reproduces
   ``outputs/mass_control_cutflow.csv`` stage-by-stage.
2. The full discrete s-grid, recomputed independently in Python from the raw
   per-event CSVs via :func:`h2_mass_control.build_cutflow_stages`, matches
   the campaign's own precomputed grid for every ``(mass, s)`` pair.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from preprocess.adapters.h2_mass_control import (
    NEW_CAMPAIGN,
    build_cutflow_stages,
    discover_s_grid,
    load_mass,
)
from preprocess.schema import validate_dataset

CAMPAIGN_STAGE_TO_CUT_ID = {
    "Jet Selection": "jet_selection",
    "Fiducial": "fiducial_dv",
    "R_vertex > 4 mm": "rxy_gt_4_mm",
    "|d0| > 2 mm": "d0_gt_2_mm",
    "selected decay products >= 5": "tracks_ge_5",
    "invariant mass > 10 GeV": "mdv_gt_10_gev",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_campaign_rows(atlas_dihiggs_root: Path, mass: int) -> list[dict[str, str]]:
    path = atlas_dihiggs_root / NEW_CAMPAIGN / "outputs/mass_control_cutflow.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        return [row for row in csv.DictReader(stream) if int(row["mH2"]) == mass]


def validate_mass(atlas_dihiggs_root: Path, dataset_dir: Path, mass: int) -> dict[str, Any]:
    manifest = _load(dataset_dir / "manifest.json")
    cuts = _load(dataset_dir / "cuts.json")
    summary = _load(dataset_dir / "summary.json")
    validate_dataset(manifest, cuts, summary)
    if manifest["sample"]["mass_GeV"] != mass:
        raise ValueError(f"dataset mass mismatch: manifest says {manifest['sample']['mass_GeV']}, expected {mass}")

    events, _ = load_mass(atlas_dihiggs_root, mass)
    campaign_rows = _load_campaign_rows(atlas_dihiggs_root, mass)
    s_grid = discover_s_grid(atlas_dihiggs_root)

    checks: list[dict[str, Any]] = []

    # 1. baseline s=1 summary.json must match the campaign's own s=1.0 rows exactly.
    baseline_rows = {row["stage"]: row for row in campaign_rows if row["s"] == "1.0"}
    for stage in summary["cutflow"]["stages"]:
        if stage["cut_id"] == "acceptance_x_efficiency":
            expected = float(baseline_rows["final acceptance"]["weighted_numerator"])
            observed = stage["n_after"]
            checks.append(
                {
                    "name": "summary.acceptance_x_efficiency.weighted_numerator",
                    "expected": expected,
                    "observed": observed,
                    "passed": abs(observed - expected) < 1e-6,
                }
            )
            continue
        campaign_stage_name = next(
            name for name, cut_id in CAMPAIGN_STAGE_TO_CUT_ID.items() if cut_id == stage["cut_id"]
        )
        expected_n_after = float(baseline_rows[campaign_stage_name]["n_after"])
        checks.append(
            {
                "name": f"summary.{stage['cut_id']}.n_after",
                "expected": expected_n_after,
                "observed": stage["n_after"],
                "passed": stage["n_after"] == expected_n_after,
            }
        )

    # 2. full (mass, s) grid, recomputed independently from raw events.
    campaign_by_s_stage = {(row["s"], row["stage"]): row for row in campaign_rows}
    for s in s_grid:
        recomputed = build_cutflow_stages(events, scale=s)
        s_key = f"{s:.1f}"
        for stage in recomputed:
            if stage["cut_id"] == "acceptance_x_efficiency":
                expected = float(campaign_by_s_stage[(s_key, "final acceptance")]["weighted_numerator"])
                checks.append(
                    {
                        "name": f"grid.s={s_key}.acceptance_x_efficiency.weighted_numerator",
                        "expected": expected,
                        "observed": stage["n_after"],
                        "passed": abs(stage["n_after"] - expected) < 1e-6,
                    }
                )
                continue
            campaign_stage_name = next(
                name for name, cut_id in CAMPAIGN_STAGE_TO_CUT_ID.items() if cut_id == stage["cut_id"]
            )
            expected_n_after = float(campaign_by_s_stage[(s_key, campaign_stage_name)]["n_after"])
            checks.append(
                {
                    "name": f"grid.s={s_key}.{stage['cut_id']}.n_after",
                    "expected": expected_n_after,
                    "observed": stage["n_after"],
                    "passed": stage["n_after"] == expected_n_after,
                }
            )

    passed = all(check["passed"] for check in checks)
    report = {
        "dataset_id": manifest["dataset_id"],
        "mass_GeV": mass,
        "s_grid": s_grid,
        "n_events_full_campaign": len(events),
        "n_events_display_pack": manifest["n_events"],
        "internal_adapter_validation": "PASSED" if passed else "FAILED",
        "campaign_grid_validation": "PASSED" if passed else "FAILED",
        "comparison_contract": "exact equality on raw counts; 1e-6 tolerance on the weighted acceptance_x_efficiency numerator (floating-point summation order)",
        "checks": checks,
    }
    if not passed:
        failed = [check["name"] for check in checks if not check["passed"]]
        raise ValueError(f"H2 mass {mass}: campaign/canonical disagreement: {failed}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dihiggs-root", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--mass", type=int, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate_mass(args.atlas_dihiggs_root, args.dataset_dir, args.mass)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
