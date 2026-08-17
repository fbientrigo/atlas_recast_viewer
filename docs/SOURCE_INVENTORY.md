# Source inventory

## Baseline decision

The reference physics source is the clean detached checkout at
`../dihiggs_llp_recast-release-v1/external/recastingCodes`, upstream repository
`https://github.com/llprecasting/recastingCodes.git`, commit
`d4047c744062094c9f88e507bb1ccf69e9fe88d6`. The selected analysis is
`DisplacedVertices/ATLAS-SUSY-2018-13_GCottin`, the public recast of the ATLAS
DV+jets search arXiv:2301.13866 documented by the recast authors in
arXiv:2404.06126. `git status --short --branch` reports detached `HEAD` with no
changes in this nested upstream checkout.

`../dihiggs_llp_recast-release-v1/` is the closest immutable local package (no
outer `.git` metadata). The mutable Git-backed sibling
`../dihiggs_llp_recast/` is not the baseline.
`../dihiggs_llp_recast-jet-threshold-diag/` is an
instrumented H2 diagnostic worktree and is future compatibility evidence only.

The published viewer dataset uses the independently reproduced High-pT
`strong-bm1` aggregate artifacts under
`../dihiggs_llp_recast-release-v1/results/upstream/strong-bm1/`. Its manifest
classifies the run as unmodified upstream physics and the validation report
marks this benchmark `UPSTREAM_STRONG_BM1_VALIDATED`. The corresponding public
authors' archived output is `recast_code/2_results/strong/gluino_run01.txt`.
The authors' private LHE sample was not recovered; the local reproduction used
independent 0j/1j/2j generation.

The second dataset, `local-reference`, is deliberately separate. Its input is
a newly generated 500-event 0-parton slice at the reconstructed strong-bm1
point, with MG seed 424201 and Pythia seed 424202. It uses the same frozen C++
physics source plus a project-owned telemetry copy. It is evidence for local
event pedagogy, not a replacement for the inclusive benchmark.

## Availability matrix

Status vocabulary is exact: `AVAILABLE`, `DERIVABLE`,
`INTERNAL_BUT_NOT_SERIALIZED`, `NOT_AVAILABLE`, or `UNKNOWN`.

