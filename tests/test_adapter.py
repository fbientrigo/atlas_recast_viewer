import json
from pathlib import Path

from preprocess.adapters.original_recast import EXPECTED_SOURCE_STAGE_IDS, adapt
from preprocess.validate_dataset import validate_against_source

ROOT = Path(__file__).parents[1]
WORKSPACE = ROOT.parent
RELEASE = WORKSPACE / "dihiggs_llp_recast-release-v1"
SOURCE_CUTFLOW = RELEASE / "results" / "upstream" / "strong-bm1" / "cutflow.json"


def test_adapter_exactly_serializes_source_cutflow(tmp_path: Path) -> None:
    payload = adapt(
        source_cutflow=SOURCE_CUTFLOW,
        source_benchmark_manifest=(
            RELEASE / "benchmarks" / "upstream" / "strong-bm1" / "manifest.json"
        ),
        source_benchmark=(
            RELEASE / "benchmarks" / "upstream" / "strong-bm1" / "benchmark.json"
        ),
        source_checkout=RELEASE / "external" / "recastingCodes",
        output_dir=tmp_path,
        generator_command="pytest deterministic adapter invocation",
        created_utc="2026-08-17T00:00:00+00:00",
    )
    source = json.loads(SOURCE_CUTFLOW.read_text(encoding="utf-8"))
    assert tuple(cut["id"] for cut in payload["cuts"]["cuts"]) == EXPECTED_SOURCE_STAGE_IDS
    assert [stage["n_after"] for stage in payload["summary"]["cutflow"]["stages"]] == [
        stage["our_weighted_events"] for stage in source["stages"]
    ]
    assert all(cut["mathematical_latex"] for cut in payload["cuts"]["cuts"])
    overlays = {
        cut["id"]: cut.get("geometry_overlay") for cut in payload["cuts"]["cuts"]
    }
    assert overlays["fiducial_dv"] == {
        "view": "r_z",
        "r_min_mm": None,
        "r_max_mm": 300.0,
        "abs_z_max_mm": 300.0,
    }
    assert overlays["rxy_gt_4_mm"]["r_min_mm"] == 4.0
    report = validate_against_source(tmp_path, SOURCE_CUTFLOW)
    assert report["internal_adapter_validation"] == "PASSED"


def test_reference_capabilities_follow_aggregate_evidence() -> None:
    manifest = json.loads(
        (ROOT / "public" / "data" / "reference" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["capabilities"] == {
        "cutflow": True,
        "atomic_event_cuts": False,
        "jet_observables": False,
        "jet_what_if": False,
        "dv_radial": False,
        "dv_xyz": False,
        "response_weights": False,
    }
    assert not (ROOT / "public" / "data" / "reference" / "events.json").exists()
