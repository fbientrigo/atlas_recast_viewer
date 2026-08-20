import copy
import json
from pathlib import Path

import pytest

from preprocess.schema import DatasetValidationError, validate_dataset, validate_events

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "public" / "data" / "reference"
H2_DATASET = ROOT / "public" / "data" / "h2-m150"


def load_dataset() -> tuple[dict, dict, dict]:
    return tuple(  # type: ignore[return-value]
        json.loads((DATASET / name).read_text(encoding="utf-8"))
        for name in ("manifest.json", "cuts.json", "summary.json")
    )


def load_h2_dataset() -> tuple[dict, dict, dict, dict]:
    return tuple(  # type: ignore[return-value]
        json.loads((H2_DATASET / name).read_text(encoding="utf-8"))
        for name in ("manifest.json", "cuts.json", "summary.json", "events.json")
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


def test_h2_event_pack_validates_with_no_geometry_capability() -> None:
    manifest, cuts, summary, events = load_h2_dataset()
    validate_dataset(manifest, cuts, summary)
    validate_events(events, manifest, cuts)
    assert manifest["capabilities"]["dv_radial"] is False
    assert manifest["capabilities"]["dv_xyz"] is False
    assert manifest["capabilities"]["jet_observables"] is True
    assert all(event["vertices"] == [] for event in events["events"])


def test_h2_jet_direction_is_nullable() -> None:
    manifest, cuts, summary, events = load_h2_dataset()
    assert any(jet["eta"] is None for event in events["events"] for jet in event["jets"])
    validate_events(events, manifest, cuts)  # must not raise despite null eta/phi


def test_nonempty_vertices_rejected_without_geometry_capability() -> None:
    manifest, cuts, summary, events = load_h2_dataset()
    events = copy.deepcopy(events)
    events["events"][0]["vertices"] = [{"x_mm": 1.0}]
    with pytest.raises(DatasetValidationError, match="vertices"):
        validate_events(events, manifest, cuts)


def test_event_scoped_predicate_missing_is_rejected() -> None:
    manifest, cuts, summary, events = load_h2_dataset()
    events = copy.deepcopy(events)
    del events["events"][0]["predicates"]["fiducial_dv"]
    with pytest.raises(DatasetValidationError, match="predicates.fiducial_dv"):
        validate_events(events, manifest, cuts)


def test_jet_finite_eta_or_phi_still_rejects_nan() -> None:
    manifest, cuts, summary, events = load_h2_dataset()
    events = copy.deepcopy(events)
    target = next(event for event in events["events"] if event["jets"])
    target["jets"][0]["eta"] = float("nan")
    with pytest.raises(DatasetValidationError, match=r"jets\[0\]\.eta"):
        validate_events(events, manifest, cuts)
