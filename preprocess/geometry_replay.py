"""Merge telemetry-only H2 replay output into a canonical geometry pack.

Consumes the frozen selection manifest (`preprocess/geometry_selection.py`)
and the NDJSON telemetry emitted by
`preprocess/instrumentation/h2_recast_2301_13866_telemetry.cc`, cross-checks
every selected event against the frozen campaign `events.csv` (Section 19's
regression gate) and against an independent mDV recomputation (Section 18),
and writes `geometry_events.json` plus a `manifest.geometry_pack` patch.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from preprocess import SCHEMA_VERSION
from preprocess.adapters.h2_mass_control import _campaign_dir_for_mass
from preprocess.schema import validate_events

CHARGED_PION_MASS_GEV = 0.13957039
FLOAT_REL_TOL = 1e-9  # looser than Gate 1's proven 1e-12 to absorb JSON text round-tripping


def selected_indices_by_subrun(selection: dict[str, Any]) -> dict[int, list[int]]:
    by_subrun: dict[int, list[int]] = {}
    for event in selection["events"]:
        by_subrun.setdefault(event["subrun"], []).append(event["source_event_index"])
    return by_subrun


def write_index_files(selection: dict[str, Any], output_dir: Path) -> dict[int, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for subrun, indices in selected_indices_by_subrun(selection).items():
        path = output_dir / f"selected_subrun{subrun}.txt"
        path.write_text("\n".join(str(i) for i in sorted(indices)) + "\n", encoding="utf-8")
        paths[subrun] = path
    return paths


def seed_cmnd_paths(atlas_dihiggs_root: Path, mass: int) -> dict[int, Path]:
    """subrun (0/1, ascending seed order) -> frozen .cmnd card path."""

    campaign = atlas_dihiggs_root / _campaign_dir_for_mass(mass)
    runs_dir = campaign / "runs/main" / f"mH{mass}"
    seed_dirs = sorted(runs_dir.glob("seed_*"))
    result = {}
    for subrun, seed_dir in enumerate(seed_dirs):
        seed_number = int(seed_dir.name.split("_")[1])
        result[subrun] = campaign / "cards" / f"mH{mass}_ctau4p326_s{seed_number}.cmnd"
    return result


def seed_events_csv_paths(atlas_dihiggs_root: Path, mass: int) -> dict[int, Path]:
    campaign = atlas_dihiggs_root / _campaign_dir_for_mass(mass)
    runs_dir = campaign / "runs/main" / f"mH{mass}"
    seed_dirs = sorted(runs_dir.glob("seed_*"))
    return {subrun: seed_dir / "events.csv" for subrun, seed_dir in enumerate(seed_dirs)}


def _load_telemetry(path: Path) -> dict[int, dict[str, Any]]:
    """source_event_index -> telemetry record, for one seed's ndjson file."""

    records: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            records[record["source_event_index"]] = record
    return records


def _canonical_event_id(subrun: int, source_event_index: int) -> int:
    return subrun * 10_000 + source_event_index


def _jets_rank_4_7(telemetry_jets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"rank": jet["rank"], "pt_GeV": jet["pt_GeV"], "eta": jet["eta"], "phi": jet["phi"]}
        for jet in telemetry_jets
        if 4 <= jet["rank"] <= 7
    ]


def build_geometry_events_doc(dataset_id: str, selection: dict[str, Any], telemetry_by_subrun: dict[int, dict[int, dict[str, Any]]]) -> dict[str, Any]:
    events = []
    for sel in selection["events"]:
        subrun, idx = sel["subrun"], sel["source_event_index"]
        record = telemetry_by_subrun[subrun][idx]
        if not record["valid_weight"]:
            raise ValueError(f"selected event subrun={subrun} idx={idx} has valid_weight=false in telemetry")
        events.append(
            {
                "event_id": _canonical_event_id(subrun, idx),
                "subrun": subrun,
                "source_event_index": idx,
                "weight": 1.0,  # canonical raw-count convention, matching events.json (see cuts.json unit_conventions)
                "source_weight_mb": None,
                "valid_weight": True,
                "observables": record["observables"],
                "predicates": record["predicates"],
                "response": record["response"],
                "jets": _jets_rank_4_7(record["jets"]),
                "vertices": record["vertices"],
            }
        )
    events.sort(key=lambda e: e["event_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "selection_semantics": {
            "boolean_counterfactual": "recomputed from event jet predicate and event-scoped DV atomic predicates, same as events.json",
            "vertex_combination": "genuine per-LLP breakdown recovered by telemetry replay for this curated pack only; event.predicates remains the authoritative boolean per DATA_CONTRACT.md (predicate_scope=event)",
            "response_counterfactual": "not defined; response weighting remains the published baseline operation",
            "geometry": "real: recovered by deterministic Mode-B telemetry replay of the frozen campaign LHE/seed/cmnd for exactly these 100 curated events (see docs/H2_GEOMETRY_REPLAY_CONTRACT.md)",
            "tracks": "real: charged final daughters of the matched LLP, with the exact recast d0 proxy",
            "d0": "exact recast proxy: rTrack * sin(deltaPhi), identical formula to local-reference",
        },
        "events": events,
    }


