"""Regenerating an H2 statistics dataset must not drop an already-replayed
geometry pack, and must never fabricate or silently accept a broken one.
See preprocess/adapters/h2_mass_control.py::_recover_geometry_pack.
"""

import json
import shutil
from pathlib import Path

from preprocess.adapters.h2_mass_control import adapt

ROOT = Path(__file__).parents[1]
ATLAS_DIHIGGS_ROOT = ROOT.parent
REAL_H2_M150 = ROOT / "public" / "data" / "h2-m150"


def _adapt(output_dir: Path) -> dict:
    return adapt(
        atlas_dihiggs_root=ATLAS_DIHIGGS_ROOT,
        mass=150,
        display_count=100,
        output_dir=output_dir,
        generator_command="pytest geometry-pack-preservation",
        created_utc="2026-08-17T00:00:00+00:00",
    )


def test_regenerating_the_dataset_preserves_a_valid_geometry_pack(tmp_path: Path) -> None:
    output_dir = tmp_path / "h2-m150"
    output_dir.mkdir()
    shutil.copy(REAL_H2_M150 / "manifest.json", output_dir / "manifest.json")
    shutil.copy(REAL_H2_M150 / "geometry_events.json", output_dir / "geometry_events.json")
    original_pack = json.loads((output_dir / "manifest.json").read_text())["geometry_pack"]

    payload = _adapt(output_dir)

    assert payload["manifest"]["geometry_pack"] == original_pack
    on_disk = json.loads((output_dir / "manifest.json").read_text())
    assert on_disk["geometry_pack"] == original_pack


def test_regeneration_is_idempotent_across_two_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "h2-m150"
    output_dir.mkdir()
    shutil.copy(REAL_H2_M150 / "manifest.json", output_dir / "manifest.json")
    shutil.copy(REAL_H2_M150 / "geometry_events.json", output_dir / "geometry_events.json")

    first = _adapt(output_dir)
    second = _adapt(output_dir)

    assert first["manifest"]["geometry_pack"] == second["manifest"]["geometry_pack"]


def test_missing_geometry_pack_stays_absent(tmp_path: Path) -> None:
    output_dir = tmp_path / "h2-m150"
    # no pre-existing manifest.json or geometry_events.json at all
    payload = _adapt(output_dir)
    assert "geometry_pack" not in payload["manifest"]


def test_geometry_events_present_but_no_prior_manifest_link_stays_absent(tmp_path: Path) -> None:
    output_dir = tmp_path / "h2-m150"
    output_dir.mkdir()
    shutil.copy(REAL_H2_M150 / "geometry_events.json", output_dir / "geometry_events.json")
    payload = _adapt(output_dir)
    assert "geometry_pack" not in payload["manifest"]


def test_invalid_geometry_events_is_not_silently_reattached(tmp_path: Path) -> None:
    output_dir = tmp_path / "h2-m150"
    output_dir.mkdir()
    shutil.copy(REAL_H2_M150 / "manifest.json", output_dir / "manifest.json")
    broken = json.loads((REAL_H2_M150 / "geometry_events.json").read_text())
    broken["events"] = broken["events"][:5]  # event_count now disagrees with manifest.geometry_pack.event_count
    (output_dir / "geometry_events.json").write_text(json.dumps(broken), encoding="utf-8")

    payload = _adapt(output_dir)

    assert "geometry_pack" not in payload["manifest"]


def test_dataset_id_mismatch_is_not_silently_reattached(tmp_path: Path) -> None:
    output_dir = tmp_path / "h2-m150"
    output_dir.mkdir()
    shutil.copy(REAL_H2_M150 / "manifest.json", output_dir / "manifest.json")
    broken = json.loads((REAL_H2_M150 / "geometry_events.json").read_text())
    broken["dataset_id"] = "h2-m999"
    (output_dir / "geometry_events.json").write_text(json.dumps(broken), encoding="utf-8")

    payload = _adapt(output_dir)

    assert "geometry_pack" not in payload["manifest"]
