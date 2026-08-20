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

An optional `manifest.sample` object carries scientific-campaign identity that
the frontend must not infer from `dataset_id` strings: `family`, `mass_GeV`,
`analysis_region`, `decay_mode`, `ctau_response_mm`, `lifetime_mode`. When a
source's authoritative statistics population (e.g. a full campaign) is larger
than what `events.json` serializes for display, `manifest.n_events` describes
only the displayed subsample — matching the pre-existing convention where
`n_events` means "events.json length," not "events generated" — and
`event_count_semantics.full_campaign_events` records the true statistics-scope
count. `summary.json`'s cutflow always uses the full statistics scope; the UI
must disclose the two scopes whenever they differ (see `AcceptanceStrip`'s
scope note).

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

A boolean cut's predicate normally lives per vertex (`vertices[].predicates`);
the event verdict is an OR across vertices. A cut may instead declare
`predicate_scope: "event"` when its source only ever computed a jet-blind
event-level OR internally and never serialized a per-vertex breakdown — the
boolean then lives directly in `events[].predicates` under the cut's id.
Absence of the field means `"vertex"`, matching every dataset written before
this field existed. A dataset that uses `predicate_scope: "event"` for every
non-jet boolean cut may leave `vertices: []` on every event; `dv_radial` and
`dv_xyz` stay `false` in that case (see capabilities below).

`jet_logic` may additionally declare, generically and optionally:

```text
additional_requirement.supported     boolean
additional_requirement.predicate_id  name of the event-level boolean in events[].predicates
additional_requirement.scales_with_s boolean (always false for every dataset seen so far)
threshold_scale.supported            boolean — the ONLY thing that enables the `s` UI control
threshold_scale.baseline             the s value that reproduces the stored baseline predicate
threshold_scale.values               discrete, validated s grid (never assumed by the frontend)
```

When `threshold_scale.supported` is true, `jet_selection` may be recomputed at
any declared `s` from `events[].jets[].pt_GeV` and these branch thresholds
(`core/selection.ts::jetSelectionPasses`); `s` rescales only the ordinary
ranked-jet branches, never `additional_requirement`. Absence of
`threshold_scale` (or `supported: false`) means the frontend always uses the
stored baseline `predicates.jet_selection` — this is the case for every
High-pT dataset.

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

`jets[].eta` and `jets[].phi` are nullable: a source that serialized jet pT
without a reconstructed direction (no eta/phi ever computed, or computed
internally but never written out) reports `null` rather than a fabricated
angle. `GeometryViewer`/`ObjectInspector` render such a jet without 3D
placement and show `—` for direction, the same "missing identity resolves to
unavailable, never fabricated" rule already applied to disabled-cut
counterfactuals.

`events.json` may exist with `capabilities.dv_radial` and `capabilities.dv_xyz`
both `false`, provided at least one of `jet_observables`/`dv_radial`/`dv_xyz`
is `true` and `atomic_event_cuts` is `true`. In that case every event's
`vertices` array must be empty — no vertex object is serialized without real
coordinates — and any DV-style boolean cut must be `predicate_scope: "event"`.
This lets a jet-only source (real pT, no geometry) support cutflow, atomic
cut disabling, and jet inspection honestly, without a 3D/R–z/x–y scene.

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

## Optional geometry pack

A source whose primary `events.json` has no per-vertex coordinates (e.g. the
H2 mass-control campaign, Step 1) may still recover real geometry for a small,
deterministically curated subset of events via telemetry replay of the frozen
source (see `docs/H2_GEOMETRY_REPLAY_CONTRACT.md`). When it does, the dataset
directory gains a sibling file:

```text
public/data/<dataset_id>/geometry_events.json   # same EventsDocument shape as events.json
```

and `manifest.json` gains an optional block whose mere presence signals the
file exists:

```json
"geometry_pack": {
  "event_count": 100,
  "selection_method": "curated_pedagogical_cohorts",
  "replay_mode": "B",
  "cohort_summary": {"accepted_baseline": 20, "fail_jet_selection_s1": 15, "...": "..."}
}
```

`geometry_events.json` is validated with the same `validate_events`/
`validateEventsDocument` function used for `events.json`, against its own
`geometry_pack.event_count` (not `manifest.n_events`) and its own file name,
with `dv_radial`/`dv_xyz` overridden to `true` for that call only — the
on-disk `capabilities.dv_radial`/`dv_xyz` keep describing `events.json`
honestly (still `false` when it has no geometry). The frontend performs the
same override when routing which array feeds `GeometryViewer`
(`App.svelte`'s `geometryPanelEvents`/`geometryPanelCapabilities`); the
component itself is unmodified and never branches on `source_kind`.

A vertex inside a geometry pack may carry a genuine per-vertex boolean
breakdown for a cut declared `predicate_scope: "event"` at the dataset level
(this specific pack computed one, even though the primary statistics
population never serialized a per-vertex breakdown). `vertex.predicates` is
therefore validated as "at least every predicate_scope=vertex cut", not an
exact-key match; `event.predicates` remains the sole authority for cut-scope
routing everywhere else.

The curated 100 events are a **deterministic pedagogical/coverage sample**
stratified into cohorts (accepted baseline, first-failure-per-cut,
jet-threshold-borderline, `s`-sensitive, coverage-extreme) — never an
unbiased estimator of acceptance. `summary.json`'s cutflow and every
acceptance number always come from the full statistics-scope population; the
UI discloses the geometry pack's count separately (`AcceptanceStrip`'s
`geometryPackCount` note) and never substitutes it into a denominator. The
same 100 events are reused as the diagnostic threshold scale `s` changes:
`s` only reclassifies (`jet_selection` boolean), it never reruns replay or
alters any stored coordinate.

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
