"""Adapt the H2 mass-control jet-recovery campaign to ``viewer.dataset.v1``.

Source: ``dihiggs_llp_recast-jet-threshold-diag/results/`` — a fixed
detector-response experiment (m_H2 varied, ctau_response held fixed, H2->bb
forced, unmodified published Trackless jet selection at the diagnostic scale
s=1). See ``docs/H2_SOURCE_INVENTORY.md`` for the full evidence trail.

Two population scopes are deliberately kept separate (Step 1B):

* statistics scope — all 20000 generated events per mass, used to build
  ``summary.json``'s cutflow exactly as the campaign's own
  ``analyze_mass_control.py`` / ``extract_response_table.py`` do;
* display scope — a bounded, deterministic subsample serialized into
  ``events.json`` for the jet inspector. ``manifest.n_events`` describes this
  subsample, not the full campaign (same convention as ``local-reference``).

No per-vertex geometry (x/y/z, tracks, jet eta/phi) is available in this
source (Step 1A #8/#9), so ``dv_radial``/``dv_xyz`` stay false and the five DV
predicates are declared ``predicate_scope: "event"`` rather than per-vertex.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from preprocess import SCHEMA_VERSION
from preprocess.adapters.original_recast import (
    CUT_DEFINITIONS as REFERENCE_CUT_DEFINITIONS,
    CUT_TRANSLATIONS_ES as REFERENCE_CUT_TRANSLATIONS_ES,
)
from preprocess.schema import DatasetValidationError, validate_dataset, validate_events

CAMPAIGN_ROOT = Path("dihiggs_llp_recast-jet-threshold-diag")
OLD_CAMPAIGN = CAMPAIGN_ROOT / "results/jet_threshold_response_20260815T230503Z"
NEW_CAMPAIGN = CAMPAIGN_ROOT / "results/mass_control_jet_recovery_20260816T173704Z"
OLD_MASSES = {130, 150, 170, 200, 250}
NEW_MASSES = {300, 330, 345}
ALL_MASSES = sorted(OLD_MASSES | NEW_MASSES)

CTAU_RESPONSE_MM = 4.326221529733112
DECAY_MODE = "bb"

TRACKLESS_JET_SOURCE_FILE = str(
    OLD_CAMPAIGN / "src/recast_2301_13866.cc"
)
JET_PT_COLUMN = {4: "jet4_pt", 5: "jet5_pt", 6: "jet6_pt", 7: "jet7_pt"}
TRACKLESS_THRESHOLDS_GEV = {4: 137.0, 5: 101.0, 6: 83.0, 7: 55.0}
MISSING_JET_SENTINEL = -1.0

BOOLEAN_CUT_IDS = (
    "jet_selection",
    "fiducial_dv",
    "rxy_gt_4_mm",
    "d0_gt_2_mm",
    "tracks_ge_5",
    "mdv_gt_10_gev",
)
DV_CUT_IDS = BOOLEAN_CUT_IDS[1:]
DV_CUT_SOURCE_COLUMN = {
    "fiducial_dv": "pass_fiducial",
    "rxy_gt_4_mm": "pass_rvtx4",
    "d0_gt_2_mm": "pass_d0",
    "tracks_ge_5": "pass_ndecay5",
    "mdv_gt_10_gev": "pass_mdv10",
}
DV_CUT_SOURCE_LINES = {
    "fiducial_dv": "365-369",
    "rxy_gt_4_mm": "371-375",
    "d0_gt_2_mm": "377-381",
    "tracks_ge_5": "383-387",
    "mdv_gt_10_gev": "389-393",
}
ALL_CUT_IDS = BOOLEAN_CUT_IDS + ("acceptance_x_efficiency",)

JET_SELECTION_TRACKLESS: dict[str, Any] = {
    "name": "Trackless jet selection",
    "category": "jet_kinematics",
    "kind": "compound_boolean",
    "mathematical_definition": (
        "[(Njet≥4 ∧ pT(j4)>137·s GeV) ∨ (Njet≥5 ∧ pT(j5)>101·s GeV) ∨ "
        "(Njet≥6 ∧ pT(j6)>83·s GeV) ∨ (Njet≥7 ∧ pT(j7)>55·s GeV)] "
        "∧ [pT(displaced_1)>70 GeV ∨ pT(displaced_2)>50 GeV]  (s=1 is the published baseline)"
    ),
    "mathematical_latex": (
        r"\left[(N_{\mathrm{jet}}\!\geq\!4 \land p_{\mathrm{T}}(j_4)>137s\,\mathrm{GeV})"
        r" \lor (N_{\mathrm{jet}}\!\geq\!5 \land p_{\mathrm{T}}(j_5)>101s\,\mathrm{GeV})"
        r" \lor (N_{\mathrm{jet}}\!\geq\!6 \land p_{\mathrm{T}}(j_6)>83s\,\mathrm{GeV})"
        r" \lor (N_{\mathrm{jet}}\!\geq\!7 \land p_{\mathrm{T}}(j_7)>55s\,\mathrm{GeV})\right]"
        r" \land \left[p_{\mathrm{T}}(d_1)>70\,\mathrm{GeV} \lor p_{\mathrm{T}}(d_2)>50\,\mathrm{GeV}\right]"
    ),
    "physical_meaning": (
        "Requires a sufficiently energetic ordinary multijet OR together with a matched displaced-jet leg. "
        "The diagnostic scale s rescales only the four ordinary thresholds; the displaced leg never changes."
    ),
    "analysis_rationale": (
        "This is the Trackless signal-region event leg. s=1 reproduces the unmodified published selection; "
        "s<1 is a diagnostic what-if counterfactual, never a published ATLAS variant."
    ),
    "source_line_or_symbol": (
        "recast_2301_13866.cc:274-280,402-405 (ordinary OR, s-scaled here); "
        "recast_2301_13866.cc (unmodified displaced-jet matching, s-independent)"
    ),
    "depends_on_parameters": [
        "trackless_j4_pt_GeV",
        "trackless_j5_pt_GeV",
        "trackless_j6_pt_GeV",
        "trackless_j7_pt_GeV",
    ],
    "parameters": {
        "trackless_j4_pt_GeV": TRACKLESS_THRESHOLDS_GEV[4],
        "trackless_j5_pt_GeV": TRACKLESS_THRESHOLDS_GEV[5],
        "trackless_j6_pt_GeV": TRACKLESS_THRESHOLDS_GEV[6],
        "trackless_j7_pt_GeV": TRACKLESS_THRESHOLDS_GEV[7],
    },
    "requires_fields": ["jets[].pt_GeV", "jets[].rank", "predicates.trackless_additional"],
}

ACCEPTANCE_X_EFFICIENCY_TRACKLESS: dict[str, Any] = {
    "name": "Acceptance × efficiency (Trackless)",
    "category": "response_weight",
    "kind": "response_weight",
    "mathematical_definition": (
        "Σ_event w × eventEff_Trackless(r_max, ΣpT_all_jets) × "
        "[1−∏_accepted vertices(1−vertexEff(R_DV,m_DV,N_tracks))]"
    ),
    "mathematical_latex": (
        r"\sum_{e} w_e\,\varepsilon_{\mathrm{event}}^{\mathrm{Trackless}}(r_{\max},\sum p_{\mathrm{T}})"
        r"\left[1-\prod_{v\in V_{\mathrm{accepted}}}"
        r"\left(1-\varepsilon_{\mathrm{vertex}}(R_v,m_v,N_{\mathrm{trk},v})\right)\right]"
    ),
    "physical_meaning": "Weights fully accepted truth events by the Trackless event- and vertex-response maps.",
    "analysis_rationale": "Converts truth-level acceptance into the recast's parameterized detector-response yield.",
    "source_line_or_symbol": (
        "recast_2301_13866.cc:395-399,430 (vEff union, eventEff_Trackless call); efficiency.cc:eventEff_Trackless,vertexEff"
    ),
    "depends_on_parameters": ["event_efficiency_map_trackless", "vertex_efficiency_map"],
    "requires_fields": [
        "event.weight",
        "event.observables.r_max_mm",
        "event.observables.sum_pt_GeV",
        "event.response.vertex_eff",
    ],
}

CUT_TRANSLATIONS_ES_TRACKLESS = {
    "jet_selection": {
        "name": "Selección de jets Trackless",
        "physical_meaning": (
            "Exige un OR ordinario de jets suficientemente energético junto con una rama de jet "
            "desplazado emparejado. La escala diagnóstica s reescala solo los cuatro umbrales ordinarios."
        ),
        "analysis_rationale": (
            "Es la rama de evento de la región Trackless. s=1 reproduce la selección publicada; "
            "s<1 es un contrafactual diagnóstico, nunca una variante publicada de ATLAS."
        ),
    },
    "acceptance_x_efficiency": {
        "name": "Aceptancia × eficiencia (Trackless)",
        "physical_meaning": "Pondera los eventos de verdad aceptados con los mapas de respuesta Trackless de evento y vértice.",
        "analysis_rationale": "Convierte la aceptancia a nivel de verdad en el rendimiento con respuesta parametrizada del recast.",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _campaign_dir_for_mass(mass: int) -> Path:
    if mass in OLD_MASSES:
        return OLD_CAMPAIGN
    if mass in NEW_MASSES:
        return NEW_CAMPAIGN
    raise ValueError(f"unknown H2 mass-control mass: {mass} (known: {ALL_MASSES})")


def discover_masses(atlas_dihiggs_root: Path) -> list[int]:
    """Discover masses from the campaign's own n_generated.json (Step 3A)."""

    payload = json.loads((atlas_dihiggs_root / NEW_CAMPAIGN / "outputs/n_generated.json").read_text())
    return sorted(int(mass) for mass in payload)


