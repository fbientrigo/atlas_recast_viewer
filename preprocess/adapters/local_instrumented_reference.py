"""Adapt validated local strong-bm1 telemetry to ``viewer.dataset.v1``.

This dataset is a 500-event reconstructed 0-parton teaching sample. It is not
the published inclusive 0j+1j+2j benchmark and never replaces that dataset.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from preprocess import SCHEMA_VERSION
from preprocess.adapters.original_recast import (
    ANALYSIS_SOURCE,
    CUT_TRANSLATIONS_ES,
    CUT_DEFINITIONS,
    EXPECTED_SOURCE_STAGE_IDS,
    UPSTREAM_COMMIT,
    UPSTREAM_REPOSITORY,
)
from preprocess.schema import validate_dataset, validate_events

BOOLEAN_CUT_IDS = EXPECTED_SOURCE_STAGE_IDS[:-1]
VERTEX_CUT_IDS = BOOLEAN_CUT_IDS[1:]
TELEMETRY_VERTEX_KEYS = {
    "fiducial_dv": "fiducial",
    "rxy_gt_4_mm": "r_vertex",
    "d0_gt_2_mm": "track_d0",
    "tracks_ge_5": "decay_products",
    "mdv_gt_10_gev": "dv_mass",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _events(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid telemetry JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"telemetry record must be an object at {path}:{line_number}")
        result.append(value)
    if not result:
        raise ValueError("telemetry is empty")
    return result


def _metric(log_text: str, label: str) -> float:
    match = re.search(rf"^{re.escape(label)}\s+([-+0-9.eE]+)(?:\s+\w+)?\s*$", log_text, re.MULTILINE)
    if not match:
        raise ValueError(f"metric missing from recast log: {label}")
    return float(match.group(1))


def _vertex_passes(vertex: dict[str, Any], active: tuple[str, ...]) -> bool:
    predicates = vertex["predicates"]
    return all(
        bool(predicates[cut_id] if cut_id in predicates else predicates[TELEMETRY_VERTEX_KEYS[cut_id]])
        for cut_id in active
    )


def _event_passes(event: dict[str, Any], cuts: tuple[str, ...]) -> bool:
    if not event["valid_weight"]:
        return False
    if "jet_selection" in cuts and not event["predicates"]["jet_selection"]:
        return False
    active_vertex = tuple(cut_id for cut_id in cuts if cut_id in VERTEX_CUT_IDS)
    return not active_vertex or any(_vertex_passes(vertex, active_vertex) for vertex in event["vertices"])


def adapt(
    *,
    telemetry: Path,
    upstream_log: Path,
    instrumented_log: Path,
    input_lhe: Path,
    run_card: Path,
    instrumented_source: Path,
    output_dir: Path,
    generator_command: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    raw_events = _events(telemetry)
    upstream_text = upstream_log.read_text(encoding="utf-8")
    instrumented_text = instrumented_log.read_text(encoding="utf-8")
    all_events = _metric(upstream_text, "All Events:")
    sigma_mb = _metric(upstream_text, "The inclusive cross section after merging is:")
    if all_events != len(raw_events):
        raise ValueError(f"telemetry/log event mismatch: {len(raw_events)} != {all_events}")
    if sigma_mb <= 0:
        raise ValueError("source cross section must be positive")

    canonical_events = []
    for event in raw_events:
        vertices = []
        for vertex in event.get("vertices", []):
            tracks = [
                {
                    "track_index": track["track_index"],
                    "pdg_id": track["pdg_id"],
                    "charge": track["charge"],
                    "x_prod_mm": track["x_prod_mm"],
                    "y_prod_mm": track["y_prod_mm"],
                    "z_prod_mm": track["z_prod_mm"],
                    "px_GeV": track["px_GeV"],
                    "py_GeV": track["py_GeV"],
                    "pz_GeV": track["pz_GeV"],
                    "d0_mm": track["d0_mm"],
                    "transverse_distance_mm": track["transverse_distance_mm"],
                    "passes_d0": track["passes_d0"],
                    "selected_for_dv": track["selected_for_dv"],
                }
                for track in vertex.get("tracks", [])
            ]
            vertices.append(
                {
                    "llp_index": vertex["llp_index"],
                    "pdg_id": vertex["pdg_id"],
                    "x_mm": vertex["x_mm"],
                    "y_mm": vertex["y_mm"],
                    "z_mm": vertex["z_mm"],
                    "r_mm": vertex["r_mm"],
                    "llp_momentum_GeV": vertex["llp_momentum_GeV"],
                    "selected_track_count": vertex["selected_track_count"],
                    "impacted_track_count": vertex["impacted_track_count"],
                    "mass_GeV": vertex["mass_GeV"],
                    "vertex_eff": vertex["vertex_eff"],
                    "predicates": {
                        cut_id: bool(vertex["predicates"][source_key])
                        for cut_id, source_key in TELEMETRY_VERTEX_KEYS.items()
                    },
                    "tracks": tracks,
                }
            )
        observables = event.get("observables", {})
        canonical_events.append(
            {
                "event_id": event["event_id"],
                "subrun": event["subrun"],
                "source_event_index": event["source_event_index"],
                "weight": event["weight"] / sigma_mb,
                "source_weight_mb": event["weight"],
                "valid_weight": event["valid_weight"],
                "observables": {
                    "sum_pt_GeV": observables.get("sum_pt_GeV"),
                    "r_max_mm": observables.get("r_max_mm"),
                },
                "predicates": {"jet_selection": bool(event.get("predicates", {}).get("jet_selection", False))},
                "response": event.get("response", {"vertex_eff": None, "event_eff": None}),
                "jets": event.get("jets", []),
                "vertices": vertices,
            }
        )

    denominator = sum(event["weight"] for event in canonical_events)
    stages = []
    previous = denominator
    for index, cut_id in enumerate(BOOLEAN_CUT_IDS, start=1):
        active = BOOLEAN_CUT_IDS[:index]
        after = sum(event["weight"] for event in canonical_events if _event_passes(event, active))
        stages.append(
            {
                "cut_id": cut_id,
                "n_before": previous,
                "n_after": after,
                "conditional_loss": None if previous == 0 else (previous - after) / previous,
                "cumulative_efficiency_pct": 0 if denominator == 0 else 100 * after / denominator,
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

    response_after = sum(
        event["weight"] * event["response"]["event_eff"] * event["response"]["vertex_eff"]
        for event in canonical_events
        if _event_passes(event, BOOLEAN_CUT_IDS)
    )
    stages.append(
        {
            "cut_id": "acceptance_x_efficiency",
            "n_before": previous,
            "n_after": response_after,
            "conditional_loss": None if previous == 0 else (previous - response_after) / previous,
            "cumulative_efficiency_pct": 0 if denominator == 0 else 100 * response_after / denominator,
            "reference": {
                "authors_recast_efficiency_pct": None,
                "atlas_full_sim_pct": None,
                "atlas_parametric_pct": None,
                "paper_recast_pct": None,
                "relative_difference_reproduction_vs_authors": None,
            },
        }
    )

    dataset_id = "local-reference"
    artifacts = (telemetry, upstream_log, instrumented_log, input_lhe, run_card, instrumented_source)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "title": "Local instrumented reference — strong-bm1 0j teaching sample",
        "source_kind": "instrumented_local_reference",
        "source_repository": "local recast_viewer instrumentation over frozen upstream",
        "source_commit": "uncommitted instrumentation; upstream base " + UPSTREAM_COMMIT,
        "source_dirty": True,
        "source_artifacts": [{"path": str(path), "sha256": _sha256(path)} for path in artifacts],
        "reference_sample": (
            "Reconstructed strong-bm1 0-parton slice; 500 events; "
            "m_gluino=2000 GeV, m_neutralino=850 GeV, tau=0.01 ns"
        ),
        "translations": {
            "es": {
                "title": "Referencia local instrumentada — muestra docente strong-bm1 0j",
                "reference_sample": "Fracción 0j de strong-bm1 reconstruida; 500 eventos; m_gluino=2000 GeV, m_neutralino=850 GeV, τ=0,01 ns",
            }
        },
        "n_events": len(canonical_events),
        "event_count_semantics": {
            "n_events": "locally generated 0-parton LHE events",
            "scope_warning": "teaching sample; not the inclusive published 0j+1j+2j benchmark",
            "weight_conversion": "canonical weight = merging weight in mb / local merged cross section in mb",
        },
        "created_utc": created_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generator_command": generator_command,
        "upstream_base": {"repository": UPSTREAM_REPOSITORY, "commit": UPSTREAM_COMMIT, "source": ANALYSIS_SOURCE},
        "capabilities": {
            "cutflow": True,
            "atomic_event_cuts": True,
            "jet_observables": True,
            "jet_what_if": True,
            "dv_radial": True,
            "dv_xyz": True,
            "response_weights": True,
        },
    }

    cuts = []
    for order, cut_id in enumerate(EXPECTED_SOURCE_STAGE_IDS, start=1):
        definition = copy.deepcopy(CUT_DEFINITIONS[cut_id])
        if cut_id == "jet_selection":
            definition["event_level_note"] = "Per-event j4/j5/j6/j7 observables are serialized for this local sample."
        cuts.append(
            {
                "id": cut_id,
                "order": order,
                "source_file": str(instrumented_source),
                "published_or_diagnostic": "published",
                "translations": {"es": CUT_TRANSLATIONS_ES[cut_id]},
                **definition,
            }
        )
    cuts_doc = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "unit_conventions": {
            "energy": "GeV",
            "length": "mm",
            "angles": "radians",
            "adapter_conversions": ["event weight: mb divided by local sigma_mb -> weighted-event units"],
        },
        "cuts": cuts,
        "jet_logic": {
            "region": "High-pT",
            "rank_indexing": "j4 is jets[3]; jets are sorted by smeared pT descending",
            "missing_jet_semantics": "A rank that does not exist makes its branch false.",
            "combination": "j4 OR j5 OR j6 OR j7",
            "branches": [
                {"jet_rank": rank, "threshold_GeV": threshold, "comparison": ">"}
                for rank, threshold in zip((4, 5, 6, 7), (250, 195, 116, 90), strict=True)
            ],
            "event_level_note": "Branch observables and predicates come from the instrumented local execution.",
        },
    }
    summary = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "cutflow": {
            "region": "High-pT",
            "count_semantics": "weighted_events",
            "denominator": {"weighted_events": denominator, "raw_recast_events": len(raw_events), "generated_events": len(raw_events)},
            "stages": stages,
        },
        "external_validation": {
            "status": "PROVISIONAL",
            "scope": "local reconstructed strong-bm1 0j teaching sample only",
            "reference": "published aggregate dataset remains dataset_id=reference",
            "uncertainty_status": "500-event statistical teaching sample; no precision claim",
            "note": (
                "Instrumented and upstream nominal logs agree exactly after removing the Pythia clock line. "
                "This 0j sample is close to, but does not replace, the inclusive public benchmark."
            ),
            "translations": {
                "es": {
                    "scope": "solo muestra docente local strong-bm1 0j reconstruida",
                    "reference": "el agregado publicado permanece en dataset_id=reference",
                    "note": "Los resultados nominales instrumentado y upstream coinciden exactamente al omitir la hora de Pythia. Esta muestra 0j es cercana al benchmark público inclusivo, pero no lo reemplaza.",
                }
            },
        },
    }
    events_doc = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "selection_semantics": {
            "boolean_counterfactual": "recomputed from event jet predicate and per-vertex atomic predicates",
            "vertex_combination": "event passes DV selection iff at least one vertex passes every enabled DV cut",
            "response_counterfactual": "not defined; response weighting remains the published baseline operation",
            "geometry": "truth LLP decay vertices plus smeared recast jet axes; not reconstructed detector hits",
            "tracks": (
                "charged final recursive LLP daughters; straight truth/recast directions only; "
                "selected_for_dv exactly records beta*gamma*tau > 520 mm and pT/|q| > 1 GeV"
            ),
            "d0": "signed proxy exactly serialized from r_prod * sin(phi_prod - phi_track)",
        },
        "events": canonical_events,
    }

    validate_dataset(manifest, cuts_doc, summary)
    validate_events(events_doc, manifest, cuts_doc)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in (("manifest.json", manifest), ("cuts.json", cuts_doc), ("summary.json", summary), ("events.json", events_doc)):
        (output_dir / filename).write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    return {"manifest": manifest, "cuts": cuts_doc, "summary": summary, "events": events_doc}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry", type=Path, required=True)
    parser.add_argument("--upstream-log", type=Path, required=True)
    parser.add_argument("--instrumented-log", type=Path, required=True)
    parser.add_argument("--input-lhe", type=Path, required=True)
    parser.add_argument("--run-card", type=Path, required=True)
    parser.add_argument("--instrumented-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    command = "python -m preprocess.adapters.local_instrumented_reference " + " ".join(
        f"--{key.replace('_', '-')} {value}" for key, value in vars(args).items()
    )
    adapt(**vars(args), generator_command=command)
    print(f"wrote {SCHEMA_VERSION} event dataset to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
