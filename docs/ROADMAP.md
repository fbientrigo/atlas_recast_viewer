# Roadmap

The local 500-event 0j teaching slice now closes the first implementation of
LT1–LT3: telemetry regression, per-vertex boolean counterfactuals, linked
Three.js/R–z/x–y geometry, exact `d0`, and deterministic small cohorts. The published aggregate
remains non-interactive, as required by its capabilities.

## LT1 — Reference instrumentation

**Local 0j status: complete. Inclusive 0j+1j+2j status: deferred.**

- **Goal:** Export missing atomic event information from an instrumented copy of the original recast; telemetry only.
- **Required data:** Event id/weight, j4–j7 pT and branch booleans, DV predicates/coordinates, track counts/mass, r_max, response factors.
- **Implementation:** Add a deterministic sidecar writer without touching selections, maps, RNG calls, or control flow.
- **Acceptance test:** Same input and seed give identical cut counts and weighted acceptance before/after instrumentation.
- **Blocked if:** Any physics output changes. Exact private inputs are needed only to instrument the historical inclusive execution, not the local teaching sample.

## LT2 — Honest cut what-if engine

**Boolean ON/OFF status: complete for local 0j. Threshold variation: pending.**

- **Goal:** Enable cut ON/OFF and threshold changes from atomic records.
- **Required data:** Complete event predicates, observables, weights, cut dependency metadata.
- **Implementation:** Recompute the jet leg per event and require one vertex to satisfy all enabled DV predicates; isolate baseline and diagnostic state.
- **Acceptance test:** Baseline equals original recast exactly; modified toy cases independently verify denominators and losses.
- **Blocked if:** Any required predicate/observable is missing or has adapter-dependent semantics.

## LT3 — Event geometry v1

**Linked R–z, x–y, OrbitControls 3D, layer/object inspection, and straight truth-track pedagogy: complete.**

- **Goal:** Add R–z, x–y, and simple cylindrical views.
- **Required data:** Per-vertex x/y/z, jet pT/eta/phi, relevant tracks or charged daughters.
- **Implementation:** Current compact geometry is embedded in `events.json`; add `objects/geometry.json` only when richer tracks/objects justify it.
- **Acceptance test:** Stored coordinates reproduce `R=sqrt(x²+y²)`; displayed `d0` reproduces the exact source proxy; detector landmarks carry authoritative provenance.
- **Blocked if:** Coordinates cannot be traced to truth/recast quantities or would be mislabeled as detector hits.

## LT4 — Curated pedagogical cohorts

**Runtime deterministic cohorts: complete. Persisted/precomputed packs: optional.**

- **Goal:** Precompute accepted, fails-jets, fails-radius, fails-displacement, fails-multiplicity, fails-mass, and borderline groups.
- **Required data:** Atomic predicates and stable event ids.
- **Implementation:** Deterministic cohort rules in preprocessing, with provenance.
- **Acceptance test:** Every cohort assignment follows mechanically from canonical predicates; no hand labels.
- **Blocked if:** Predicates are aggregate-only or multiple failure ordering is undefined.

## LT5 — H2 adapter

- **Goal:** Connect current H2 telemetry without changing core frontend components.
- **Required data:** Instrumented `events.csv`, sample manifests, cut/response provenance, explicit missing-sentinel semantics.
- **Implementation:** Map H2 columns and `-1` jet-rank sentinels to canonical nulls/predicates in `H2Adapter`.
- **Acceptance test:** Original and H2 adapters emit `viewer.dataset.v1` and render through the same components.
- **Blocked if:** A basic H2 meaning needs a frontend `source_kind` branch; reassess the schema first.

## LT6 — Sample comparison

- **Goal:** Compare reference with H2 masses 150, 250, 300, and 345 through common fields/cuts.
- **Required data:** Adapter-declared semantic/unit compatibility and matched summary fields.
- **Implementation:** Comparison model keyed by canonical ids, never raw source columns.
- **Acceptance test:** No comparison is rendered where units or semantics differ between adapters.
- **Blocked if:** Provenance or selection modes differ ambiguously.

## LT7 — Shareable teaching bundle

- **Goal:** Produce a static offline artifact for a professor.
- **Required data:** Valid canonical datasets and local frontend assets.
- **Implementation:** Package `dist/` and selected aggregate/event packs; remove network dependencies.
- **Acceptance test:** A clean checkout builds the bundle and it opens without Python, backend, or network access.
- **Blocked if:** Runtime fetches escape the packaged asset tree.
