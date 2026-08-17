#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RELEASE="${RELEASE:-$ROOT/../dihiggs_llp_recast-release-v1}"
PYTHIA_PREFIX="${PYTHIA_PREFIX:-/home/fabian/.local/pythia8308}"
FASTJET_PREFIX="${FASTJET_PREFIX:-/home/fabian/.local/fastjet-3.4.0}"
ANALYSIS="$RELEASE/external/recastingCodes/DisplacedVertices/ATLAS-SUSY-2018-13_GCottin/recast_code/1_analysis"
RUN="$ROOT/validation/local_reference"
INPUT="$RUN/input"
BUILD="$RUN/build"
EXPECTED_COMMIT="d4047c744062094c9f88e507bb1ccf69e9fe88d6"

[[ "$(git -C "$RELEASE/external/recastingCodes" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]]
[[ -z "$(git -C "$RELEASE/external/recastingCodes" status --porcelain)" ]]
mkdir -p "$BUILD"

COMMON=(
  -std=c++11 -O2
  "-I$PYTHIA_PREFIX/include" "-I$FASTJET_PREFIX/include" "-I$ANALYSIS"
  "$ANALYSIS/Simpler_ToyDetector.cc" "$ANALYSIS/efficiency.cc"
  "-L$PYTHIA_PREFIX/lib" "-Wl,-rpath,$PYTHIA_PREFIX/lib" -lpythia8
  "-L$FASTJET_PREFIX/lib" "-Wl,-rpath,$FASTJET_PREFIX/lib" -lfastjet -lz
)
g++ "${COMMON[@]:0:6}" "$ANALYSIS/recast_2301_13866.cc" "${COMMON[@]:6}" -o "$BUILD/recast_upstream"
g++ "${COMMON[@]:0:6}" "$ROOT/preprocess/instrumentation/recast_2301_13866_telemetry.cc" "${COMMON[@]:6}" -o "$BUILD/recast_telemetry"

(
  cd "$INPUT"
  ../build/recast_upstream local_0j.cmnd > ../upstream.log 2>&1
  ../build/recast_telemetry local_0j.cmnd ../events.ndjson > ../instrumented.log 2>&1
)

cd "$ROOT"
.venv/bin/python -m preprocess.adapters.local_instrumented_reference \
  --telemetry validation/local_reference/events.ndjson \
  --upstream-log validation/local_reference/upstream.log \
  --instrumented-log validation/local_reference/instrumented.log \
  --input-lhe validation/local_reference/input/strong_bm1_reconstructed_0j_500_width_fixed.lhe.gz \
  --run-card validation/local_reference/input/local_0j.cmnd \
  --instrumented-source preprocess/instrumentation/recast_2301_13866_telemetry.cc \
  --output-dir public/data/local-reference
.venv/bin/python -m preprocess.validate_local_instrumentation \
  --dataset-dir public/data/local-reference \
  --upstream-log validation/local_reference/upstream.log \
  --instrumented-log validation/local_reference/instrumented.log \
  --report validation/local_instrumentation_validation.json