| Concept | Original recast source | Available now? | Representation | Needed by viewer? | Notes |
| ------- | ---------------------- | -------------: | -------------- | ----------------: | ----- |
| Event sequence/id | C++ event loop, `recast_2301_13866.cc:89` | INTERNAL_BUT_NOT_SERIALIZED | Loop index only; not printed | Future | No stable event record in the reference artifacts. |
| Sample identity | benchmark and result manifests | AVAILABLE | `strong-bm1`, High-pT | Yes | Frozen benchmark metadata includes masses, lifetime, process, and region. |
| Event weight | `pythia.info.weight()` and `mergingWeight()`, source lines 105–115 | INTERNAL_BUT_NOT_SERIALIZED | Per-event CKKW-L weight; aggregate weighted denominator is serialized | Yes | Weighted denominator is 9458.407; raw accepted-event count is 7884. |
| Random seeds | benchmark metadata | AVAILABLE | 0j=201, 1j=202, 2j=203 | Provenance | No per-event RNG state is serialized. |
| Jet 1…N pT | `detector.jets`, source lines 124–129 and 200–216 | INTERNAL_BUT_NOT_SERIALIZED | Smeared, pT-sorted `Vec4` collection | Future | Only aggregate jet-selection yield is present for `strong-bm1`. |
| Jet eta/phi | `ToyDetector::jets`; matching at source lines 155–194 | INTERNAL_BUT_NOT_SERIALIZED | Smeared `Vec4` values | Future geometry | Not emitted by the original executable. |
| Jet algorithm/minimum | `Simpler_ToyDetector.cc:42–43,176–178` | AVAILABLE | FastJet kT, R=0.4, inclusive pT > 20 GeV | Yes | Source metadata, not event data. |
| High-pT j4/j5/j6/j7 branches | source lines 200–207 | AVAILABLE | OR of j4>250, j5>195, j6>116, j7>90 GeV, with rank existence guards | Yes | Selected `strong-bm1` region. Missing rank means that branch is false. |
| Trackless j4/j5/j6/j7 branches | source lines 209–216 | AVAILABLE | OR of j4>137, j5>101, j6>83, j7>55 GeV | Future H2 | Definition is available; event values/fractions are absent from the reference dataset. |
| Displaced/trackless jet leg | source lines 150–194 and 218–224 | AVAILABLE | matched leading displaced jet >70 OR second >50 GeV | Future H2 | Combined with the ordinary Trackless OR using AND. |
| LLP identities/count | source lines 131–140 | INTERNAL_BUT_NOT_SERIALIZED | mother indices for abs(PDG)=1000022/23/24 | Future | Count is recomputed internally per event. |
| Decay x/y/z | source lines 242–248 | INTERNAL_BUT_NOT_SERIALIZED | Pythia truth decay coordinates in mm | Future geometry | Must never be presented as reconstructed detector hits. |
| DV transverse radius R | source line 247 | INTERNAL_BUT_NOT_SERIALIZED | `sqrt(x^2+y^2)` in mm | Yes/future | Aggregate cut stages exist, but no distribution or event values. |
| r_max | source lines 239,248 | INTERNAL_BUT_NOT_SERIALIZED | maximum LLP transverse decay radius in mm | Future response | Used by the event-efficiency map. |
| Number of LLP mothers | source lines 133–140 | INTERNAL_BUT_NOT_SERIALIZED | integer vector length | Future | Not printed. |
| Track d0 proxy | source lines 263–270 | INTERNAL_BUT_NOT_SERIALIZED | `rTrack*sin(deltaPhi)` in mm | Yes/future | Aggregate “at least one |d0|>2 mm” stage is serialized. |
| Selected track count | source lines 253–282 | INTERNAL_BUT_NOT_SERIALIZED | count with transverse-distance >520 mm and pT/|q| >1 GeV | Yes/future | Aggregate >=5 stage is serialized. |
| DV mass | source lines 256,281–282,309–311 | INTERNAL_BUT_NOT_SERIALIZED | pion-mass-hypothesis invariant mass in GeV | Yes/future | Aggregate >10 GeV stage is serialized. |
| Vertex efficiency | `vertexEff` and source lines 316,319 | INTERNAL_BUT_NOT_SERIALIZED | 12x8x8 lookup; event union `1-product(1-eff)` | Yes | Final weighted result includes it; per-event values are absent. |
| Event efficiency | `eventEff_HighPT(rMax,sumPT)`, source line 339 | INTERNAL_BUT_NOT_SERIALIZED | response-map weight | Yes | This is a weight, not a hard cut. |
| Material veto | source and artifacts searched | NOT_AVAILABLE | None found as a separate predicate | Future | Do not infer one from the vertex-efficiency radial dependence. |
| Response maps | `efficiency.cc` | AVAILABLE | embedded lookup arrays and binning | Yes | Definitions are source-visible; lookup inputs are not serialized. |
| Jet selection predicate | source lines 197–229 | INTERNAL_BUT_NOT_SERIALIZED | per-event booleans; aggregate weighted yield available | Yes | High-pT and Trackless regions are counted separately. |
| Fiducial predicate | source lines 285–289 | INTERNAL_BUT_NOT_SERIALIZED | any LLP vertex with R<300 mm and |z|<300 mm | Yes | Aggregate weighted yield available. |
| R>4 mm predicate | source lines 291–295 | INTERNAL_BUT_NOT_SERIALIZED | cumulative per-vertex boolean | Yes | Aggregate weighted yield available. |
| d0 predicate | source lines 297–301 | INTERNAL_BUT_NOT_SERIALIZED | at least one impacted daughter | Yes | Aggregate weighted yield available. |
| Track multiplicity predicate | source lines 303–307 | INTERNAL_BUT_NOT_SERIALIZED | selectedCount >=5 | Yes | Aggregate weighted yield available. |
| DV mass predicate | source lines 309–313 | INTERNAL_BUT_NOT_SERIALIZED | mDV >10 GeV | Yes | Aggregate weighted yield available. |
| Final vertex acceptance | source lines 315–319 | INTERNAL_BUT_NOT_SERIALIZED | compound boolean plus per-vertex efficiency union | Yes | Raw acceptance and response weighting are distinct. |
| Final A x efficiency | source lines 336–340 | AVAILABLE | weighted aggregate | Yes | `strong-bm1`: 2538.679 weighted events, 26.84045%. |

