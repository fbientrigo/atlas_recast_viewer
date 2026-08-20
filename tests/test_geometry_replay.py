import json
from pathlib import Path

import pytest

from preprocess.geometry_replay import (
    _recompute_mdv,
    build_and_validate,
    seed_cmnd_paths,
    seed_events_csv_paths,
    selected_indices_by_subrun,
    write_index_files,
)

ROOT = Path(__file__).parents[1]
ATLAS_DIHIGGS_ROOT = ROOT.parent
TELEMETRY_DIR = ROOT / "validation" / "h2_geometry_telemetry" / "m150"


def test_selected_indices_grouped_by_subrun() -> None:
    selection = {"events": [
        {"subrun": 0, "source_event_index": 5},
        {"subrun": 1, "source_event_index": 7},
        {"subrun": 0, "source_event_index": 1},
    ]}
    grouped = selected_indices_by_subrun(selection)
    assert grouped == {0: [5, 1], 1: [7]}


def test_write_index_files_are_sorted(tmp_path: Path) -> None:
    selection = {"events": [{"subrun": 0, "source_event_index": 9}, {"subrun": 0, "source_event_index": 2}]}
    paths = write_index_files(selection, tmp_path)
    assert paths[0].read_text() == "2\n9\n"


def test_seed_cmnd_paths_resolve_for_mass_150() -> None:
    paths = seed_cmnd_paths(ATLAS_DIHIGGS_ROOT, 150)
    assert set(paths) == {0, 1}
    for path in paths.values():
        assert path.exists()
        assert path.name.startswith("mH150_ctau4p326_s")


def test_seed_events_csv_paths_exist_for_mass_150() -> None:
    paths = seed_events_csv_paths(ATLAS_DIHIGGS_ROOT, 150)
    assert set(paths) == {0, 1}
    for path in paths.values():
        assert path.exists()


def test_recompute_mdv_matches_zero_for_no_selected_tracks() -> None:
    vertex = {"tracks": [{"selected_for_dv": False, "px_GeV": 1, "py_GeV": 1, "pz_GeV": 1}]}
    assert _recompute_mdv(vertex) == 0.0


@pytest.mark.skipif(not TELEMETRY_DIR.exists(), reason="requires a prior run of run_h2_geometry.sh 150")
def test_build_and_validate_reuses_frozen_telemetry_for_mass_150(tmp_path: Path) -> None:
    selection_path = ROOT / "validation" / "h2_geometry_selection" / "m150.json"
    dataset_dir = tmp_path / "h2-m150"
    dataset_dir.mkdir()
    for name in ("manifest.json", "cuts.json", "summary.json"):
        (dataset_dir / name).write_text((ROOT / "public" / "data" / "h2-m150" / name).read_text(), encoding="utf-8")
    manifest = json.loads((dataset_dir / "manifest.json").read_text())
    manifest.pop("geometry_pack", None)
    (dataset_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = build_and_validate(
        ATLAS_DIHIGGS_ROOT,
        150,
        selection_path,
        {0: TELEMETRY_DIR / "telemetry_subrun0.ndjson", 1: TELEMETRY_DIR / "telemetry_subrun1.ndjson"},
        dataset_dir,
    )
    assert report["failures"] == []
    assert report["identity_matches"] == report["selected"] == 100
    written = json.loads((dataset_dir / "geometry_events.json").read_text())
    assert len(written["events"]) == 100
