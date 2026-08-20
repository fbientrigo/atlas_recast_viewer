# H2 mass-control source inventory (Step 1A)

Status vocabulary (per gauntlet spec): `AVAILABLE`, `DERIVABLE`, `AGGREGATE_ONLY`,
`INTERNAL_NOT_SERIALIZED`, `MISSING`, `UNKNOWN`. These map onto the older
`docs/SOURCE_INVENTORY.md` vocabulary as: `AVAILABLE`≈`AVAILABLE`,
`INTERNAL_NOT_SERIALIZED`≈`INTERNAL_BUT_NOT_SERIALIZED`, `MISSING`≈`NOT_AVAILABLE`.

## Baseline decision

Primary campaign: `../dihiggs_llp_recast-jet-threshold-diag/results/mass_control_jet_recovery_20260816T173704Z/`
(`DECISION.md` is the written scientific verdict and semantic authority for what
this campaign is and is not). Its `outputs/` directory contains **aggregate-only**
CSVs (`mass_control_cutflow.csv`, `jet_response_vs_mass.csv`,
`conditional_loss_ranking.csv`, `n_generated.json`, `production_sparse.csv`,
`coupling_audit_summary.json`) — no event-level rows. `outputs/analyze_mass_control.py`
(the generating script, hence semantic authority for column meaning) shows these
aggregates are built by loading real **per-event CSVs** from two upstream run
directories and recomputing everything with
`../jet_threshold_response_20260815T230503Z/scripts/extract_response_table.py`
(`ert`), which is therefore the semantic authority for the exact jet-selection and
`s`-scaling logic.

Per-event source (the actual event-level artifact):

```
<CAMPAIGN>/runs/main/mH<mass>/seed_<seed>/events.csv
```

where `<CAMPAIGN>` is `jet_threshold_response_20260815T230503Z` for masses
`{130,150,170,200,250}` and `mass_control_jet_recovery_20260816T173704Z` for
masses `{300,330,345}` (both dirs share the identical `events.csv` schema — the
new masses' script imports `ert` from the old campaign and reuses its column
producer). Two seeds (`81001`, `81002`) × 10000 events each = 20000 events/mass,
matching `n_generated.json`.

The generating C++ is
`jet_threshold_response_20260815T230503Z/src/recast_2301_13866.cc`, forked from
the validated `dihiggs_llp_recast` upstream (`docs/causal_map_trackless_cutflow.md`
cites commit `0cd325c`) with the DV/vertex loop hoisted above the
`if (!passJetSelection) continue;` gate so DV booleans are computed for **every**
event, independent of jet-selection outcome (verified bitwise against the frozen
R8 2000-event regression contract before being trusted —
`reference/baseline_regression.json`, `scripts/verify_gate.py`).

`physical_trajectory_overlay.csv`, `trajectory_coupling_audit.csv`, and
`coupling_audit_summary.json` belong to the **separate** physical-2HDM-lifetime
trajectory family (`scripts/build_trajectory_artifacts.py`). Per `DECISION.md`
these are explicitly not the mass-control sample and are **not used** as the H2
adapter's primary input.

## Step 1A answers

1. **Masses that exist:** `130, 150, 170, 200, 250, 300, 330, 345` GeV (8 masses,
   `outputs/n_generated.json`). All 8 have identical `events.csv` schema and full
   artifacts. Chosen Step-1 mass: **150 GeV** — the prompt's default; inspection
   found no other mass with materially cleaner or more complete data (all 8 are
   schema-identical), so the default stands undisturbed.
2. **Events per mass:** 20000 generated (`valid_weight==1` for all of them in the
   `mH150` sample checked; `weight` is a uniform per-event LHE weight, not a
   varying physics weight — see `extract_response_table.py` docstring).
3. **Fixed `ctau_response`:** `4.326221529733112` mm (frozen, identical across all
   8 masses; stated in `analyze_mass_control.py` docstring and `DECISION.md`).
4. **Decay mode:** forced `H2 → b b̄` (stated in both `DECISION.md` and
   `analyze_mass_control.py` docstring; not re-derived from LHE herein).
