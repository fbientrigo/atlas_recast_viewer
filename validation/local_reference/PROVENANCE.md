# Local instrumented reference provenance

Scope: 500-event reconstructed strong-bm1 0-parton teaching sample. This is
not the authors' private input and not the inclusive 0j+1j+2j benchmark.

## Generation

- MG5_aMC 3.5.3, local executable
  `/home/fabian/.local/mg5amcnlo/3.5.3/bin/mg5_aMC`.
- Frozen process/run cards and reconstructed 2000/850 GeV SLHA from
  `../dihiggs_llp_recast-release-v1/benchmarks/upstream/strong-bm1/`.
- Command:

  ```bash
  MG5_BIN=/home/fabian/.local/mg5amcnlo/3.5.3/bin/mg5_aMC \
    bash scripts/run_strong_bm1_mg5.sh \
    0 500 424201 local_viewer_500 /tmp/recast_viewer_strong0j
  ```

- Generated 0j cross section: `0.0004874580020380087 pb ±
  3.63429539806549e-06 pb` (MG integration output).
- Raw LHE SHA-256:
  `e9a82385345c22cb71606c339dc62a67b1fa9f9fdd5d22ae4ee5213f7a55e52a`.
- MG5 labels this checkout an unknown development version and warns that
  Python 3.12 support is experimental. This sample is therefore pedagogical,
  not a precision production campaign.

MG5 retained the four intended RPV channels but serialized the tiny neutralino
width as zero. `preprocess/instrumentation/fix_lhe_neutralino_width.py` requires
exactly one matching header and changes it to `6.582120e-14 GeV` (0.01 ns).
The deterministic repaired LHE SHA-256 is
`0414bc36e980e082372ad3c8397961735eb876dab865f5abbea4b7398a5418ea`.

## Recast and instrumentation

- Frozen upstream base: `llprecasting/recastingCodes` commit
  `d4047c744062094c9f88e507bb1ccf69e9fe88d6`, clean detached checkout.
- Pythia 8.308; FastJet 3.4.0; Pythia seed 424202.
- `run_local_reference.sh` compiles the untouched source and the telemetry
  copy independently, then runs both on `input/local_0j.cmnd`.
- The only intentional control-flow change is hoisting the early jet-failure
  `continue` so vertex atomic predicates can be observed for counterfactuals.
  All original accumulators retain their gates; efficiency lookups use no RNG.
- Telemetry additionally records LLP momentum and charged final daughters
  already traversed by the source loop: production x/y/z, momentum, the exact
  `d0` proxy, and the two source selection flags. No reconstructed quantities
  or detector response are invented.

Validation result: nominal stdout is identical after normalizing only the
Pythia wall-clock line. Telemetry reproduces 99.8% High-pT jet acceptance,
31.4% boolean DV acceptance, and 27.25118% final A×efficiency exactly at the
source print precision. See `../local_instrumentation_validation.json`.
The report also records zero `d0` reconstruction mismatches and zero
per-track/vertex-count mismatches.
