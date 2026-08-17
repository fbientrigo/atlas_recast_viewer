"""Validate telemetry-only instrumentation against the same local recast run."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from preprocess.adapters.local_instrumented_reference import BOOLEAN_CUT_IDS, _event_passes
from preprocess.schema import validate_dataset, validate_events

LOG_LABELS = {
    "jet_selection": "High-pT Jet Selection [%]:",
    "fiducial_dv": "High-pT Fiducial [%]:",
    "rxy_gt_4_mm": "High-pT R_vertex > 4 mm [%]:",
    "d0_gt_2_mm": "High-pT Have track with |d_0| > 2 mm [%]:",
    "tracks_ge_5": "High-pT Selected Decay Product >= 5 [%]:",
    "mdv_gt_10_gev": "High-pT Invariant Mass > 10 GeV [%]:",
    "acceptance_x_efficiency": "High-pT Acc x Eff [%]:",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_token(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}\s+([-+0-9.eE]+)\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"missing log metric: {label}")
    return match.group(1)


def _without_clock(text: str) -> str:
    return re.sub(r"Now is \d{2} \w{3} \d{4} at \d{2}:\d{2}:\d{2}", "Now is <CLOCK>", text)


def validate_local(dataset_dir: Path, upstream_log: Path, instrumented_log: Path) -> dict[str, Any]:
    manifest = _load(dataset_dir / "manifest.json")
    cuts = _load(dataset_dir / "cuts.json")
    summary = _load(dataset_dir / "summary.json")
    events_doc = _load(dataset_dir / "events.json")
    validate_dataset(manifest, cuts, summary)
    validate_events(events_doc, manifest, cuts)

    upstream_text = upstream_log.read_text(encoding="utf-8")
    instrumented_text = instrumented_log.read_text(encoding="utf-8")
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "name": "nominal_stdout_exact_except_pythia_clock",
            "expected": "byte-identical after replacing only the Pythia wall-clock field",
            "observed": "identical" if _without_clock(upstream_text) == _without_clock(instrumented_text) else "different",
            "passed": _without_clock(upstream_text) == _without_clock(instrumented_text),
        }
    )

    events = events_doc["events"]
    denominator = sum(event["weight"] for event in events)
    for index, cut_id in enumerate(BOOLEAN_CUT_IDS, start=1):
        active = BOOLEAN_CUT_IDS[:index]
        after = sum(event["weight"] for event in events if _event_passes(event, active))
        computed = f"{100 * after / denominator:.6e}"
        source = _metric_token(upstream_text, LOG_LABELS[cut_id]).lower()
        checks.append(
            {"name": f"{cut_id}.telemetry_reproduces_printed_source", "expected": source, "observed": computed, "passed": computed == source}
        )

    response = sum(
        event["weight"] * event["response"]["event_eff"] * event["response"]["vertex_eff"]
        for event in events if _event_passes(event, BOOLEAN_CUT_IDS)
    )
    computed_response = f"{100 * response / denominator:.6e}"
    source_response = _metric_token(upstream_text, LOG_LABELS["acceptance_x_efficiency"]).lower()
    checks.append(
        {"name": "acceptance_x_efficiency.telemetry_reproduces_printed_source", "expected": source_response, "observed": computed_response, "passed": computed_response == source_response}
    )

    geometry_mismatches = sum(
        1 for event in events for vertex in event["vertices"]
        if abs(vertex["r_mm"] ** 2 - vertex["x_mm"] ** 2 - vertex["y_mm"] ** 2) > 1e-8
    )
    checks.append(
        {"name": "geometry_r_squared_exact_within_serialization_precision", "expected": 0, "observed": geometry_mismatches, "passed": geometry_mismatches == 0}
    )
    d0_mismatches = 0
    count_mismatches = 0
    for event in events:
        for vertex in event["vertices"]:
            selected = 0
            impacted = 0
            for track in vertex["tracks"]:
                phi_prod = math.atan2(track["y_prod_mm"], track["x_prod_mm"])
                phi_track = math.atan2(track["py_GeV"], track["px_GeV"])
                delta_phi = phi_prod - phi_track
                if abs(delta_phi) > math.pi:
                    delta_phi = 2 * math.pi - abs(delta_phi)
                expected_d0 = math.hypot(track["x_prod_mm"], track["y_prod_mm"]) * math.sin(delta_phi)
                d0_mismatches += int(not math.isclose(track["d0_mm"], expected_d0, rel_tol=1e-12, abs_tol=1e-12))
                selected += int(track["selected_for_dv"])
                impacted += int(track["passes_d0"])
            count_mismatches += int(selected != vertex["selected_track_count"] or impacted != vertex["impacted_track_count"])
    checks.append(
        {"name": "track_d0_geometry_reproduces_recast_proxy", "expected": 0, "observed": d0_mismatches, "passed": d0_mismatches == 0}
    )
    checks.append(
        {"name": "track_flags_reproduce_vertex_counts", "expected": 0, "observed": count_mismatches, "passed": count_mismatches == 0}
    )
    passed = all(check["passed"] for check in checks)
    public_summary_path = dataset_dir.parent / "reference" / "summary.json"
    public_comparison: dict[str, Any] | None = None
    if public_summary_path.is_file():
        public_summary = _load(public_summary_path)
        public_by_id = {stage["cut_id"]: stage for stage in public_summary["cutflow"]["stages"]}
        local_by_id = {stage["cut_id"]: stage for stage in summary["cutflow"]["stages"]}
        public_comparison = {}
        for cut_id in ("jet_selection", "mdv_gt_10_gev", "acceptance_x_efficiency"):
            local_pct = local_by_id[cut_id]["cumulative_efficiency_pct"]
            public_pct = public_by_id[cut_id]["cumulative_efficiency_pct"]
            public_comparison[cut_id] = {
                "local_0j_pct": local_pct,
                "public_inclusive_pct": public_pct,
                "relative_difference": (local_pct - public_pct) / public_pct,
                "interpretation": "context only; no validation tolerance",
            }
    report = {
        "dataset_id": manifest["dataset_id"],
        "schema_version": manifest["schema_version"],
        "instrumentation_regression": "PASSED" if passed else "FAILED",
        "event_adapter_validation": "PASSED" if passed else "FAILED",
        "comparison_contract": "exact normalized stdout plus exact six-significant-digit source output reproduction",
        "scope": "500-event reconstructed strong-bm1 0-parton teaching sample; not the inclusive public benchmark",
        "contextual_public_comparison": public_comparison,
        "checks": checks,
    }
    if not passed:
        raise ValueError(f"local instrumentation validation failed: {[c['name'] for c in checks if not c['passed']]}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--upstream-log", type=Path, required=True)
    parser.add_argument("--instrumented-log", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = validate_local(args.dataset_dir, args.upstream_log, args.instrumented_log)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