def _recompute_mdv(vertex: dict[str, Any]) -> float:
    e_total = px = py = pz = 0.0
    for track in vertex["tracks"]:
        if not track["selected_for_dv"]:
            continue
        p2 = track["px_GeV"] ** 2 + track["py_GeV"] ** 2 + track["pz_GeV"] ** 2
        e_total += math.sqrt(p2 + CHARGED_PION_MASS_GEV**2)
        px += track["px_GeV"]
        py += track["py_GeV"]
        pz += track["pz_GeV"]
    m2 = e_total**2 - px**2 - py**2 - pz**2
    return math.sqrt(m2) if m2 > 0 else 0.0


def regression_report(
    mass: int,
    selection: dict[str, Any],
    telemetry_by_subrun: dict[int, dict[int, dict[str, Any]]],
    csv_rows_by_subrun: dict[int, dict[int, dict[str, str]]],
) -> dict[str, Any]:
    identity_matches = cut_predicate_matches = jet_matches = r_matches = d0_matches = 0
    ntracks_matches = mdv_matches = response_matches = 0
    failures: list[dict[str, Any]] = []

    for sel in selection["events"]:
        subrun, idx = sel["subrun"], sel["source_event_index"]
        telemetry = telemetry_by_subrun[subrun][idx]
        row = csv_rows_by_subrun[subrun][idx]
        local_failures = []

        if telemetry["source_event_index"] != idx or telemetry["subrun"] != subrun:
            local_failures.append("identity")
        else:
            identity_matches += 1

        predicate_pairs = [
            ("jet_selection", "trackless_selected"),
            ("trackless_additional", "trackless_additional"),
            ("fiducial_dv", "pass_fiducial"),
            ("rxy_gt_4_mm", "pass_rvtx4"),
            ("d0_gt_2_mm", "pass_d0"),
            ("tracks_ge_5", "pass_ndecay5"),
            ("mdv_gt_10_gev", "pass_mdv10"),
        ]
        predicate_ok = all(
            telemetry["predicates"][tel_key] == (row[csv_key] == "1")
            for tel_key, csv_key in predicate_pairs
        )
        if predicate_ok:
            cut_predicate_matches += 1
        else:
            local_failures.append("predicates")

        csv_jet_pt = {4: float(row["jet4_pt"]), 5: float(row["jet5_pt"]), 6: float(row["jet6_pt"]), 7: float(row["jet7_pt"])}
        telemetry_jet_pt = {jet["rank"]: jet["pt_GeV"] for jet in telemetry["jets"] if 4 <= jet["rank"] <= 7}
        jets_ok = all(
            (csv_jet_pt[r] == -1 and r not in telemetry_jet_pt)
            or (r in telemetry_jet_pt and math.isclose(csv_jet_pt[r], telemetry_jet_pt[r], rel_tol=FLOAT_REL_TOL))
            for r in (4, 5, 6, 7)
        )
        if jets_ok:
            jet_matches += 1
        else:
            local_failures.append("jets")

        r_ok = math.isclose(telemetry["observables"]["r_max_mm"], float(row["r_max"]), rel_tol=FLOAT_REL_TOL, abs_tol=1e-9)
        if r_ok:
            r_matches += 1
        else:
            local_failures.append("r_max")

        response_ok = (
            math.isclose(telemetry["response"]["vertex_eff"], float(row["v_eff"]), rel_tol=FLOAT_REL_TOL, abs_tol=1e-9)
            and math.isclose(telemetry["response"]["event_eff"], float(row["event_eff_trackless"]), rel_tol=FLOAT_REL_TOL, abs_tol=1e-9)
        )
        if response_ok:
            response_matches += 1
        else:
            local_failures.append("response")

        d0_ok = True
        ntracks_ok = True
        mdv_ok = True
        for vertex in telemetry["vertices"]:
            selected = sum(1 for t in vertex["tracks"] if t["selected_for_dv"])
            impacted = sum(1 for t in vertex["tracks"] if t["passes_d0"])
            if selected != vertex["selected_track_count"] or impacted != vertex["impacted_track_count"]:
                ntracks_ok = False
            for track in vertex["tracks"]:
                delta_phi = math.atan2(track["y_prod_mm"], track["x_prod_mm"]) - track["phi"]
                if abs(delta_phi) > math.pi:
                    delta_phi = 2 * math.pi - abs(delta_phi)
                expected_d0 = math.hypot(track["x_prod_mm"], track["y_prod_mm"]) * math.sin(delta_phi)
                if not math.isclose(track["d0_mm"], expected_d0, rel_tol=1e-9, abs_tol=1e-9):
                    d0_ok = False
            recomputed_mdv = _recompute_mdv(vertex)
            if not math.isclose(recomputed_mdv, vertex["mass_GeV"], rel_tol=1e-6, abs_tol=1e-6):
                mdv_ok = False
        if d0_ok:
            d0_matches += 1
        else:
            local_failures.append("d0")
        if ntracks_ok:
            ntracks_matches += 1
        else:
            local_failures.append("ntracks")
        if mdv_ok:
            mdv_matches += 1
        else:
            local_failures.append("mdv")

        if local_failures:
            failures.append({"subrun": subrun, "source_event_index": idx, "failed_checks": local_failures})

    total = len(selection["events"])
    return {
        "mass_GeV": mass,
        "selected": total,
        "replayed": total,
        "telemetry_records": total,
        "identity_matches": identity_matches,
        "cut_predicate_matches": cut_predicate_matches,
        "jet_matches": jet_matches,
        "r_matches": r_matches,
        "d0_matches": d0_matches,
        "ntracks_matches": ntracks_matches,
        "mdv_matches": mdv_matches,
        "response_matches": response_matches,
        "failures": failures,
    }


