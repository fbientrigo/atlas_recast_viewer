import json
from pathlib import Path

import pytest

from preprocess.adapters.h2_mass_control import (
    ALL_MASSES,
    MISSING_JET_SENTINEL,
    TRACKLESS_THRESHOLDS_GEV,
    _canonical_jets,
    adapt,
    discover_masses,
    discover_s_grid,
    jet_selection_pass,
    load_mass,
)
from preprocess.validate_h2_dataset import validate_mass

ROOT = Path(__file__).parents[1]
ATLAS_DIHIGGS_ROOT = ROOT.parent


def test_discover_masses_matches_known_campaign() -> None:
    assert discover_masses(ATLAS_DIHIGGS_ROOT) == ALL_MASSES == [130, 150, 170, 200, 250, 300, 330, 345]


def test_discover_s_grid_is_ten_values_from_one_to_point_one() -> None:
    grid = discover_s_grid(ATLAS_DIHIGGS_ROOT)
    assert grid == [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]


def test_missing_jet_sentinel_maps_to_canonical_absence() -> None:
    event = {"jet_pt_GeV": {4: 60.0, 5: 40.0, 6: MISSING_JET_SENTINEL, 7: MISSING_JET_SENTINEL}}
    jets = _canonical_jets(event)
    ranks = {jet["rank"] for jet in jets}
    assert ranks == {4, 5}
    assert all(jet["pt_GeV"] != MISSING_JET_SENTINEL for jet in jets)
    # canonical absence never fabricates a direction either
    assert all(jet["eta"] is None and jet["phi"] is None for jet in jets)


def test_jet_selection_pass_uses_strict_greater_than_and_scales_only_ordinary_branches() -> None:
    just_at_threshold = {
        "jet_pt_GeV": {4: TRACKLESS_THRESHOLDS_GEV[4], 5: -1.0, 6: -1.0, 7: -1.0},
        "trackless_additional": True,
    }
    assert jet_selection_pass(just_at_threshold, 1.0) is False  # strict >, not >=
    just_above = {**just_at_threshold, "jet_pt_GeV": {4: TRACKLESS_THRESHOLDS_GEV[4] + 0.001, 5: -1.0, 6: -1.0, 7: -1.0}}
    assert jet_selection_pass(just_above, 1.0) is True

    # additional leg is required regardless of ordinary-branch pass
    hard_ordinary_pass_no_additional = {**just_above, "trackless_additional": False}
    assert jet_selection_pass(hard_ordinary_pass_no_additional, 1.0) is False

    # s scales only the ordinary thresholds: half the threshold at s=0.5 passes
    half_threshold_event = {
        "jet_pt_GeV": {4: TRACKLESS_THRESHOLDS_GEV[4] / 2 + 0.001, 5: -1.0, 6: -1.0, 7: -1.0},
        "trackless_additional": True,
    }
    assert jet_selection_pass(half_threshold_event, 1.0) is False
    assert jet_selection_pass(half_threshold_event, 0.5) is True


@pytest.mark.parametrize("mass", [130, 345])
def test_adapt_reproduces_campaign_cutflow_at_baseline(tmp_path: Path, mass: int) -> None:
    output_dir = tmp_path / f"h2-m{mass}"
    payload = adapt(
        atlas_dihiggs_root=ATLAS_DIHIGGS_ROOT,
        mass=mass,
        display_count=100,
        output_dir=output_dir,
        generator_command="pytest deterministic h2 adapter invocation",
        created_utc="2026-08-17T00:00:00+00:00",
    )
    assert payload["manifest"]["sample"]["mass_GeV"] == mass
    assert payload["manifest"]["sample"]["lifetime_mode"] == "fixed_response"
    assert payload["manifest"]["capabilities"]["dv_radial"] is False
    assert payload["manifest"]["capabilities"]["dv_xyz"] is False
    assert payload["manifest"]["capabilities"]["jet_observables"] is True
    assert len(payload["events"]["events"]) == 100
    for event in payload["events"]["events"]:
        assert event["vertices"] == []  # no geometry serialized, never fabricated

    report = validate_mass(ATLAS_DIHIGGS_ROOT, output_dir, mass)
    assert report["internal_adapter_validation"] == "PASSED"
    assert report["campaign_grid_validation"] == "PASSED"


def test_load_mass_returns_twenty_thousand_valid_events() -> None:
    events, csv_paths = load_mass(ATLAS_DIHIGGS_ROOT, 150)
    assert len(events) == 20000
    assert len(csv_paths) == 2


def test_missing_mass_raises() -> None:
    with pytest.raises(ValueError):
        load_mass(ATLAS_DIHIGGS_ROOT, 999)