5. **File/field map** — see table below.
6. **`pass_*` semantics:** independent atomic booleans. The DV loop is
   *jet-blind* (`causal_map_trackless_cutflow.md` §1: "computed in a loop over
   truth LLP mothers, using only truth decay vertex positions and truth daughter
   kinematics"), so `pass_fiducial`, `pass_rvtx4`, `pass_d0`, `pass_ndecay5`,
   `pass_mdv10`, `pass_vertex_acc` do **not** depend on the jet-selection outcome
   for a given event. `extract_response_table.py::cutflow_rows` applies them
   *cumulatively* only for building an 8-stage waterfall table; the underlying
   flags are atomic and safe to recompute independently per canonical-cut
   semantics (mirrors the existing `local-reference` per-vertex predicate model).
7. **Downstream quantities for jet-cut failures:** **Yes** — this is the entire
   point of the diagnostic instrumentation (`causal_map_trackless_cutflow.md` §3
   "What this study did about it"). All DV booleans, `r_max`, `sum_pt`, `v_eff`,
   `event_eff_trackless` are populated for every event regardless of jet-selection
   outcome.
8. **Per-vertex information:** `MISSING`. The vertex loop iterates over truth LLP
   mothers internally but only the *event-level OR* over vertices is serialized
   per predicate (one boolean column per DV stage, not one row per vertex).
   `r_max` is the single scalar "farthest truth LLP decay radius" (source
   `recast_2301_13866.cc:319,328`), not a per-vertex list.
9. **x/y/z, jet eta/phi, tracks, d0 (serialized):** `MISSING` for this specific
   mass-control family. The C++ computes them internally (`xDec/yDec/zDec`,
   `rTrack*sin(ΔΦ)`, jet 4-vectors) but never writes them to `events.csv` —
   `INTERNAL_NOT_SERIALIZED` at the code level, `MISSING` at the artifact level.
   No teaching/geometry event pack exists anywhere under `dihiggs_llp_recast*` or
   `dihiggs_hep_cross*` for this family (searched for `x_mm`, `xDec`,
   `*telemetry*`, `*events.ndjson*`; only hits are the generic pyarrow package and
   the diagnostic source files already covered above).
10. **`s`-dependence artifacts:**
    - `jet_threshold_response_20260815T230503Z/response_table/{response_table,branch_table}.{csv,parquet}`
      — full per-`(mass,s)` 8-stage cutflow and per-branch ablation, masses
      `{130,150,170,200,250}` only, `s ∈ {1.0,0.9,0.8,0.7,0.6,0.5,0.4,0.3,0.2,0.1}`
      (10 values, `SCALES = [round(1.0-0.1*i,1) for i in range(10)]`).
    - `mass_control_jet_recovery_20260816T173704Z/outputs/mass_control_cutflow.csv`
      — same 10-value `s` grid, **all 8 masses** (verified: `cut -d, -f2
      mass_control_cutflow.csv | sort -u` → `0.1..1.0` step 0.1, no other values).
      This is the authoritative validation target for Step 3F.
    - `outputs/jet_response_vs_mass.csv` — a display-only subset
      (`R_jet_s0p9/0p7/0p5/0p3/0p1`), not the full grid; not used as a validation
      source (use `mass_control_cutflow.csv` instead, which has the complete grid).

## Availability matrix

| Concept | File / source | Status | Notes |
|---|---|---|---|
| j4/j5/j6/j7 pT (per event) | `events.csv: jet4_pt..jet7_pt` | AVAILABLE | `-1` sentinel for a missing rank (confirmed: row with `n_jets=6` has `jet7_pt=-1`; source `recast_2301_13866.cc:410-413`: `detector.jets.size()>=7 ? ... : -1.`) |
| Trackless ordinary OR (j4..j7 > 137/101/83/55) | `events.csv` cols + `extract_response_table.py:45,79-86` | AVAILABLE | Source: `recast_2301_13866.cc:402-405`. Strict `>`, rank-existence-guarded. |
| Trackless additional (displaced) leg | `events.csv: trackless_additional` | AVAILABLE | Does **not** scale with `s` (`extract_response_table.py:86`: `... & (df["trackless_additional"]==1)`, unconditioned on `s`). |
| Fiducial predicate | `events.csv: pass_fiducial` | AVAILABLE | Jet-blind, atomic. |
| R_vertex > 4 mm predicate | `events.csv: pass_rvtx4` | AVAILABLE | Jet-blind, atomic. |
| d0 predicate | `events.csv: pass_d0` | AVAILABLE | Jet-blind, atomic. |
| Ntracks ≥ 5 predicate | `events.csv: pass_ndecay5` | AVAILABLE | Jet-blind, atomic. |
| mDV > 10 GeV predicate | `events.csv: pass_mdv10` | AVAILABLE | Jet-blind, atomic. |
| Final vertex acceptance | `events.csv: pass_vertex_acc` | AVAILABLE | Numerically identical to mDV stage per `causal_map...md` (set the moment invariant mass passes). |
| v_eff (vertex response) | `events.csv: v_eff` | AVAILABLE | Per event. |
| event_eff (Trackless) | `events.csv: event_eff_trackless` | AVAILABLE | `eventEff_Trackless(r_max, sum_pt)`, pure lookup, no RNG. |
| r_max | `events.csv: r_max` | AVAILABLE | Scalar farthest truth decay radius; not per-vertex. |
| sum_pt | `events.csv: sum_pt` | AVAILABLE | Scalar sum of **all** reconstructed jet pT (not just j4-j7). |
| Event weight | `events.csv: weight, valid_weight` | AVAILABLE | Uniform per-event LHE weight. |
| Per-vertex breakdown | — | MISSING | Only event-level OR over vertices is serialized. |
| Vertex x/y/z | — | MISSING (INTERNAL_NOT_SERIALIZED in C++) | Computed as `xDec/yDec/zDec`, never written out. |
| Jet eta/phi | — | MISSING (INTERNAL_NOT_SERIALIZED in C++) | Only pT is written. |
| Individual tracks / track d0 | — | MISSING (INTERNAL_NOT_SERIALIZED in C++) | `rTrack*sin(ΔΦ)` computed internally, not serialized. |
| Teaching/geometry event pack (100-500 events, full geometry) | — | MISSING | Searched the whole `atlas_dihiggs` tree; none exists for this family. Building one requires a new telemetry-instrumented binary analogous to `recast_viewer/preprocess/instrumentation/recast_2301_13866_telemetry.cc`, forked from the diagnostic C++ above — not attempted in Step 1 (see Step 1G decision below). |
| `s`-grid precomputed dependence | `mass_control_cutflow.csv`, `response_table.{csv,parquet}` | AVAILABLE | 10-value grid, `1.0..0.1` step `0.1`, confirmed for all 8 masses in `mass_control_cutflow.csv`. |
| Production cross sections | `outputs/production_sparse.csv` | AVAILABLE | Separate concern (cross-section, not acceptance); not used by the viewer adapter. |
| Physical-lifetime trajectory | `outputs/physical_trajectory_overlay.csv` | AVAILABLE but OUT OF SCOPE | Explicitly a different sample family (Section 3 of the gauntlet spec, `DECISION.md`). Not ingested. |

## Step 1B — statistics scope vs display scope decision

**Case B applies, with a specific shape.** The campaign has full **event-level**
statistics (20000 events/mass with real jet pT, all DV atomic predicates, and
response weights — enough to exactly recompute the published cutflow and the
full `(mass, s)` grid offline, matching `mass_control_cutflow.csv` bit-for-bit).
But it has **no serialized geometry** (no vertex x/y/z, no jet eta/phi, no
tracks) for any subset, teaching-sized or otherwise — this is a hole in the
*source*, not a statistics/display scope mismatch of the reference-dataset kind.

Adopted design (smallest change consistent with the existing `n_events` vs
`summary.cutflow.denominator` split already present in the schema — see
`DATA_CONTRACT.md`: "`n_events` is the number generated... while the summary
separately records..."):

- **Statistics scope (authoritative):** all 20000 events/mass, recomputed exactly
  from `events.csv`, cross-validated against `mass_control_cutflow.csv` /
  `response_table.csv` for every `(mass, s)` pair (Step 1F/3F). Drives
  `summary.json.cutflow.denominator.weighted_events` and all cutflow stages.
- **Display scope (interactive):** a bounded subsample (target ~300-500 events,
  final count decided in Step 1C/1G) drawn from the same 20000, serialized into
  `events.json` for the jet inspector. `manifest.n_events` describes this
  subsample size, exactly matching the existing `local-reference` convention
  (`manifest.n_events == len(events.json.events)`, enforced by
  `preprocess/validate_dataset.py::validate_events`). The UI must show
  "statistics: full campaign (20000) / display: N of 20000" per gauntlet §3E —
  this is a **required**, not optional, disclosure here because the scopes
  genuinely differ (unlike `local-reference`, which is its own independently
  generated 500-event sample and states its scope implicitly).
- **Geometry (dv_radial/dv_xyz) capability:** not available from this source.
  Step 1 ships with these capabilities **false** and documents the limitation
  rather than fabricating coordinates. `jet_observables`/`jet_what_if` remain
  achievable because jet pT is real; jet `eta`/`phi` are not available either, so
  the schema needs a **generic** (not H2-specific) extension: nullable jet
  `eta`/`phi`, with `GeometryViewer`/`ObjectInspector` displaying "—" and
  skipping 3D placement when direction is absent — the same "missing identity
  resolves to unavailable, never fabricated" principle already documented for
  cut-object resolution in `DATA_CONTRACT.md`. This extension benefits any future
  adapter with pT-only jets, not just H2.

This keeps the existing `viewer.dataset.v1` contract's meaning of `n_events`
completely intact (it already means "events.json length", not "generated count",
whenever an event pack exists) — no redefinition, only a same-shape reuse plus
one generic nullable-field relaxation for jet direction.
