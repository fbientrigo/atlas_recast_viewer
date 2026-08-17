# Validation contract and failure modes

## Two validation levels

Internal adapter validation is exact serialization agreement. For the same
source artifact, every canonical weighted denominator, stage yield, efficiency,
and ordering must equal `cutflow.json`; no tolerance is used. Contract checks
also enforce finite non-negative yields, monotonic flow, explicit nulls,
capability dependencies, and a clean checkout at the pinned commit.

External validation is inherited evidence, not rerun here. The selected
`strong-bm1` High-pT reproduction is marked `UPSTREAM_STRONG_BM1_VALIDATED` by
its frozen report. Relative differences against the authors' archived recast
are approximately 0.06% at jet/fiducial, 0.70% at the boolean DV acceptance,
and 0.90% at final A×efficiency. The historical 20% gate is an engineering
triage criterion, not a statistical theorem. No pull is reported because
event weights/sum-of-squares and author uncertainties are unavailable.

The interactive dataset has a separate local regression contract. The same
500-event LHE and Pythia seed are run through a freshly compiled frozen source
and a telemetry-only copy. Their complete stdout is identical after replacing
only Pythia's wall-clock field. Event telemetry independently reproduces all
six printed High-pT boolean percentages and final A×efficiency at the source's
six-significant-digit print precision. This validates instrumentation, not a
new inclusive publication-level benchmark.

The event pack additionally requires every stored `R` to reproduce
`hypot(x,y)`, every track `d0` to reproduce the exact C++ proxy
`r_prod*sin(phi_prod-phi_track)` (including its angular folding), and track
flags to reproduce the stored impacted/selected counts. These checks use
serialization-level numerical tolerance and are reported explicitly.

## Guardrails

| Failure mode | Detection or mitigation |
| --- | --- |
| Wrong source identification | Record public repository, exact commit, current dirty state, artifact paths, and SHA-256. |
| Adapter semantic drift | One explicit source-stage mapping plus exact source/canonical tests. |
| UI hard-codes thresholds | Thresholds and branch semantics come from `cuts.json`. |
| OR accidentally becomes AND | Toy tests where only j5 passes; Trackless ordinary and displaced legs are tested as AND. |
| Missing jN treated as a jet | Rank-existence guards and `None` tests; no sentinel-to-zero conversion. |
| Boolean cut confused with response map | Required semantic `kind`; final stage is `response_weight`. |
| Aggregate cutflow used for what-if | Diagnostic availability requires a loaded event pack; aggregate reference toggles remain disabled. |
| Weight ignored | Generated, raw recast, weighted denominator, and weighted stage yields are separate fields. |
| Missing value coerced | Python and TypeScript validators preserve `null` and reject absent required fields. |
| Predicates from different vertices combined | Tests require one vertex to satisfy every enabled DV predicate. |
| Truth geometry called reconstruction | UI labels vertices as truth and jets as simplified recast objects; the cylinder is not detector reconstruction. |
| Detector shell confused with cut or response bin | Geometry metadata has distinct kinds, styles, controls, and per-landmark provenance. |
| Inspector invents an object or value | Stable typed object identities resolve only against validated canonical events/landmarks; unit tests reject unresolved identities. |
| A jet rank is given a fictitious branch | Inspection returns no threshold/decision outside the source-defined j4–j7 branches. |
| Non-reproducible event examples | Cohorts sort by event id and use deterministic pagination; no `Math.random()`. |
| Generic d0 substituted for source proxy | Canonical tracks store the source value; Python and TypeScript tests recompute the exact C++ formula. |
| Diagnostic shown as published | Any disabled cut activates a persistent bilingual counterfactual label. |
| Response extrapolated after cut removal | Diagnostic mode reports boolean acceptance; baseline A×eff remains fixed and separately labeled. |
| Frontend becomes H2-specific | Loader/renderers consume only the canonical schema and capabilities. |
| Huge data bundle | Aggregate JSON by default; event packs are optional and scoped. |
| Architecture outruns science | Every module needs a serialized capability and acceptance test. |

## Commands and current result

```bash
make validate       # exact adapter/source report
make validate-local # exact local instrumentation/event report
make test           # Python mapping/schema/logic tests
make frontend-test  # TypeScript loader/selection tests
make build           # static production assets
```

Generated reports are `validation/reference_validation.json` and
`validation/local_instrumentation_validation.json`. Absence of
`reference/events.json` is validated against false capabilities; presence and
shape of `local-reference/events.json` are validated against true capabilities.
`detector_geometry.json` is also validated in TypeScript, including bilingual
relevance/source notes and distinct 299 mm SCT hardware and 300 mm analysis
boundary records. Canonical charged-daughter production coordinates include
finite x/y/z; the z value is copied from already-recorded telemetry and does
not alter the instrumentation regression.

The exact author-local `strong_0/1/2_2000_850_0p01.lhe.gz` files are not
distributed; `benchmarks/upstream/strong-bm1/missing_inputs.md` records this.
They are not required for local teaching interactivity. The retained local 0j
LHE was generated independently with the reconstructed strong-bm1 card and is
explicitly labeled as a 500-event 0j slice. Its final 27.25118% is close to the
26.84045% inclusive aggregate, but no equivalence or precision claim is made.

MG5 3.5.3 rewrote the tiny neutralino width to zero in the generated LHE
header while retaining its four RPV channels. The checked transform
`fix_lhe_neutralino_width.py` changes exactly that one header to the documented
`6.582120e-14 GeV`; both recast binaries consume the same repaired LHE.