def discover_s_grid(atlas_dihiggs_root: Path) -> list[float]:
    """Discover the s grid from the campaign's own cutflow artifact (Step 3B)."""

    path = atlas_dihiggs_root / NEW_CAMPAIGN / "outputs/mass_control_cutflow.csv"
    values: set[float] = set()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            values.add(round(float(row["s"]), 6))
    return sorted(values, reverse=True)


def _read_seed_events(path: Path, event_id_base: int, seed_index: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["valid_weight"] != "1":
                continue
            rows.append(
                {
                    "event_id": event_id_base + int(row["event"]),
                    "subrun": seed_index,
                    "source_event_index": int(row["event"]),
                    "jet_pt_GeV": {rank: float(row[column]) for rank, column in JET_PT_COLUMN.items()},
                    "trackless_additional": row["trackless_additional"] == "1",
                    "pass_fiducial": row["pass_fiducial"] == "1",
                    "pass_rvtx4": row["pass_rvtx4"] == "1",
                    "pass_d0": row["pass_d0"] == "1",
                    "pass_ndecay5": row["pass_ndecay5"] == "1",
                    "pass_mdv10": row["pass_mdv10"] == "1",
                    "r_max_mm": float(row["r_max"]),
                    "sum_pt_GeV": float(row["sum_pt"]),
                    "vertex_eff": float(row["v_eff"]),
                    "event_eff": float(row["event_eff_trackless"]),
                }
            )
    return rows


def load_mass(atlas_dihiggs_root: Path, mass: int) -> tuple[list[dict[str, Any]], list[Path]]:
    """Load every valid event for one mass across both seeds (full statistics scope)."""

    campaign = atlas_dihiggs_root / _campaign_dir_for_mass(mass)
    runs_dir = campaign / "runs/main" / f"mH{mass}"
    seed_dirs = sorted(runs_dir.glob("seed_*"))
    if not seed_dirs:
        raise FileNotFoundError(f"no seed directories under {runs_dir}")
    events: list[dict[str, Any]] = []
    csv_paths: list[Path] = []
    for offset, seed_dir in enumerate(seed_dirs):
        csv_path = seed_dir / "events.csv"
        csv_paths.append(csv_path)
        events.extend(_read_seed_events(csv_path, offset * 10_000, offset))
    return events, csv_paths


def jet_selection_pass(event: dict[str, Any], scale: float) -> bool:
    ordinary = any(
        event["jet_pt_GeV"][rank] > scale * threshold
        for rank, threshold in TRACKLESS_THRESHOLDS_GEV.items()
    )
    return ordinary and event["trackless_additional"]


def _boolean_stage_mask(
    events: list[dict[str, Any]], cut_id: str, previous_mask: list[bool], scale: float
) -> list[bool]:
    if cut_id == "jet_selection":
        return [prev and jet_selection_pass(event, scale) for prev, event in zip(previous_mask, events, strict=True)]
    column = DV_CUT_SOURCE_COLUMN[cut_id]
    return [prev and event[column] for prev, event in zip(previous_mask, events, strict=True)]


def build_cutflow_stages(events: list[dict[str, Any]], scale: float = 1.0) -> list[dict[str, Any]]:
    """Exact full-statistics cutflow at threshold scale ``s`` (baseline s=1.0, Step 1F)."""

    denominator = float(len(events))
    stages: list[dict[str, Any]] = []
    mask = [True] * len(events)
    previous = denominator
    for cut_id in BOOLEAN_CUT_IDS:
        mask = _boolean_stage_mask(events, cut_id, mask, scale)
        after = float(sum(mask))
        stages.append(
            {
                "cut_id": cut_id,
                "n_before": previous,
                "n_after": after,
                "conditional_loss": None if previous == 0 else (previous - after) / previous,
                "cumulative_efficiency_pct": 0.0 if denominator == 0 else 100.0 * after / denominator,
                "reference": {
                    "authors_recast_efficiency_pct": None,
                    "atlas_full_sim_pct": None,
                    "atlas_parametric_pct": None,
                    "paper_recast_pct": None,
                    "relative_difference_reproduction_vs_authors": None,
                },
            }
        )
        previous = after

    weighted_numerator = sum(
        event["event_eff"] * event["vertex_eff"] for event, passed in zip(events, mask, strict=True) if passed
    )
    stages.append(
        {
            "cut_id": "acceptance_x_efficiency",
            "n_before": previous,
            "n_after": weighted_numerator,
            "conditional_loss": None if previous == 0 else (previous - weighted_numerator) / previous,
            "cumulative_efficiency_pct": 0.0 if denominator == 0 else 100.0 * weighted_numerator / denominator,
            "reference": {
                "authors_recast_efficiency_pct": None,
                "atlas_full_sim_pct": None,
                "atlas_parametric_pct": None,
                "paper_recast_pct": None,
                "relative_difference_reproduction_vs_authors": None,
            },
        }
    )
    return stages


def _canonical_jets(event: dict[str, Any]) -> list[dict[str, Any]]:
    jets = []
    for rank in sorted(JET_PT_COLUMN):
        pt = event["jet_pt_GeV"][rank]
        if pt == MISSING_JET_SENTINEL:
            continue  # canonical absence: never rendered as a physical jet
        jets.append({"rank": rank, "pt_GeV": pt, "eta": None, "phi": None})
    return jets


def _canonical_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event["event_id"],
        "subrun": event["subrun"],
        "source_event_index": event["source_event_index"],
        "weight": 1.0,
        "source_weight_mb": None,
        "valid_weight": True,
        "observables": {"sum_pt_GeV": event["sum_pt_GeV"], "r_max_mm": event["r_max_mm"]},
        "predicates": {
            "jet_selection": jet_selection_pass(event, 1.0),
            "trackless_additional": event["trackless_additional"],
            "fiducial_dv": event["pass_fiducial"],
            "rxy_gt_4_mm": event["pass_rvtx4"],
            "d0_gt_2_mm": event["pass_d0"],
            "tracks_ge_5": event["pass_ndecay5"],
            "mdv_gt_10_gev": event["pass_mdv10"],
        },
        "response": {"event_eff": event["event_eff"], "vertex_eff": event["vertex_eff"]},
        "jets": _canonical_jets(event),
        "vertices": [],
    }