## What the source actually serializes

The original executable prints aggregate weighted percentages/yields and an
inclusive merged cross section to stdout. It does not write event rows. The
portable reference artifacts convert those aggregates to `cutflow.json` and
`comparison.json`; they do not add atomic predicates. Therefore the v1
reference dataset supports cutflow, source-defined jet logic text, and
source-defined geometry boundaries, but not event inspection, jet
distributions, event-point geometry, or honest cut disabling.

The H2 diagnostic copy demonstrates a future adapter target: its `events.csv`
contains per-event weights, j4–j7 pT with `-1` missing-rank sentinels, branch
booleans, DV-stage predicates, `r_max`, `sum_pt`, and response values. Those
fields are telemetry from an instrumented copy, not evidence that the frozen
original dataset contains them. No H2 data are ingested in v1.

## Local instrumented availability

For `local-reference`, the following original-source quantities are now
`AVAILABLE`: stable local event sequence, normalized and raw merging weight,
j1–j7 pT/eta/phi, High-pT jet predicate, source-considered LLP mother records,
x/y/z/R/r_max, per-vertex atomic DV predicates, selected/impacted track counts,
DV mass, vertex response, and High-pT event response. Telemetry also exposes
LLP momentum and each charged final recursive daughter's production x/y/z,
momentum, exact C++ `d0` proxy, `passes_d0`, and `selected_for_dv`. This
telemetry-only addition passed the same upstream/instrumented regression.
Reconstructed detector hits, fitted tracks, and per-track reconstruction
failure reasons remain `NOT_AVAILABLE`.

The source considers every neutralino/chargino record matched by its original
mother scan. The event pack preserves those records—including coincident
copies—because deduplicating them would silently change the source's vertex
efficiency union. The UI calls them source-processed LLP vertex records, not a
deduplicated reconstructed-vertex collection.

## Minimal ATLAS geometry evidence

The display metadata is intentionally small. Run-2 beam pipe `r=24.3 mm` is
from ATLAS `ATL-INDET-PROC-2015-001`; IBL/pixel radii 33.25, 50.5, 88.5, and
122.5 mm are from ATLAS `2106.09287`; the innermost SCT radius 299 mm and
`|z|<746 mm` support are from `ATL-PHYS-PUB-2019-013`. Exact URLs and scope
notes live beside every landmark in `public/data/detector_geometry.json`.
These hardware records are independent from the recast's 4/300 mm analysis
boundaries and from `vertexEff` radial bin edges.

## Cheap provenance checks

- Reference cutflow SHA-256:
  `572ef07b301234ae34bd1056290c418da8e1dd3a334ad7f1817ae9efb279d849`.
- Reference comparison SHA-256:
  `72f84ff8a65bfd581755d6812f4bdab8cfc2d096b236f6b0e810ce576f64908f`.
- Frozen upstream analysis source SHA-256:
  `e24bd377b6737f28537eb4d237488649d5e080212990627686d6b19c9c18adf2`.
- Local raw 500-event LHE SHA-256:
  `e9a82385345c22cb71606c339dc62a67b1fa9f9fdd5d22ae4ee5213f7a55e52a`.
- Width-repaired local LHE SHA-256:
  `0414bc36e980e082372ad3c8397961735eb876dab865f5abbea4b7398a5418ea`.
- The benchmark's portable checksum manifest verifies the cutflow,
  comparison, cards, and plots without rerunning physics.