def _read_csv_rows(path: Path) -> dict[int, dict[str, str]]:
    rows = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            rows[int(row["event"])] = row
    return rows


def build_and_validate(
    atlas_dihiggs_root: Path,
    mass: int,
    selection_path: Path,
    telemetry_paths: dict[int, Path],
    dataset_dir: Path,
) -> dict[str, Any]:
    dataset_id = f"h2-m{mass}"
    selection = json.loads(selection_path.read_text())
    if selection["mass_GeV"] != mass:
        raise ValueError("selection manifest mass mismatch")

    telemetry_by_subrun = {subrun: _load_telemetry(path) for subrun, path in telemetry_paths.items()}
    csv_paths = seed_events_csv_paths(atlas_dihiggs_root, mass)
    csv_rows_by_subrun = {subrun: _read_csv_rows(path) for subrun, path in csv_paths.items()}

    report = regression_report(mass, selection, telemetry_by_subrun, csv_rows_by_subrun)
    if report["failures"]:
        raise ValueError(f"h2-m{mass} geometry replay regression failures: {report['failures']}")

    geometry_doc = build_geometry_events_doc(dataset_id, selection, telemetry_by_subrun)

    manifest = json.loads((dataset_dir / "manifest.json").read_text())
    cuts_doc = json.loads((dataset_dir / "cuts.json").read_text())
    cohort_summary = {}
    for event in selection["events"]:
        cohort_summary[event["cohort"]] = cohort_summary.get(event["cohort"], 0) + 1
    manifest["geometry_pack"] = {
        "event_count": len(geometry_doc["events"]),
        "selection_method": "curated_pedagogical_cohorts",
        "replay_mode": "B",
        "cohort_summary": cohort_summary,
    }
    # The on-disk manifest.capabilities.dv_radial/dv_xyz describe events.json
    # (still genuinely false: no geometry there). geometry_events.json has
    # real coordinates, so validate it against a capabilities override,
    # exactly mirroring the frontend's App.svelte geometryPanelCapabilities.
    geometry_manifest = {**manifest, "capabilities": {**manifest["capabilities"], "dv_radial": True, "dv_xyz": True}}
    validate_events(
        geometry_doc, geometry_manifest, cuts_doc,
        expected_count=manifest["geometry_pack"]["event_count"], file_name="geometry_events.json",
    )

    (dataset_dir / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    (dataset_dir / "geometry_events.json").write_text(
        json.dumps(geometry_doc, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dihiggs-root", type=Path, required=True)
    parser.add_argument("--mass", type=int, required=True)
    parser.add_argument("--selection-path", type=Path, required=True)
    parser.add_argument("--telemetry", action="append", required=True, help="subrun:path, repeatable")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    telemetry_paths = {}
    for item in args.telemetry:
        subrun_str, path_str = item.split(":", 1)
        telemetry_paths[int(subrun_str)] = Path(path_str)

    report = build_and_validate(args.atlas_dihiggs_root, args.mass, args.selection_path, telemetry_paths, args.dataset_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"mass {args.mass}: {report['identity_matches']}/{report['selected']} identity, "
          f"{report['cut_predicate_matches']}/{report['selected']} predicates, "
          f"{len(report['failures'])} failures -> {args.report}")
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
