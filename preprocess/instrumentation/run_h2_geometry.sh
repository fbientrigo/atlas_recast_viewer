#!/usr/bin/env bash
# Build the H2 telemetry-only recast and replay it for one mass's frozen
# top-100 selection, producing public/data/h2-m{mass}/geometry_events.json.
set -euo pipefail

MASS="${1:?usage: run_h2_geometry.sh MASS}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ATLAS_DIHIGGS_ROOT="${ATLAS_DIHIGGS_ROOT:-$ROOT/..}"
PYTHIA_PREFIX="${PYTHIA_PREFIX:-/home/fabian/.local/pythia8308}"
FASTJET_PREFIX="${FASTJET_PREFIX:-/home/fabian/.local/fastjet-3.4.0}"
CAMPAIGN_SRC="$ATLAS_DIHIGGS_ROOT/dihiggs_llp_recast-jet-threshold-diag/results/jet_threshold_response_20260815T230503Z/src"

SELECTION="$ROOT/validation/h2_geometry_selection/m${MASS}.json"
BUILD="$ROOT/validation/h2_geometry_telemetry/build"
RUN="$ROOT/validation/h2_geometry_telemetry/m${MASS}"
DATASET_DIR="$ROOT/public/data/h2-m${MASS}"
REPORT="$ROOT/validation/h2_geometry_replay_m${MASS}.json"

[[ -f "$SELECTION" ]] || { echo "missing $SELECTION — run preprocess.geometry_selection first" >&2; exit 1; }

mkdir -p "$BUILD" "$RUN"

g++ -std=c++11 -O2 \
  -I"$PYTHIA_PREFIX/include" -I"$FASTJET_PREFIX/include" -I"$CAMPAIGN_SRC" \
  "$CAMPAIGN_SRC/Simpler_ToyDetector.cc" "$CAMPAIGN_SRC/efficiency.cc" \
  "$ROOT/preprocess/instrumentation/h2_recast_2301_13866_telemetry.cc" \
  -L"$PYTHIA_PREFIX/lib" -Wl,-rpath,"$PYTHIA_PREFIX/lib" -lpythia8 \
  -L"$FASTJET_PREFIX/lib" -Wl,-rpath,"$FASTJET_PREFIX/lib" -lfastjet -lz \
  -o "$BUILD/h2_telemetry"

.venv/bin/python - "$SELECTION" "$RUN" <<'PYEOF'
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from preprocess.geometry_replay import write_index_files
selection = json.loads(Path(sys.argv[1]).read_text())
paths = write_index_files(selection, Path(sys.argv[2]))
print("index files:", {k: str(v) for k, v in paths.items()})
PYEOF

TELEMETRY_ARGS=()
for INDEX_FILE in "$RUN"/selected_subrun*.txt; do
  SUBRUN="$(basename "$INDEX_FILE" | sed -E 's/selected_subrun([0-9]+)\.txt/\1/')"
  CMND="$(.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from pathlib import Path
from preprocess.geometry_replay import seed_cmnd_paths
print(seed_cmnd_paths(Path('$ATLAS_DIHIGGS_ROOT'), $MASS)[$SUBRUN])
")"
  echo "=== mass=$MASS subrun=$SUBRUN card=$CMND ==="
  "$BUILD/h2_telemetry" "$CMND" "$RUN/telemetry_subrun${SUBRUN}.ndjson" "$INDEX_FILE" "$SUBRUN" > "$RUN/telemetry_subrun${SUBRUN}.log" 2>&1
  TELEMETRY_ARGS+=("--telemetry" "${SUBRUN}:$RUN/telemetry_subrun${SUBRUN}.ndjson")
done

.venv/bin/python -m preprocess.geometry_replay \
  --atlas-dihiggs-root "$ATLAS_DIHIGGS_ROOT" \
  --mass "$MASS" \
  --selection-path "$SELECTION" \
  "${TELEMETRY_ARGS[@]}" \
  --dataset-dir "$DATASET_DIR" \
  --report "$REPORT"
