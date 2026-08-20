# H2 geometry replay contract

Establishes, with evidence, whether an individual event in an H2 mass-control
`events.csv` row can be exactly reproduced to recover geometry (DV x/y/z, jet
eta/phi, tracks) that was computed internally by the recast but never
serialized. See `docs/H2_SOURCE_INVENTORY.md` for the full field inventory.

## Provenance identifiers

| Item | Available? | Meaning | Can reproduce exact event? |
|---|---|---|---|
| Hard-process input (LHE) | AVAILABLE | Every mass's relabelled LHE file is preserved on disk: old masses (130,150,170,200,250) at `results/aeff_grid_20260811T042218Z/inputs/relabelled_full_mH{mass}_s10{1,7}.lhe.gz` (confirmed via `recast.log`'s `SusyLesHouches ... Parsing:` line, not the run's own `results/jet_threshold_response_.../cards/`); new masses (300,330,345) at `results/mass_control_jet_recovery_20260816T173704Z/inputs/relabelled_full_mH{mass}_s10{1,7}.lhe.gz`, sha256-verified in `reference/input_sha256.txt`. | Yes — exact source event record. |
| Pythia input (.cmnd card) | AVAILABLE | One frozen `.cmnd` per (mass, seed) under `results/{campaign}/cards/`, e.g. `mH150_ctau4p326_s81001.cmnd`. Declares `Beams:LHEF`, `Random:seed`, forced H2→bb decay, fixed `35:tau0`. | Yes. |
| Random seed | AVAILABLE | `Random:seed = 81001` / `81002` per seed directory, `Random:setSeed = on`. This seeds Pythia's own RNG (shower/hadronization/decay). | Yes, for the Pythia-owned stream. |
| Event ordering | AVAILABLE, sequential only | `recast_2301_13866.cc`'s event loop (`for (iEvent=0; iEvent<nEvent; iEvent++) pythia.next();`) reads LHE records strictly in file order; no shuffling, no random access. | Yes, but only by replaying from event 0 forward (Mode B — see below). |
| Event index → LHE record | AVAILABLE, derived | The `event` column in `events.csv` is `diagnosticEvent`, a counter incremented exactly once per loop iteration (both for `weight==0` and valid events; recast_2301_13866.cc:174,180). It therefore equals the 0-based LHE record index, i.e. the loop counter `iEvent`. | Yes. |
| Recast event id (canonical) | DERIVABLE | `H2Adapter._read_seed_events` sets `event_id = seed_offset*10000 + source_event_index`, `subrun = seed_index` (preprocess/adapters/h2_mass_control.py:206-230). Inverting gives `(seed_index, source_event_index)` directly. | Yes. |
| Campaign mass / ctau_response | AVAILABLE | `manifest.sample.mass_GeV`, `ctau_response_mm=4.326221529733112` fixed for all 8 masses (DECISION.md). | Yes. |
| Forced H2 decay mode | AVAILABLE | `.cmnd`: `35:onMode=off; 35:onIfMatch = 5 -5` (forced H2→bb̄). | Yes. |
| Second, private detector-smearing RNG stream | AVAILABLE, undocumented until now | `ToyDetector` (`Simpler_ToyDetector.h:56`) owns its own `Rndm rndm` member, **never explicitly seeded** (`rndm.init(...)` is never called anywhere in `recast_2301_13866.cc`). It is therefore a second, independent RNG stream (governing jet-energy and lepton smearing, `Simpler_ToyDetector.cc:117,208`) whose state evolves deterministically across `detector.getObjects()` calls in loop order, starting from Pythia8's fixed default `Rndm` seed. It is **not** controlled by the card's `Random:seed`. Reproducing this stream requires processing events 0..N of the *same run* in the *same order* — it cannot be reseeded independently per event. | Yes, under Mode B only. |

## Three replay modes — which is supported

**MODE B (deterministic stream replay) is the mode this source supports.**
MODE A (exact stored *shower-level* event, independent of stream position) is
not available: no HepMC/post-shower event record is stored, only the pre-shower
LHE input. Recovering a specific event's post-shower/smeared geometry
therefore requires re-running Pythia's shower RNG *and* `ToyDetector`'s private
RNG from the start of the same (mass, seed) run through the target event index,
consuming both streams exactly as the original run did, and serializing only
the selected indices. This is legal under Mode B ("process events 0...N
internally and only serialize selected indices" / "do not skip earlier events
in a way that changes the RNG sequence").

## Empirical proof (Gate 1)

The unmodified `recast_2301_13866.cc` (H2 campaign copy, with the R4/R5
configurable-LLP-identity change) was recompiled from source
(`dihiggs_llp_recast-jet-threshold-diag/results/jet_threshold_response_20260815T230503Z/src/`)
against the same Pythia 8.308 / FastJet 3.4.0 install used originally
(`~/.local/pythia8308`, `~/.local/fastjet-3.4.0`), and rerun unmodified against
the frozen `cards/mH150_ctau4p326_s81001.cmnd` (same LHE path, same seed
81001). The rebuilt `events.csv` was diffed against the frozen campaign
`events.csv`:

* 10000/10000 events reproduced, same order, same `event` index.
* Every boolean predicate (`pass_fiducial`, `pass_rvtx4`, `pass_d0`,
  `pass_ndecay5`, `pass_mdv10`, `trackless_additional`, `trackless_selected`,
  `highpt_selected`, ...), every jet rank pT (`jet4_pt`..`jet7_pt`), `sum_pt`,
  `v_eff`, `event_eff_trackless` — **exact match**, 10000/10000 rows.
* `r_max` (the one field computed via `std::sqrt(std::pow(x,2)+std::pow(y,2))`
  and printed at `setprecision(17)`) differed in the 16th significant digit on
  3/10000 rows (e.g. `3.2284730517434856` vs `3.2284730517434852`, relative
  difference ≈ 1.2e-16) — floating-point-associativity noise from a differing
  toolchain minor version, not an RNG or physics divergence: every predicate
  and every other continuous quantity derived from the same computation chain
  was unaffected.

**Verdict: Mode B replay is proven, with a documented floating-point tolerance
of 1e-12 relative on continuous doubles and exact equality on every boolean
predicate, count, and jet pT.** This tolerance is used by
`preprocess/validate_h2_geometry_replay.py`'s regression gate (Section 19 of
the gauntlet).

## Consequence for telemetry instrumentation

Any telemetry-only H2 recast variant must, like the existing
`preprocess/instrumentation/recast_2301_13866_telemetry.cc` (used for
`local-reference`), be a straight-line copy of the frozen `recast_2301_13866.cc`
control flow with **zero added `rndm.gauss()` / `pythia.rndm.flat()` calls and
zero added `detector.getObjects()` calls** — telemetry may only serialize
values already computed by the existing control flow, gated by an `if (event
index is selected)` check that itself consumes no randomness. This preserves
both RNG streams' state identically to the frozen run.
