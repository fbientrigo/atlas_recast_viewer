import json
from pathlib import Path

from preprocess.generate_catalog import regenerate


def _write_manifest(data_dir: Path, dataset_id: str, mass: int) -> None:
    dataset_dir = data_dir / dataset_id
    dataset_dir.mkdir(parents=True)
    manifest = {"dataset_id": dataset_id, "sample": {"mass_GeV": mass, "ctau_response_mm": 4.326221529733112}}
    (dataset_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_regenerate_preserves_existing_entries_and_sorts_h2_numerically(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "catalog.json").write_text(
        json.dumps(
            [
                {"dataset_id": "reference", "labels": {"es": "R", "en": "R"}, "description": {"es": "d", "en": "d"}},
                {"dataset_id": "local-reference", "labels": {"es": "L", "en": "L"}, "description": {"es": "d", "en": "d"}},
            ]
        ),
        encoding="utf-8",
    )
    _write_manifest(data_dir, "h2-m345", 345)
    _write_manifest(data_dir, "h2-m130", 130)
    _write_manifest(data_dir, "h2-m200", 200)

    catalog = regenerate(data_dir)

    assert [entry["dataset_id"] for entry in catalog] == [
        "reference", "local-reference", "h2-m130", "h2-m200", "h2-m345",
    ]
    reloaded = json.loads((data_dir / "catalog.json").read_text(encoding="utf-8"))
    assert reloaded == catalog


def test_regenerate_ignores_datasets_missing_a_manifest(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "catalog.json").write_text("[]", encoding="utf-8")
    (data_dir / "h2-m999").mkdir()  # no manifest.json inside

    catalog = regenerate(data_dir)

    assert catalog == []


def test_regenerate_is_idempotent(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "catalog.json").write_text("[]", encoding="utf-8")
    _write_manifest(data_dir, "h2-m150", 150)

    first = regenerate(data_dir)
    second = regenerate(data_dir)

    assert first == second
