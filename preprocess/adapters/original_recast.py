"""Adapter for the frozen public-recast strong-bm1 aggregate artifacts.

This is intentionally source-specific. It serializes existing aggregate values;
it does not reconstruct event predicates that the original executable never wrote.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from preprocess import SCHEMA_VERSION
from preprocess.schema import validate_dataset

UPSTREAM_REPOSITORY = "https://github.com/llprecasting/recastingCodes.git"
UPSTREAM_COMMIT = "d4047c744062094c9f88e507bb1ccf69e9fe88d6"
ANALYSIS_SOURCE = (
    "DisplacedVertices/ATLAS-SUSY-2018-13_GCottin/"
    "recast_code/1_analysis/recast_2301_13866.cc"
)

# Explicit source-stage mapping. Display text and physics meaning do not leak
# into the frontend as adapter conditionals.
CUT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "jet_selection": {
        "name": "High-pT jet selection",
        "category": "jet_kinematics",
        "kind": "compound_boolean",
        "mathematical_definition": (
            "(Njet≥4 ∧ pT(j4)>250 GeV) ∨ (Njet≥5 ∧ pT(j5)>195 GeV) ∨ "
            "(Njet≥6 ∧ pT(j6)>116 GeV) ∨ (Njet≥7 ∧ pT(j7)>90 GeV)"
        ),
        "mathematical_latex": (
            r"(N_{\mathrm{jet}}\!\geq\!4 \land p_{\mathrm{T}}(j_4)>250\,\mathrm{GeV})"
            r" \lor (N_{\mathrm{jet}}\!\geq\!5 \land p_{\mathrm{T}}(j_5)>195\,\mathrm{GeV})"
            r" \lor (N_{\mathrm{jet}}\!\geq\!6 \land p_{\mathrm{T}}(j_6)>116\,\mathrm{GeV})"
            r" \lor (N_{\mathrm{jet}}\!\geq\!7 \land p_{\mathrm{T}}(j_7)>90\,\mathrm{GeV})"
        ),
        "physical_meaning": (
            "Requires a sufficiently energetic multijet event. Each jet-rank branch is an OR; "
            "a missing jet makes only that branch false."
        ),
        "analysis_rationale": (
            "This is the High-pT signal-region event leg used to select energetic hadronic production."
        ),
        "source_line_or_symbol": "recast_2301_13866.cc:197-207,321-340",
        "depends_on_parameters": [
            "highpt_j4_pt_GeV",
            "highpt_j5_pt_GeV",
            "highpt_j6_pt_GeV",
            "highpt_j7_pt_GeV",
        ],
        "parameters": {"highpt_j4_pt_GeV": 250, "highpt_j5_pt_GeV": 195, "highpt_j6_pt_GeV": 116, "highpt_j7_pt_GeV": 90},
        "requires_fields": ["jets[].pt_GeV", "jets[].rank"],
    },
    "fiducial_dv": {
        "name": "Fiducial displaced vertex",
        "category": "geometry",
        "kind": "compound_boolean",
        "mathematical_definition": "∃ LLP decay vertex: R_DV < 300 mm ∧ |z_DV| < 300 mm",
        "mathematical_latex": (
            r"\exists\,v_{\mathrm{DV}}:\quad R_{\mathrm{DV}}<300\,\mathrm{mm}"
            r" \;\land\; |z_{\mathrm{DV}}|<300\,\mathrm{mm}"
        ),
        "geometry_overlay": {
            "view": "r_z",
            "r_min_mm": None,
            "r_max_mm": 300.0,
            "abs_z_max_mm": 300.0,
        },
        "physical_meaning": "At least one LLP decay lies inside the truth-level DV fiducial volume.",
        "analysis_rationale": "Restricts vertices to the radial and longitudinal region modeled by the recast.",
        "source_line_or_symbol": "recast_2301_13866.cc:242-248,285-289",
        "depends_on_parameters": ["dv_r_max_mm", "dv_abs_z_max_mm"],
        "parameters": {"dv_r_max_mm": 300, "dv_abs_z_max_mm": 300},
        "requires_fields": ["decay_vertices[].x_mm", "decay_vertices[].y_mm", "decay_vertices[].z_mm"],
    },
    "rxy_gt_4_mm": {
        "name": "DV radius above 4 mm",
        "category": "geometry",
        "kind": "atomic_boolean",
        "mathematical_definition": "R_DV = √(x_DV²+y_DV²) > 4 mm",
        "mathematical_latex": (
            r"R_{\mathrm{DV}}=\sqrt{x_{\mathrm{DV}}^2+y_{\mathrm{DV}}^2}>4\,\mathrm{mm}"
        ),
        "geometry_overlay": {
            "view": "r_z",
            "r_min_mm": 4.0,
            "r_max_mm": None,
            "abs_z_max_mm": None,
        },
        "physical_meaning": "Selects a vertex measurably displaced from the beam line.",
        "analysis_rationale": "Suppresses prompt vertices and enters the domain of the DV response map.",
        "source_line_or_symbol": "recast_2301_13866.cc:291-295",
        "depends_on_parameters": ["dv_r_min_mm"],
        "parameters": {"dv_r_min_mm": 4},
        "requires_fields": ["decay_vertices[].r_mm"],
    },
    "d0_gt_2_mm": {
        "name": "At least one displaced track",
        "category": "track_displacement",
        "kind": "compound_boolean",
        "mathematical_definition": "∃ charged final daughter track: |d₀| > 2 mm",
        "mathematical_latex": (
            r"\exists\,t\in\{\text{charged final daughters}\}:\quad |d_0(t)|>2\,\mathrm{mm}"
        ),
        "physical_meaning": "Requires evidence that at least one charged daughter does not point back to the beam line.",
        "analysis_rationale": "Rejects vertices without a displaced charged-track signature.",
        "source_line_or_symbol": "recast_2301_13866.cc:258-270,297-301",
        "depends_on_parameters": ["track_abs_d0_min_mm"],
        "parameters": {"track_abs_d0_min_mm": 2},
        "requires_fields": ["tracks[].d0_mm"],
    },
    "tracks_ge_5": {
        "name": "At least five selected tracks",
        "category": "dv_quality",
        "kind": "compound_boolean",
        "mathematical_definition": (
            "N(selected charged final daughters) ≥ 5, with βγτ > 520 mm and pT/|q| > 1 GeV"
        ),
        "mathematical_latex": (
            r"N_{\mathrm{selected\ tracks}}\geq5,\qquad "
            r"\beta\gamma\tau>520\,\mathrm{mm},\quad p_{\mathrm{T}}/|q|>1\,\mathrm{GeV}"
        ),
        "physical_meaning": "Keeps multi-track vertices with enough reconstructable charged activity.",
        "analysis_rationale": "Reduces low-multiplicity backgrounds and defines an input axis of the vertex response map.",
        "source_line_or_symbol": "recast_2301_13866.cc:253-282,303-307",
        "depends_on_parameters": [
            "selected_track_count_min",
            "track_transverse_distance_min_mm",
            "track_pt_over_charge_min_GeV",
        ],
        "parameters": {"selected_track_count_min": 5, "track_transverse_distance_min_mm": 520, "track_pt_over_charge_min_GeV": 1},
        "requires_fields": ["decay_vertices[].selected_track_count"],
    },
    "mdv_gt_10_gev": {
        "name": "DV mass above 10 GeV",
        "category": "dv_quality",
        "kind": "atomic_boolean",
        "mathematical_definition": "m_DV(selected tracks, charged-pion mass hypothesis) > 10 GeV",
        "mathematical_latex": (
            r"m_{\mathrm{DV}}(\text{selected tracks};\ m_{\pi^\pm}\text{ hypothesis})"
            r">10\,\mathrm{GeV}"
        ),
        "physical_meaning": "Keeps high-mass vertices built from the selected charged daughters.",
        "analysis_rationale": "Suppresses low-mass backgrounds and supplies the mass axis of the vertex response map.",
        "source_line_or_symbol": "recast_2301_13866.cc:256-282,309-313",
        "depends_on_parameters": ["dv_mass_min_GeV"],
        "parameters": {"dv_mass_min_GeV": 10, "charged_pion_mass_GeV": 0.13957039},
        "requires_fields": ["decay_vertices[].mass_GeV"],
    },
    "acceptance_x_efficiency": {
        "name": "Acceptance × efficiency",
        "category": "response_weight",
        "kind": "response_weight",
        "mathematical_definition": (
            "Σ_event w × eventEff_HighPT(r_max, ΣpT) × "
            "[1−∏_accepted vertices(1−vertexEff(R_DV,m_DV,N_tracks))]"
        ),
        "mathematical_latex": (
            r"\sum_{e} w_e\,\varepsilon_{\mathrm{event}}(r_{\max},\sum p_{\mathrm{T}})"
            r"\left[1-\prod_{v\in V_{\mathrm{accepted}}}"
            r"\left(1-\varepsilon_{\mathrm{vertex}}(R_v,m_v,N_{\mathrm{trk},v})\right)\right]"
        ),
        "physical_meaning": "Weights fully accepted truth events by digitized ATLAS event and vertex response maps.",
        "analysis_rationale": "Converts truth-level acceptance into the recast's parameterized detector-response yield.",
        "source_line_or_symbol": "recast_2301_13866.cc:315-319,336-340; efficiency.cc:eventEff_HighPT,vertexEff",
        "depends_on_parameters": ["event_efficiency_map", "vertex_efficiency_map"],
        "requires_fields": [
            "event.weight",
            "event.r_max_mm",
            "event.sum_jet_pt_GeV",
            "decay_vertices[].vertex_eff",
        ],
    },
}

EXPECTED_SOURCE_STAGE_IDS = tuple(CUT_DEFINITIONS)

CUT_TRANSLATIONS_ES: dict[str, dict[str, str]] = {
    "jet_selection": {
        "name": "Selección de jets de alto pT",
        "physical_meaning": "Exige un evento multijet suficientemente energético. Las ramas por rango se combinan con OR; si un jet no existe, solo esa rama es falsa.",
        "analysis_rationale": "Es la rama de evento de la región High-pT que selecciona producción hadrónica energética.",
    },
    "fiducial_dv": {
        "name": "Vértice desplazado fiducial",
        "physical_meaning": "Al menos un decaimiento LLP ocurre dentro del volumen fiducial de verdad usado para el DV.",
        "analysis_rationale": "Restringe los vértices a la región radial y longitudinal modelada por el recast.",
    },
    "rxy_gt_4_mm": {
        "name": "Radio del DV mayor que 4 mm",
        "physical_meaning": "Selecciona un vértice claramente desplazado respecto de la línea del haz.",
        "analysis_rationale": "Suprime vértices prompt y entra en el dominio del mapa de respuesta del DV.",
    },
    "d0_gt_2_mm": {
        "name": "Al menos una traza desplazada",
        "physical_meaning": "Exige que al menos una hija cargada no apunte de regreso a la línea del haz.",
        "analysis_rationale": "Rechaza vértices sin una firma de traza cargada desplazada.",
    },
    "tracks_ge_5": {
        "name": "Al menos cinco trazas seleccionadas",
        "physical_meaning": "Conserva vértices multitraza con suficiente actividad cargada reconstruible.",
        "analysis_rationale": "Reduce fondos de baja multiplicidad y define un eje del mapa de respuesta del vértice.",
    },
    "mdv_gt_10_gev": {
        "name": "Masa del DV mayor que 10 GeV",
        "physical_meaning": "Conserva vértices de masa alta construidos con las hijas cargadas seleccionadas.",
        "analysis_rationale": "Suprime fondos de baja masa y proporciona el eje de masa del mapa de respuesta del vértice.",
    },
    "acceptance_x_efficiency": {
        "name": "Aceptancia × eficiencia",
        "physical_meaning": "Pondera los eventos de verdad aceptados con los mapas parametrizados de respuesta de evento y vértice de ATLAS.",
        "analysis_rationale": "Convierte la aceptancia a nivel de verdad en el rendimiento con respuesta parametrizada del recast.",
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"source file missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid source JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"source JSON must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_output(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _validate_source(
    cutflow: dict[str, Any], benchmark_manifest: dict[str, Any], benchmark: dict[str, Any]
) -> None:
    if cutflow.get("schema_version") != 1:
        raise ValueError(f"source cutflow schema_version must be 1, got {cutflow.get('schema_version')!r}")
    if cutflow.get("benchmark") != "strong-bm1" or cutflow.get("signal_region") != "High-pT":
        raise ValueError("source must be the frozen strong-bm1 High-pT cutflow")
    stages = cutflow.get("stages")
    if not isinstance(stages, list):
        raise ValueError("source cutflow stages must be an array")
    ids = tuple(stage.get("id") for stage in stages)
    if ids != EXPECTED_SOURCE_STAGE_IDS:
        raise ValueError(f"source stage order mismatch: expected {EXPECTED_SOURCE_STAGE_IDS}, got {ids}")
    for stage in stages:
        for field in (
            "our_weighted_events",
            "our_efficiency_pct",
            "authors_recast_efficiency_pct",
            "atlas_full_sim_pct",
        ):
            if field not in stage:
                raise ValueError(f"source stage {stage.get('id')} missing {field}")
    if benchmark_manifest.get("upstream_commit") != UPSTREAM_COMMIT:
        raise ValueError("benchmark manifest upstream commit does not match adapter pin")
    if benchmark_manifest.get("verdict") != "UPSTREAM_STRONG_BM1_VALIDATED":
        raise ValueError("benchmark manifest does not carry the validated verdict")
    if benchmark.get("reference_result") is None or benchmark.get("signal_region") != "High-pT":
        raise ValueError("benchmark definition lacks the High-pT archived reference result")


def adapt(
    *,
    source_cutflow: Path,
    source_benchmark_manifest: Path,
    source_benchmark: Path,
    source_checkout: Path,
    output_dir: Path,
    generator_command: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    cutflow = _load_json(source_cutflow)
    benchmark_manifest = _load_json(source_benchmark_manifest)
    benchmark = _load_json(source_benchmark)
    _validate_source(cutflow, benchmark_manifest, benchmark)

    head = _git_output(source_checkout, "rev-parse", "HEAD")
    dirty_text = _git_output(source_checkout, "status", "--porcelain")
    if head != UPSTREAM_COMMIT:
        raise ValueError(f"source checkout commit mismatch: expected {UPSTREAM_COMMIT}, got {head}")
    if dirty_text:
        raise ValueError("source checkout is dirty; refusing to label the dataset as frozen")

    source_analysis = source_checkout / ANALYSIS_SOURCE
    if not source_analysis.is_file():
        raise ValueError(f"frozen analysis source missing: {source_analysis}")

    dataset_id = "reference"
    generated_total = benchmark_manifest["event_counts"]["generated_total"]
    source_denominator = cutflow["denominators"]["our_reproduction"]
    source_paths = (source_cutflow, source_benchmark_manifest, source_benchmark, source_analysis)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "title": "Original public recast — strong-bm1 High-pT validation",
        "source_kind": "original_recast",
        "source_repository": UPSTREAM_REPOSITORY,
        "source_commit": head,
        "source_dirty": False,
        "source_artifacts": [
            {"path": str(path), "sha256": _sha256(path)} for path in source_paths
        ],
        "reference_sample": "strong-bm1: pp→gluino gluino + 0,1,2j; m_g=2000 GeV; m_χ=850 GeV; τ=0.01 ns",
        "translations": {
            "es": {
                "title": "Recast público original — validación strong-bm1 High-pT",
                "reference_sample": "strong-bm1: pp→gluino gluino + 0,1,2j; m_g=2000 GeV; m_χ=850 GeV; τ=0,01 ns",
            }
        },
        "n_events": generated_total,
        "event_count_semantics": {
            "n_events": "generated events across the three matrix-element multiplicities",
            "raw_recast_events": source_denominator["raw_events"],
            "weighted_recast_denominator": source_denominator["weighted_events"],
        },
        "created_utc": created_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generator_command": generator_command,
        "capabilities": {
            "cutflow": True,
            "atomic_event_cuts": False,
            "jet_observables": False,
            "jet_what_if": False,
            "dv_radial": False,
            "dv_xyz": False,
            "response_weights": False,
        },
    }

    cuts = []
    for order, stage_id in enumerate(EXPECTED_SOURCE_STAGE_IDS, start=1):
        cuts.append(
            {
                "id": stage_id,
                "order": order,
                "source_file": ANALYSIS_SOURCE,
                "published_or_diagnostic": "published",
                "translations": {"es": CUT_TRANSLATIONS_ES[stage_id]},
                **CUT_DEFINITIONS[stage_id],
            }
        )
    cuts_doc = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "unit_conventions": {
            "energy": "GeV",
            "length": "mm",
            "angles": "radians",
            "adapter_conversions": [],
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
            "event_level_note": (
                "Branch pass fractions and distributions are unavailable because the original reference "
                "execution serialized aggregate cutflow only."
            ),
        },
    }

    stages = []
    previous = source_denominator["weighted_events"]
    for source_stage in cutflow["stages"]:
        after = source_stage["our_weighted_events"]
        conditional_loss = None if previous == 0 else (previous - after) / previous
        authors = source_stage["authors_recast_efficiency_pct"]
        relative_difference = None if authors in (None, 0) else (
            source_stage["our_efficiency_pct"] - authors
        ) / authors
        stages.append(
            {
                "cut_id": source_stage["id"],
                "n_before": previous,
                "n_after": after,
                "conditional_loss": conditional_loss,
                "cumulative_efficiency_pct": source_stage["our_efficiency_pct"],
                "reference": {
                    "authors_recast_efficiency_pct": authors,
                    "atlas_full_sim_pct": source_stage["atlas_full_sim_pct"],
                    "atlas_parametric_pct": source_stage.get("atlas_parametric_pct"),
                    "paper_recast_pct": source_stage.get("paper_recast_pct"),
                    "relative_difference_reproduction_vs_authors": relative_difference,
                },
            }
        )
        previous = after

    summary = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "cutflow": {
            "region": "High-pT",
            "count_semantics": "weighted_events",
            "denominator": {
                "weighted_events": source_denominator["weighted_events"],
                "raw_recast_events": source_denominator["raw_events"],
                "generated_events": generated_total,
            },
            "stages": stages,
        },
        "external_validation": {
            "status": "VALIDATED",
            "scope": "High-pT strong-bm1 only",
            "reference": benchmark["reference_result"],
            "uncertainty_status": cutflow["uncertainty"],
            "note": (
                "The historical engineering tolerance is a triage criterion. No pull is claimed because "
                "weighted sum-of-squares and author uncertainties are unavailable."
            ),
            "translations": {
                "es": {
                    "scope": "solo strong-bm1 High-pT",
                    "reference": benchmark["reference_result"],
                    "note": "La tolerancia histórica de ingeniería es un criterio de triaje. No se calcula un pull porque faltan la suma de pesos al cuadrado y las incertidumbres de los autores.",
                }
            },
        },
    }

    validate_dataset(manifest, cuts_doc, summary)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in (
        ("manifest.json", manifest),
        ("cuts.json", cuts_doc),
        ("summary.json", summary),
    ):
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return {"manifest": manifest, "cuts": cuts_doc, "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cutflow", type=Path, required=True)
    parser.add_argument("--source-benchmark-manifest", type=Path, required=True)
    parser.add_argument("--source-benchmark", type=Path, required=True)
    parser.add_argument("--source-checkout", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    command = "python -m preprocess.adapters.original_recast " + " ".join(
        f"--{key.replace('_', '-')} {value}" for key, value in vars(args).items()
    )
    adapt(**vars(args), generator_command=command)
    print(f"wrote {SCHEMA_VERSION} dataset to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
