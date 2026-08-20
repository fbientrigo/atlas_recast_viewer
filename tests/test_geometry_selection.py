import json
from pathlib import Path

from preprocess.geometry_selection import (
    COHORT_QUOTAS,
    first_failed_cut,
    select_top100,
    x_max,
)

ROOT = Path(__file__).parents[1]
ATLAS_DIHIGGS_ROOT = ROOT.parent


def test_selection_is_deterministic_across_runs() -> None:
    first = select_top100(ATLAS_DIHIGGS_ROOT, 150)
    second = select_top100(ATLAS_DIHIGGS_ROOT, 150)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_selects_exactly_100_with_no_duplicates() -> None:
    result = select_top100(ATLAS_DIHIGGS_ROOT, 150)
    assert result["selected_total"] == 100
    ids = [event["event_id"] for event in result["events"]]
    assert len(set(ids)) == 100
    assert sum(result["cohort_selected"].values()) == 100


def test_cohort_totals_match_requested_quotas_shape() -> None:
    result = select_top100(ATLAS_DIHIGGS_ROOT, 150)
    assert set(result["cohort_selected"]) == set(COHORT_QUOTAS)


def test_accepted_baseline_events_pass_every_sequential_cut() -> None:
    result = select_top100(ATLAS_DIHIGGS_ROOT, 150)
    baseline_ids = {e["event_id"] for e in result["events"] if e["cohort"] == "accepted_baseline"}
    for event in result["events"]:
        if event["event_id"] in baseline_ids:
            assert event["first_failed_cut"] is None


def test_fail_jet_selection_cohort_events_first_fail_at_jet_selection() -> None:
    result = select_top100(ATLAS_DIHIGGS_ROOT, 150)
    for event in result["events"]:
        if event["cohort"] == "fail_jet_selection_s1":
            assert event["first_failed_cut"] == "jet_selection"


def test_jet_borderline_events_have_a_real_jet() -> None:
    result = select_top100(ATLAS_DIHIGGS_ROOT, 150)
    for event in result["events"]:
        if event["cohort"] == "jet_borderline_s1":
            assert event["x_max"] is not None


def test_deficit_never_fabricates_category_membership() -> None:
    # mass 150 has almost no first-fail-at-Ntracks events; the deficit must be
    # absorbed by an honestly-labeled adjacent cohort, not invented.
    result = select_top100(ATLAS_DIHIGGS_ROOT, 150)
    assert result["cohort_deficit_unresolved"] == {}
    for event in result["events"]:
        if event["cohort"] == "first_fail_r_dv":
            assert event["first_failed_cut"] == "rxy_gt_4_mm"


def test_x_max_excludes_missing_jet_sentinel() -> None:
    event = {"jet_pt_GeV": {4: -1.0, 5: -1.0, 6: -1.0, 7: -1.0}}
    assert x_max(event) is None
