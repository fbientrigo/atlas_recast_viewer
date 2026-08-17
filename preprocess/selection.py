"""Small, source-proven selection helpers used only for validation tests."""

from __future__ import annotations

from collections.abc import Sequence

HIGH_PT_THRESHOLDS_GEV = (250.0, 195.0, 116.0, 90.0)
TRACKLESS_THRESHOLDS_GEV = (137.0, 101.0, 83.0, 55.0)
DISPLACED_THRESHOLDS_GEV = (70.0, 50.0)


def ranked_jet_or(jet_pt_gev: Sequence[float | None], thresholds: Sequence[float]) -> bool:
    """Match the C++ rank-existence guards and strict `>` comparisons."""

    return any(
        len(jet_pt_gev) > rank
        and jet_pt_gev[rank] is not None
        and jet_pt_gev[rank] > threshold
        for rank, threshold in zip(range(3, 3 + len(thresholds)), thresholds, strict=True)
    )


def high_pt_ordinary_pass(jet_pt_gev: Sequence[float | None]) -> bool:
    return ranked_jet_or(jet_pt_gev, HIGH_PT_THRESHOLDS_GEV)


def trackless_ordinary_pass(jet_pt_gev: Sequence[float | None]) -> bool:
    return ranked_jet_or(jet_pt_gev, TRACKLESS_THRESHOLDS_GEV)


def displaced_addendum_pass(displaced_jet_pt_gev: Sequence[float | None]) -> bool:
    leading = len(displaced_jet_pt_gev) >= 1 and displaced_jet_pt_gev[0] is not None
    subleading = len(displaced_jet_pt_gev) >= 2 and displaced_jet_pt_gev[1] is not None
    return bool(
        (leading and displaced_jet_pt_gev[0] > DISPLACED_THRESHOLDS_GEV[0])
        or (subleading and displaced_jet_pt_gev[1] > DISPLACED_THRESHOLDS_GEV[1])
    )


def trackless_region_pass(
    jet_pt_gev: Sequence[float | None], displaced_jet_pt_gev: Sequence[float | None]
) -> bool:
    return trackless_ordinary_pass(jet_pt_gev) and displaced_addendum_pass(displaced_jet_pt_gev)

