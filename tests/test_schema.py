import copy
import json
from pathlib import Path

import pytest

from preprocess.schema import DatasetValidationError, validate_dataset

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "public" / "data" / "reference"


def load_dataset() -> tuple[dict, dict, dict]:
    return tuple(  # type: ignore[return-value]
        json.loads((DATASET / name).read_text(encoding="utf-8"))
        for name in ("manifest.json", "cuts.json", "summary.json")
    )


def test_reference_dataset_validates() -> None:
    validate_dataset(*load_dataset())


def test_incompatible_schema_fails_with_field_context() -> None:
    manifest, cuts, summary = load_dataset()
    manifest["schema_version"] = "viewer.dataset.v999"
    with pytest.raises(DatasetValidationError, match="field=schema_version"):
        validate_dataset(manifest, cuts, summary)


def test_stage_order_mismatch_fails() -> None:
    manifest, cuts, summary = load_dataset()
    summary["cutflow"]["stages"][0], summary["cutflow"]["stages"][1] = (
        summary["cutflow"]["stages"][1],
        summary["cutflow"]["stages"][0],
    )
    with pytest.raises(DatasetValidationError, match="cutflow.stages.*cut_id"):
        validate_dataset(manifest, cuts, summary)


def test_jet_what_if_requires_atomic_predicates_and_observables() -> None:
    manifest, cuts, summary = load_dataset()
    manifest = copy.deepcopy(manifest)
    manifest["capabilities"]["jet_what_if"] = True
    with pytest.raises(DatasetValidationError, match="capabilities.jet_what_if"):
        validate_dataset(manifest, cuts, summary)


def test_null_reference_value_is_preserved() -> None:
    manifest, cuts, summary = load_dataset()
    assert summary["cutflow"]["stages"][0]["reference"]["atlas_parametric_pct"] is None
    validate_dataset(manifest, cuts, summary)


def test_negative_geometry_boundary_is_rejected() -> None:
    manifest, cuts, summary = load_dataset()
    cuts = copy.deepcopy(cuts)
    cuts["cuts"][1]["geometry_overlay"]["r_max_mm"] = -300
    with pytest.raises(DatasetValidationError, match="geometry_overlay.r_max_mm"):
        validate_dataset(manifest, cuts, summary)
