"""Deterministic pedagogical top-100 event selector for H2 geometry packs.

Selects, per mass, 100 events from the full canonical 20000-event statistics
population (the same population `h2_mass_control.build_cutflow_stages` uses),
stratified into cohorts chosen for teaching/coverage value, never for
acceptance or response weight (see gauntlet Section 5/8). The selection is a
pure function of the frozen campaign CSVs: identical output on every run
(Section 14), and is persisted before any replay/telemetry step touches the
selected events (Section 13).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from preprocess.adapters.h2_mass_control import (
    ALL_MASSES,
    MISSING_JET_SENTINEL,
    TRACKLESS_THRESHOLDS_GEV,
    _campaign_dir_for_mass,
    discover_s_grid,
    jet_selection_pass,
    load_mass,
)

SEQUENTIAL_CUT_ORDER = [
    "jet_selection",
    "fiducial_dv",
    "rxy_gt_4_mm",
    "d0_gt_2_mm",
    "tracks_ge_5",
    "mdv_gt_10_gev",
]
_SEQUENTIAL_COLUMN = {
    "fiducial_dv": "pass_fiducial",
    "rxy_gt_4_mm": "pass_rvtx4",
    "d0_gt_2_mm": "pass_d0",
    "tracks_ge_5": "pass_ndecay5",
    "mdv_gt_10_gev": "pass_mdv10",
}

COHORT_QUOTAS: dict[str, int] = {
    "accepted_baseline": 20,
    "fail_jet_selection_s1": 15,
    "jet_borderline_s1": 10,
    "s_sensitive": 10,
    "first_fail_r_dv": 10,
    "first_fail_d0": 10,
    "first_fail_ntracks": 10,
    "first_fail_mdv": 10,
    "unusual_coverage": 5,
}
assert sum(COHORT_QUOTAS.values()) == 100

_FIRST_FAIL_TO_COHORT = {
    "jet_selection": "fail_jet_selection_s1",
    "rxy_gt_4_mm": "first_fail_r_dv",
    "d0_gt_2_mm": "first_fail_d0",
    "tracks_ge_5": "first_fail_ntracks",
    "mdv_gt_10_gev": "first_fail_mdv",
}

# Deterministic redistribution chains for Section 8's deficit handling: the
# first entry with spare eligible events (beyond its own quota) absorbs the
# shortfall, honestly labeled as that fallback cohort (never mislabeled as
# the deficient cohort). Ordering follows sequential cut adjacency.
FALLBACK_CHAIN: dict[str, list[str]] = {
    "accepted_baseline": ["fail_jet_selection_s1"],
    "fail_jet_selection_s1": ["accepted_baseline"],
    "jet_borderline_s1": ["s_sensitive", "accepted_baseline"],
    "s_sensitive": ["jet_borderline_s1", "accepted_baseline"],
    "first_fail_r_dv": ["first_fail_d0", "first_fail_ntracks", "first_fail_mdv", "accepted_baseline"],
    "first_fail_d0": ["first_fail_r_dv", "first_fail_ntracks", "first_fail_mdv", "accepted_baseline"],
    "first_fail_ntracks": ["first_fail_d0", "first_fail_mdv", "first_fail_r_dv", "accepted_baseline"],
    "first_fail_mdv": ["first_fail_ntracks", "first_fail_d0", "first_fail_r_dv", "accepted_baseline"],
    "unusual_coverage": ["accepted_baseline"],
}


def first_failed_cut(event: dict[str, Any]) -> str | None:
    """Sequential first-failure semantics (Section 9); None means fully accepted."""

    if not jet_selection_pass(event, 1.0):
        return "jet_selection"
    for cut_id in SEQUENTIAL_CUT_ORDER[1:]:
        if not event[_SEQUENTIAL_COLUMN[cut_id]]:
            return cut_id
    return None


def x_max(event: dict[str, Any]) -> float | None:
    """Generic normalized jet variable (Section 10); None if no real jet is present."""

    values = [
        event["jet_pt_GeV"][rank] / threshold
        for rank, threshold in TRACKLESS_THRESHOLDS_GEV.items()
        if event["jet_pt_GeV"][rank] != MISSING_JET_SENTINEL
    ]
    return max(values) if values else None


def s_transition(event: dict[str, Any], s_grid: list[float]) -> float | None:
    """Largest s<1.0 at which the ordinary OR first becomes true (Section 11).

    None if the event's additional-leg predicate never lets it pass at any
    grid s, or if it already passes at s=1 (no transition to find).
    """

    if not event["trackless_additional"]:
        return None
    if jet_selection_pass(event, 1.0):
        return None
    candidates = [s for s in s_grid if s < 1.0 and jet_selection_pass(event, s)]
    return max(candidates) if candidates else None


def _read_n_mothers(csv_path: Path) -> dict[int, int]:
    """Read the raw n_mothers column, keyed by the source `event` index."""

    mapping: dict[int, int] = {}
    with csv_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["valid_weight"] != "1":
                continue
            mapping[int(row["event"])] = int(row["n_mothers"])
    return mapping


def _augment(events: list[dict[str, Any]], csv_paths: list[Path]) -> None:
    by_subrun: dict[int, dict[int, int]] = {}
    for subrun, path in enumerate(csv_paths):
        by_subrun[subrun] = _read_n_mothers(path)
    for event in events:
        event["n_mothers"] = by_subrun[event["subrun"]].get(event["source_event_index"], 0)


def _eligible(event: dict[str, Any]) -> bool:
    """Section 7 quality gate. Missing ranked jets are explicitly allowed."""

    if not math.isfinite(event["sum_pt_GeV"]) or not math.isfinite(event["r_max_mm"]):
        return False
    if event["event_id"] is None or event["subrun"] is None or event["source_event_index"] is None:
        return False
    return True


def _rank_key(event: dict[str, Any], cohort: str, s_grid: list[float]) -> tuple:
    """Deterministic within-cohort ranking hierarchy (Section 12)."""

    geometry_richness = -event.get("n_mothers", 0)
    jet_multiplicity = -sum(1 for v in event["jet_pt_GeV"].values() if v != MISSING_JET_SENTINEL)
    response = -(event["event_eff"] * event["vertex_eff"])
    if cohort == "jet_borderline_s1":
        xm = x_max(event)
        closeness = abs(xm - 1.0) if xm is not None else float("inf")
    elif cohort == "s_sensitive":
        transition = s_transition(event, s_grid)
        closeness = (1.0 - transition) if transition is not None else float("inf")
    elif cohort == "unusual_coverage":
        closeness = -(event["sum_pt_GeV"] + 10.0 * event["r_max_mm"])
    else:
        closeness = 0.0
    return (geometry_richness, jet_multiplicity, response, closeness, event["event_id"])


def _cohort_pool(events: list[dict[str, Any]], cohort: str, s_grid: list[float]) -> list[dict[str, Any]]:
    if cohort == "accepted_baseline":
        pool = [e for e in events if first_failed_cut(e) is None]
    elif cohort in _FIRST_FAIL_TO_COHORT.values():
        wanted = next(cut for cut, coh in _FIRST_FAIL_TO_COHORT.items() if coh == cohort)
        pool = [e for e in events if first_failed_cut(e) == wanted]
    elif cohort == "jet_borderline_s1":
        pool = [e for e in events if x_max(e) is not None]
    elif cohort == "s_sensitive":
        pool = [e for e in events if s_transition(e, s_grid) is not None]
    elif cohort == "unusual_coverage":
        pool = list(events)
    else:  # pragma: no cover - exhaustive by construction
        raise ValueError(f"unknown cohort {cohort}")
    return sorted(pool, key=lambda e: _rank_key(e, cohort, s_grid))


def select_top100(atlas_dihiggs_root: Path, mass: int) -> dict[str, Any]:
    events, csv_paths = load_mass(atlas_dihiggs_root, mass)
    events = [e for e in events if _eligible(e)]
    _augment(events, csv_paths)
    s_grid = discover_s_grid(atlas_dihiggs_root)

    pools = {cohort: _cohort_pool(events, cohort, s_grid) for cohort in COHORT_QUOTAS}
    taken: set[int] = set()
    selected: dict[str, list[dict[str, Any]]] = {cohort: [] for cohort in COHORT_QUOTAS}
    deficits: dict[str, int] = {}

    def _take(cohort: str, count: int) -> int:
        added = 0
        for event in pools[cohort]:
            if added >= count:
                break
            if event["event_id"] in taken:
                continue
            selected[cohort].append(event)
            taken.add(event["event_id"])
            added += 1
        return added

    for cohort, quota in COHORT_QUOTAS.items():
        got = _take(cohort, quota)
        if got < quota:
            deficits[cohort] = quota - got

    for cohort, deficit in list(deficits.items()):
        remaining = deficit
        for fallback in FALLBACK_CHAIN[cohort]:
            if remaining <= 0:
                break
            got = _take(fallback, remaining)
            remaining -= got
        deficits[cohort] = remaining  # unresolved remainder, if any (reported, never fabricated)

    total_selected = sum(len(v) for v in selected.values())

    records = []
    for cohort, cohort_events in selected.items():
        for rank, event in enumerate(cohort_events, start=1):
            records.append(
                {
                    "dataset_id": f"h2-m{mass}",
                    "mass_GeV": mass,
                    "event_id": event["event_id"],
                    "source_event_index": event["source_event_index"],
                    "subrun": event["subrun"],
                    "cohort": cohort,
                    "rank_in_cohort": rank,
                    "first_failed_cut": first_failed_cut(event),
                    "x_max": x_max(event),
                    "s_transition": s_transition(event, s_grid),
                    "n_mothers": event["n_mothers"],
                    "replay_mode": "B",
                }
            )
    records.sort(key=lambda r: r["event_id"])

    return {
        "dataset_id": f"h2-m{mass}",
        "mass_GeV": mass,
        "campaign_dir": str(_campaign_dir_for_mass(mass)),
        "requested_total": 100,
        "selected_total": total_selected,
        "cohort_requested": COHORT_QUOTAS,
        "cohort_selected": {cohort: len(v) for cohort, v in selected.items()},
        "cohort_deficit_unresolved": {k: v for k, v in deficits.items() if v > 0},
        "events": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dihiggs-root", type=Path, required=True)
    parser.add_argument("--mass", type=int, action="append", dest="masses")
    parser.add_argument("--output-dir", type=Path, default=Path("validation/h2_geometry_selection"))
    args = parser.parse_args()
    masses = args.masses or ALL_MASSES

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    for mass in masses:
        result = select_top100(args.atlas_dihiggs_root, mass)
        out_path = args.output_dir / f"m{mass}.json"
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"mass {mass}: selected {result['selected_total']}/100 -> {out_path}")
        for cohort, quota in COHORT_QUOTAS.items():
            summary_rows.append(
                {
                    "mass": mass,
                    "cohort": cohort,
                    "requested": quota,
                    "selected": result["cohort_selected"][cohort],
                    "deficit": result["cohort_deficit_unresolved"].get(cohort, 0),
                }
            )

    summary_path = args.output_dir / "summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["mass", "cohort", "requested", "selected", "deficit"])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