def select_display_subsample(events: list[dict[str, Any]], target_count: int) -> list[dict[str, Any]]:
    if target_count <= 0 or target_count > len(events):
        raise ValueError(f"invalid display subsample target {target_count} for {len(events)} events")
    stride = len(events) // target_count
    subsample = events[::stride][:target_count]
    if len(subsample) != target_count:
        raise ValueError(f"stride sampling produced {len(subsample)} events, expected {target_count}")
    return subsample


def _build_cuts_doc(dataset_id: str, s_grid: list[float]) -> dict[str, Any]:
    cuts = []
    for order, cut_id in enumerate(ALL_CUT_IDS, start=1):
        if cut_id == "jet_selection":
            definition = copy.deepcopy(JET_SELECTION_TRACKLESS)
            source_file = TRACKLESS_JET_SOURCE_FILE
            translations = {"es": CUT_TRANSLATIONS_ES_TRACKLESS["jet_selection"]}
        elif cut_id == "acceptance_x_efficiency":
            definition = copy.deepcopy(ACCEPTANCE_X_EFFICIENCY_TRACKLESS)
            source_file = TRACKLESS_JET_SOURCE_FILE
            translations = {"es": CUT_TRANSLATIONS_ES_TRACKLESS["acceptance_x_efficiency"]}
        else:
            definition = copy.deepcopy(REFERENCE_CUT_DEFINITIONS[cut_id])
            definition["source_line_or_symbol"] = f"recast_2301_13866.cc:{DV_CUT_SOURCE_LINES[cut_id]}"
            definition["predicate_scope"] = "event"
            source_file = TRACKLESS_JET_SOURCE_FILE
            translations = {"es": REFERENCE_CUT_TRANSLATIONS_ES[cut_id]}
        cuts.append(
            {
                "id": cut_id,
                "order": order,
                "source_file": source_file,
                "published_or_diagnostic": "published",
                "translations": translations,
                **definition,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "unit_conventions": {
            "energy": "GeV",
            "length": "mm",
            "angles": "radians",
            "adapter_conversions": [
                "event weight: campaign convention is raw unweighted event counts (canonical weight=1.0 for "
                "every valid_weight=1 event); the per-event LHE weight column is uniform within a seed and is "
                "not used for cutflow scaling, matching outputs/mass_control_cutflow.csv."
            ],
        },
        "cuts": cuts,
        "jet_logic": {
            "region": "trackless",
            "rank_indexing": "jet rank is an explicit integer field (4-7); jets are pT-sorted",
            "missing_jet_semantics": (
                "A rank absent from jets[] makes that branch false. Source sentinel -1 "
                "(recast_2301_13866.cc:410-413) is mapped to canonical absence by this adapter; "
                "it is never rendered as a physical jet."
            ),
            "combination": "j4 OR j5 OR j6 OR j7, then AND with the additional displaced-jet leg",
            "branches": [
                {"jet_rank": rank, "threshold_GeV": threshold, "comparison": ">"}
                for rank, threshold in TRACKLESS_THRESHOLDS_GEV.items()
            ],
            "additional_requirement": {
                "supported": True,
                "predicate_id": "trackless_additional",
                "scales_with_s": False,
                "description": (
                    "matched displaced jet leg (leading matched+fiducial jet pT>70 GeV OR second pT>50 GeV); "
                    "unmodified by s"
                ),
            },
            "threshold_scale": {
                "supported": True,
                "parameter_symbol": "s",
                "baseline": 1.0,
                "values": s_grid,
                "applies_to": "branches[].threshold_GeV only",
                "scope_note": (
                    "s<1 is a diagnostic counterfactual jet-threshold rescaling from the mass-control jet-recovery "
                    "study; it is not a published ATLAS analysis variant."
                ),
            },
            "event_level_note": (
                "Per-event j4-j7 pT and the additional-leg boolean are serialized; jet_selection at s=1 is stored "
                "as the baseline predicate and other s values are recomputed client-side from jets[] and this metadata."
            ),
        },
    }


def _recover_geometry_pack(output_dir: Path, manifest: dict[str, Any], cuts_doc: dict[str, Any]) -> dict[str, Any] | None:
    """Reattach an already-replayed geometry pack after regenerating this dataset.

    ``adapt()`` rewrites manifest.json from scratch on every run, which would
    otherwise silently drop the ``geometry_pack`` link created by
    ``preprocess/geometry_replay.py`` (a separate, much slower Pythia-replay
    step this function must never rerun or duplicate). If the previous
    manifest.json on disk names a geometry pack and geometry_events.json is
    still present and still validates against the freshly regenerated
    manifest/cuts, its metadata is carried forward unchanged. Anything
    missing, unreadable, or no longer consistent is treated as absent —
    never fabricated.
    """

    previous_manifest_path = output_dir / "manifest.json"
    geometry_events_path = output_dir / "geometry_events.json"
    if not previous_manifest_path.exists() or not geometry_events_path.exists():
        return None
    try:
        previous_manifest = json.loads(previous_manifest_path.read_text(encoding="utf-8"))
        geometry_pack = previous_manifest.get("geometry_pack")
        if not geometry_pack:
            return None
        geometry_doc = json.loads(geometry_events_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if geometry_doc.get("dataset_id") != manifest["dataset_id"]:
        return None
    geometry_manifest = {**manifest, "capabilities": {**manifest["capabilities"], "dv_radial": True, "dv_xyz": True}}
    try:
        validate_events(
            geometry_doc, geometry_manifest, cuts_doc,
            expected_count=geometry_pack.get("event_count"), file_name="geometry_events.json",
        )
    except DatasetValidationError:
        return None
    return geometry_pack


def adapt(
    *,
    atlas_dihiggs_root: Path,
    mass: int,
    display_count: int,
    output_dir: Path,
    generator_command: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    events, csv_paths = load_mass(atlas_dihiggs_root, mass)
    stages = build_cutflow_stages(events)
    display_events = [_canonical_event(event) for event in select_display_subsample(events, display_count)]
    s_grid = discover_s_grid(atlas_dihiggs_root)

    dataset_id = f"h2-m{mass}"
    new_campaign_dir = atlas_dihiggs_root / NEW_CAMPAIGN
    provenance_paths = [
        *csv_paths,
        new_campaign_dir / "DECISION.md",
        new_campaign_dir / "outputs/mass_control_cutflow.csv",
        new_campaign_dir / "scripts/analyze_mass_control.py",
        atlas_dihiggs_root / OLD_CAMPAIGN / "scripts/extract_response_table.py",
        atlas_dihiggs_root / OLD_CAMPAIGN / "src/recast_2301_13866.cc",
    ]

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "title": f"H2 mass control — {mass} GeV Trackless (fixed τ_response)",
        "source_kind": "h2_mass_control",
        "source_repository": "local dihiggs_llp_recast-jet-threshold-diag (mass-control jet-recovery campaign)",
        "source_commit": "ef12e05c28f15051064dc7a10d2a3f03b5efc02e",
        "source_dirty": True,
        "source_artifacts": [{"path": str(path), "sha256": _sha256(path)} for path in provenance_paths],
        "reference_sample": (
            f"H2 mass-control: gg→h*(125)→H2 H2, H2→b b̄ forced, m_H2={mass} GeV, "
            f"τ_response={CTAU_RESPONSE_MM} mm (fixed detector-response lifetime, distinct from the "
            "physical 2HDM trajectory), Trackless analysis region, s=1 published baseline."
        ),
        "translations": {
            "es": {
                "title": f"Control de masa H2 — {mass} GeV Trackless (τ_response fijo)",
                "reference_sample": (
                    f"Control de masa H2: gg→h*(125)→H2 H2, H2→b b̄ forzado, m_H2={mass} GeV, "
                    f"τ_response={CTAU_RESPONSE_MM} mm (vida media de respuesta del detector fija, distinta "
                    "de la trayectoria física 2HDM), región de análisis Trackless, línea base s=1."
                ),
            }
        },
        "n_events": len(display_events),
        "event_count_semantics": {
            "n_events": "interactive display subsample drawn from the full campaign (see sample.full_campaign_events)",
            "full_campaign_events": len(events),
            "scope_warning": (
                "cutflow/summary statistics use the full campaign population; events.json displays only a "
                "deterministic subsample for jet inspection, not the statistics denominator"
            ),
            "weight_conversion": "canonical weight = 1.0 (raw unweighted event counts; see cuts.json unit_conventions)",
        },
        "sample": {
            "family": "h2_mass_control",
            "mass_GeV": mass,
            "analysis_region": "trackless",
            "decay_mode": DECAY_MODE,
            "ctau_response_mm": CTAU_RESPONSE_MM,
            "lifetime_mode": "fixed_response",
        },
        "created_utc": created_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generator_command": generator_command,
        "capabilities": {
            "cutflow": True,
            "atomic_event_cuts": True,
            "jet_observables": True,
            "jet_what_if": True,
            "dv_radial": False,
            "dv_xyz": False,
            "response_weights": True,
        },
    }

    cuts_doc = _build_cuts_doc(dataset_id, s_grid)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "cutflow": {
            "region": "trackless",
            "count_semantics": "weighted_events",
            "denominator": {
                "weighted_events": float(len(events)),
                "raw_recast_events": len(events),
                "generated_events": len(events),
            },
            "stages": stages,
        },
        "external_validation": {
            "status": "PROVISIONAL",
            "scope": f"H2 mass-control Trackless campaign, m_H2={mass} GeV, s=1 baseline only",
            "reference": (
                "no independent external ATLAS/authors reference number exists for this diagnostic "
                "mass-control campaign; validated internally against the campaign's own "
                "outputs/mass_control_cutflow.csv"
            ),
            "uncertainty_status": "20000-event campaign statistics; validated against outputs/mass_control_cutflow.csv",
            "note": (
                "Cross-checked against the campaign's own mass_control_cutflow.csv (see "
                "validation/h2_m{mass}_validation.json). Not an independently published ATLAS number."
            ),
            "translations": {
                "es": {
                    "scope": f"Campaña de control de masa H2 Trackless, m_H2={mass} GeV, solo línea base s=1",
                    "reference": (
                        "no existe un número de referencia externo independiente de ATLAS/autores para esta "
                        "campaña diagnóstica de control de masa; validado internamente contra "
                        "outputs/mass_control_cutflow.csv de la propia campaña"
                    ),
                    "note": (
                        "Verificado contra mass_control_cutflow.csv de la propia campaña. No es un número "
                        "publicado independientemente por ATLAS."
                    ),
                }
            },
        },
    }

    events_doc = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "selection_semantics": {
            "boolean_counterfactual": "recomputed from event jet predicate and event-scoped DV atomic predicates",
            "vertex_combination": "not applicable: no per-vertex breakdown is serialized for this source (event-scoped DV predicates only)",
            "response_counterfactual": "not defined; response weighting remains the published baseline operation",
            "geometry": "unavailable for this source: no vertex x/y/z, jet eta/phi, or tracks are serialized (see H2_SOURCE_INVENTORY.md)",
            "tracks": "not available",
            "d0": "not available (only the event-level d0>2mm boolean is serialized)",
        },
        "events": display_events,
    }

    validate_dataset(manifest, cuts_doc, summary)
    validate_events(events_doc, manifest, cuts_doc)
    recovered_geometry_pack = _recover_geometry_pack(output_dir, manifest, cuts_doc)
    if recovered_geometry_pack is not None:
        manifest["geometry_pack"] = recovered_geometry_pack
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in (
        ("manifest.json", manifest),
        ("cuts.json", cuts_doc),
        ("summary.json", summary),
        ("events.json", events_doc),
    ):
        (output_dir / filename).write_text(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return {"manifest": manifest, "cuts": cuts_doc, "summary": summary, "events": events_doc}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dihiggs-root", type=Path, required=True)
    parser.add_argument("--mass", type=int, required=True)
    parser.add_argument("--display-count", type=int, default=400)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    command = "python -m preprocess.adapters.h2_mass_control " + " ".join(
        f"--{key.replace('_', '-')} {value}" for key, value in vars(args).items()
    )
    adapt(
        atlas_dihiggs_root=args.atlas_dihiggs_root,
        mass=args.mass,
        display_count=args.display_count,
        output_dir=args.output_dir,
        generator_command=command,
    )
    print(f"wrote {SCHEMA_VERSION} dataset h2-m{args.mass} to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
