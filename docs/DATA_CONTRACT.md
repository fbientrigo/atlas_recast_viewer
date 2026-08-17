# `viewer.dataset.v1` data contract

## Boundary

Every source adapter emits the same static JSON directory. The frontend may
branch on declared capabilities, never on `source_kind` or source-specific
field names.

```text
public/data/<dataset_id>/
├── manifest.json   required: identity, provenance, capabilities
├── cuts.json       required: ordered semantic cut definitions
├── summary.json    required when cutflow=true
└── events.json     optional; present only when event capabilities are true
```

All files repeat `schema_version` and `dataset_id`. Cross-file disagreement is
invalid. v1 accepts JSON numbers or explicit `null`; absence is never converted
to zero, false, pass, or unit efficiency.

## Manifest

`manifest.json` contains the frozen source repository/commit/dirty state,
hashed source artifacts, reference sample, creation command, and event-count
semantics. `n_events` is the number generated (30,000 for `strong-bm1`), while
the summary separately records 7,884 raw recast-accepted events and the
9,458.407 weighted denominator.

Capabilities describe serialized data, not code that once held a value. For
the aggregate `reference` dataset only `cutflow` is true. In particular,
`response_weights=false` means that per-event response values are absent even
though the final aggregate A×efficiency is present.

## Cuts

`cuts.json.cuts[]` is strictly ordered and contains:

```text
id, name, order, category, kind
mathematical_definition, physical_meaning, analysis_rationale
source_file, source_line_or_symbol
published_or_diagnostic, depends_on_parameters, requires_fields
parameters              numeric source values used by diagnostics/rendering
```

`kind` is one of `atomic_boolean`, `compound_boolean`, `response_weight`, or
`summary`. The final strong-bm1 stage is `response_weight`: it must not be
presented as an ordinary hard cut. Optional `jet_logic` metadata carries rank
indexing, missing-jet semantics, and thresholds so the UI has no physics
constants.

`unit_conventions` fixes energy to GeV, length to mm, and angles to radians.
Any adapter conversion must be listed; the reference adapter performs none.

Additive presentation fields are optional in v1:

```text
mathematical_latex  source-authored display form; plain definition remains canonical fallback
geometry_overlay    r_z region with nullable r_min_mm, r_max_mm, abs_z_max_mm
translations.es     Spanish name, physical meaning, and rationale
```

An overlay describes a mathematical selection region only. Its presence does
not imply that event coordinates exist and does not enable `dv_radial` or
`dv_xyz`. All threshold values come from the adapter metadata; the renderer
contains no reference-analysis cut constants.

## Summary

`summary.json.cutflow` declares `weighted_events` semantics, an explicit
denominator, and one stage per cut:

```json
{
  "cut_id": "rxy_gt_4_mm",
  "n_before": 9446.493,
  "n_after": 2830.631,
  "conditional_loss": 0.70036,
  "cumulative_efficiency_pct": 29.92715,
  "reference": {}
}
```

Reference fields remain `null` when unavailable. The response-weight stage's
`n_after` is a weighted response yield, not a surviving event count.

## Optional events and diagnostic invariant

`local-reference/events.json` contains real instrumented records:

```text
event_id, subrun, source_event_index
weight, source_weight_mb, valid_weight
observables: sum_pt_GeV, r_max_mm
predicates: jet_selection
response: event_eff, vertex_eff
jets[]: rank, pt_GeV, eta, phi
vertices[]: llp_index, pdg_id, x_mm, y_mm, z_mm, r_mm,
            llp_momentum_GeV,
            selected_track_count, impacted_track_count, mass_GeV,
            vertex_eff, predicates{}, tracks[]
tracks[]: track_index, pdg_id, charge, x_prod_mm, y_prod_mm, z_prod_mm,
          px_GeV, py_GeV, pz_GeV, d0_mm, transverse_distance_mm,
          passes_d0, selected_for_dv
```

DV predicates live per vertex. An event passes the enabled DV selection only
if one vertex satisfies every enabled predicate; booleans from different
vertices must never be combined. Disabling a cut removes that predicate before
this event-by-event/per-vertex recomputation. Aggregate rows are never deleted
to simulate a counterfactual.

Response counterfactuals are deliberately undefined. Stored event/vertex
response factors reproduce the baseline response stage, but the viewer reports
only boolean acceptance after a cut is disabled. This avoids applying the
published response outside its baseline truth-selection domain.

Every modified result must carry the persistent label:

```text
DIAGNOSTIC COUNTERFACTUAL — NOT THE PUBLISHED/REFERENCE ANALYSIS
```

## Simplified event and detector geometry

The local pack embeds the current display fields:

```text
decay vertices: x_mm, y_mm, z_mm, r_mm
recast jets: pt_GeV, eta, phi
charged final daughters: production x/y/z, momentum, exact recast d0 proxy,
                         d0 flag and DV-mass-selection flag
```

`public/data/detector_geometry.json` is source-neutral display metadata with
schema `viewer.detector_geometry.v1`. Each landmark has bilingual names,
bilingual relevance/source notes, `kind`, nominal radius/z support, and source
provenance. Kinds are deliberately
disjoint: `detector_hardware`, `analysis_boundary`, and `response_bin`.
The included Run-2 hardware is limited to the beam pipe, IBL, three pixel
barrels, and innermost SCT barrel. It is not a material map.

An optional future `objects/geometry.json` may still add:

```text
EventGeometry
  event_id
  LLPs[]: pdg_id, px, py, pz
  decay_vertices[]: x_mm, y_mm, z_mm, selected
  jets[]: id, pt_GeV, eta, phi, matched_jet_id
  tracks[]: px, py, pz, pt_GeV, eta, phi, charge, selected, matched_jet_id
```

The frozen aggregate has these quantities internally but does not serialize
them, so its event mode remains disabled. In `local-reference`, vertices are
Pythia truth coordinates and jets are the recast's smeared, pT-sorted objects.
The Three.js scene and straight daughter directions are never described as
reconstructed ATLAS hits or magnetic propagation.

Frontend inspection state is a source-neutral discriminated identity:
`layer(landmark_id)`, `vertex(event_id,index)`, `track(event_id,vertex,index)`,
or `jet(event_id,rank)`. It resolves against validated canonical records; a
missing identity resolves to unavailable rather than a fabricated object.
