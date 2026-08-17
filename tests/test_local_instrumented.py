import copy
import gzip
import json
from pathlib import Path

import pytest

from preprocess.adapters.local_instrumented_reference import BOOLEAN_CUT_IDS, _event_passes
from preprocess.schema import DatasetValidationError, validate_dataset, validate_events
from preprocess.validate_local_instrumentation import validate_local
from preprocess.instrumentation.fix_lhe_neutralino_width import NEW, OLD, fix_width

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "public" / "data" / "local-reference"


def load_local() -> tuple[dict, dict, dict, dict]:
    return tuple(  # type: ignore[return-value]
        json.loads((DATASET / name).read_text(encoding="utf-8"))
        for name in ("manifest.json", "cuts.json", "summary.json", "events.json")
    )


def test_local_event_pack_and_instrumentation_validate() -> None:
    manifest, cuts, summary, events = load_local()
    validate_dataset(manifest, cuts, summary)
    validate_events(events, manifest, cuts)
    report = validate_local(
        DATASET,
        ROOT / "validation" / "local_reference" / "upstream.log",
        ROOT / "validation" / "local_reference" / "instrumented.log",
    )
    assert report["instrumentation_regression"] == "PASSED"
    assert len(events["events"]) == 500
    assert sum(_event_passes(event, BOOLEAN_CUT_IDS) for event in events["events"]) == 157


def test_event_geometry_cannot_disagree_with_radius() -> None:
    manifest, cuts, summary, events = load_local()
    malformed = copy.deepcopy(events)
    malformed["events"][0]["vertices"][0]["r_mm"] += 1
    with pytest.raises(DatasetValidationError, match="hypot"):
        validate_events(malformed, manifest, cuts)


def test_track_d0_cannot_disagree_with_recast_proxy() -> None:
    manifest, cuts, summary, events = load_local()
    malformed = copy.deepcopy(events)
    malformed["events"][0]["vertices"][0]["tracks"][0]["d0_mm"] += 0.1
    with pytest.raises(DatasetValidationError, match="recast-proxy"):
        validate_events(malformed, manifest, cuts)


def test_track_production_z_is_required_and_finite() -> None:
    manifest, cuts, summary, events = load_local()
    malformed = copy.deepcopy(events)
    del malformed["events"][0]["vertices"][0]["tracks"][0]["z_prod_mm"]
    with pytest.raises(DatasetValidationError, match="z_prod_mm"):
        validate_events(malformed, manifest, cuts)


def test_width_repair_changes_exactly_one_checked_header(tmp_path: Path) -> None:
    source = tmp_path / "raw.lhe.gz"
    output = tmp_path / "fixed.lhe.gz"
    original = f"<header>\n{OLD}\n  1.0 3 2 1 3\n</header>\n"
    with gzip.open(source, "wt", encoding="utf-8") as stream:
        stream.write(original)
    fix_width(source, output)
    with gzip.open(output, "rt", encoding="utf-8") as stream:
        repaired = stream.read()
    assert repaired == original.replace(OLD, NEW)
