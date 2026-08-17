from preprocess.selection import (
    displaced_addendum_pass,
    high_pt_ordinary_pass,
    trackless_ordinary_pass,
    trackless_region_pass,
)


def test_ranked_jet_logic_is_or_not_and() -> None:
    # Only j5 passes; the overall ordinary selection must still pass.
    assert high_pt_ordinary_pass([500.0, 400.0, 300.0, 200.0, 196.0])
    assert not high_pt_ordinary_pass([500.0, 400.0, 300.0, 250.0])  # strict >


def test_missing_jet_rank_is_false_not_zero_or_pass() -> None:
    assert not trackless_ordinary_pass([300.0, 200.0, 150.0])
    assert not trackless_ordinary_pass([300.0, 200.0, 150.0, None])
    assert trackless_ordinary_pass([300.0, 200.0, 150.0, 138.0])


def test_trackless_ordinary_and_displaced_compound_logic() -> None:
    ordinary_pass = [300.0, 200.0, 150.0, 138.0]
    assert not trackless_region_pass(ordinary_pass, [70.0])  # strict >
    assert trackless_region_pass(ordinary_pass, [70.1])
    assert displaced_addendum_pass([40.0, 50.1])
    assert not trackless_region_pass([300.0, 200.0, 150.0, 137.0], [100.0])

