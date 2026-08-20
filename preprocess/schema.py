"""Strict dependency-free validation for the deliberately small v1 contract."""

from __future__ import annotations

from typing import Any
import math

from preprocess import SCHEMA_VERSION

REQUIRED_CAPABILITIES = {
    "cutflow",
    "atomic_event_cuts",
    "jet_observables",
    "jet_what_if",
    "dv_radial",
    "dv_xyz",
    "response_weights",
}
CUT_KINDS = {"atomic_boolean", "compound_boolean", "response_weight", "summary"}


class DatasetValidationError(ValueError):
    """A contract violation with a field-oriented message."""


def _require(obj: dict[str, Any], field: str, expected: str, where: str) -> Any:
    if field not in obj:
        raise DatasetValidationError(
            f"dataset={where} field={field} expected={expected} received=missing"
        )
    return obj[field]


def validate_manifest(manifest: dict[str, Any]) -> None:
    dataset_id = str(manifest.get("dataset_id", "unknown"))
    version = _require(manifest, "schema_version", SCHEMA_VERSION, dataset_id)
    if version != SCHEMA_VERSION:
        raise DatasetValidationError(
            f"dataset={dataset_id} file=manifest.json field=schema_version "
            f"expected={SCHEMA_VERSION} received={version!r}"
        )
    for field in (
        "dataset_id",
        "title",
        "source_kind",
        "source_repository",
        "source_commit",
        "source_dirty",
        "source_artifacts",
        "reference_sample",
        "n_events",
        "created_utc",
        "generator_command",
        "capabilities",
    ):
        _require(manifest, field, "present", dataset_id)
    capabilities = manifest["capabilities"]
    if not isinstance(capabilities, dict):
        raise DatasetValidationError(
            f"dataset={dataset_id} file=manifest.json field=capabilities "
            f"expected=object received={type(capabilities).__name__}"
        )
    missing = REQUIRED_CAPABILITIES - capabilities.keys()
    if missing:
        raise DatasetValidationError(
            f"dataset={dataset_id} file=manifest.json field=capabilities "
            f"expected=keys({sorted(REQUIRED_CAPABILITIES)}) received=missing({sorted(missing)})"
        )
    if any(not isinstance(capabilities[key], bool) for key in REQUIRED_CAPABILITIES):
        raise DatasetValidationError(
            f"dataset={dataset_id} file=manifest.json field=capabilities.* "
            "expected=boolean received=non-boolean"
        )


def validate_cuts(cuts_doc: dict[str, Any], dataset_id: str) -> None:
    if cuts_doc.get("schema_version") != SCHEMA_VERSION:
        raise DatasetValidationError(
            f"dataset={dataset_id} file=cuts.json field=schema_version "
            f"expected={SCHEMA_VERSION} received={cuts_doc.get('schema_version')!r}"
        )
    units = cuts_doc.get("unit_conventions")
    expected_units = {"energy": "GeV", "length": "mm", "angles": "radians"}
    if not isinstance(units, dict) or any(units.get(key) != value for key, value in expected_units.items()):
        raise DatasetValidationError(
            f"dataset={dataset_id} file=cuts.json field=unit_conventions "
            f"expected={expected_units} received={units!r}"
        )
    if not isinstance(units.get("adapter_conversions"), list):
        raise DatasetValidationError(
            f"dataset={dataset_id} file=cuts.json field=unit_conventions.adapter_conversions "
            f"expected=array received={units.get('adapter_conversions')!r}"
        )
    cuts = cuts_doc.get("cuts")
    if not isinstance(cuts, list) or not cuts:
        raise DatasetValidationError(
            f"dataset={dataset_id} file=cuts.json field=cuts expected=non-empty-array "
            f"received={type(cuts).__name__}"
        )
    required = {
        "id",
        "name",
        "order",
        "category",
        "kind",
        "mathematical_definition",
        "physical_meaning",
        "analysis_rationale",
        "source_file",
        "source_line_or_symbol",
        "published_or_diagnostic",
        "depends_on_parameters",
        "requires_fields",
    }
    ids: set[str] = set()
    for index, cut in enumerate(cuts):
        missing = required - cut.keys()
        if missing:
            raise DatasetValidationError(
                f"dataset={dataset_id} file=cuts.json field=cuts[{index}] "
                f"expected=fields({sorted(required)}) received=missing({sorted(missing)})"
            )
        if cut["id"] in ids:
            raise DatasetValidationError(
                f"dataset={dataset_id} file=cuts.json field=cuts[{index}].id "
                f"expected=unique received={cut['id']!r}"
            )
        ids.add(cut["id"])
        if cut["kind"] not in CUT_KINDS:
            raise DatasetValidationError(
                f"dataset={dataset_id} file=cuts.json field=cuts[{index}].kind "
                f"expected=one-of({sorted(CUT_KINDS)}) received={cut['kind']!r}"
            )
        if "mathematical_latex" in cut and not isinstance(cut["mathematical_latex"], str):
            raise DatasetValidationError(
                f"dataset={dataset_id} file=cuts.json field=cuts[{index}].mathematical_latex "
                f"expected=string received={type(cut['mathematical_latex']).__name__}"
            )
        if "geometry_overlay" in cut:
            overlay = cut["geometry_overlay"]
            if not isinstance(overlay, dict) or overlay.get("view") != "r_z":
                raise DatasetValidationError(
                    f"dataset={dataset_id} file=cuts.json field=cuts[{index}].geometry_overlay "
                    "expected=r_z-overlay received=invalid"
                )
            for field in ("r_min_mm", "r_max_mm", "abs_z_max_mm"):
                value = overlay.get(field)
                if value is not None and (not isinstance(value, (int, float)) or value < 0):
                    raise DatasetValidationError(
                        f"dataset={dataset_id} file=cuts.json "
                        f"field=cuts[{index}].geometry_overlay.{field} "
                        f"expected=non-negative-number-or-null received={value!r}"
                    )
        parameters = cut.get("parameters", {})
        if not isinstance(parameters, dict) or any(
            not isinstance(key, str) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for key, value in parameters.items()
        ):
            raise DatasetValidationError(
                f"dataset={dataset_id} file=cuts.json field=cuts[{index}].parameters expected=finite-number-map received={parameters!r}"
            )
    orders = [cut["order"] for cut in cuts]
    if orders != sorted(orders) or len(set(orders)) != len(orders):
        raise DatasetValidationError(
            f"dataset={dataset_id} file=cuts.json field=cuts[].order "
            f"expected=strictly-increasing received={orders}"
        )


def validate_summary(summary: dict[str, Any], cuts_doc: dict[str, Any], dataset_id: str) -> None:
    if summary.get("schema_version") != SCHEMA_VERSION:
        raise DatasetValidationError(
            f"dataset={dataset_id} file=summary.json field=schema_version "
            f"expected={SCHEMA_VERSION} received={summary.get('schema_version')!r}"
        )
    cutflow = summary.get("cutflow")
    if not isinstance(cutflow, dict):
        raise DatasetValidationError(
            f"dataset={dataset_id} file=summary.json field=cutflow expected=object received=missing"
        )
    stages = cutflow.get("stages")
    if not isinstance(stages, list):
        raise DatasetValidationError(
            f"dataset={dataset_id} file=summary.json field=cutflow.stages "
            "expected=array received=missing"
        )
    cut_ids = [cut["id"] for cut in cuts_doc["cuts"]]
    stage_ids = [stage.get("cut_id") for stage in stages]
    if stage_ids != cut_ids:
        raise DatasetValidationError(
            f"dataset={dataset_id} file=summary.json field=cutflow.stages[].cut_id "
            f"expected={cut_ids} received={stage_ids}"
        )
    previous = cutflow.get("denominator", {}).get("weighted_events")
    if not isinstance(previous, (int, float)) or previous < 0:
        raise DatasetValidationError(
            f"dataset={dataset_id} file=summary.json field=cutflow.denominator.weighted_events "
            f"expected=non-negative-number received={previous!r}"
        )
    for index, stage in enumerate(stages):
        before, after = stage.get("n_before"), stage.get("n_after")
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            raise DatasetValidationError(
                f"dataset={dataset_id} file=summary.json field=cutflow.stages[{index}].n_after "
                "expected=number received=missing-or-non-number"
            )
        if before != previous:
            raise DatasetValidationError(
                f"dataset={dataset_id} file=summary.json field=cutflow.stages[{index}].n_before "
                f"expected={previous!r} received={before!r}"
            )
        if after < 0 or after > before:
            raise DatasetValidationError(
                f"dataset={dataset_id} file=summary.json field=cutflow.stages[{index}].n_after "
                f"expected=0..{before!r} received={after!r}"
            )
        previous = after


def validate_dataset(
    manifest: dict[str, Any], cuts_doc: dict[str, Any], summary: dict[str, Any]
) -> None:
    validate_manifest(manifest)
    dataset_id = manifest["dataset_id"]
    if cuts_doc.get("dataset_id") != dataset_id or summary.get("dataset_id") != dataset_id:
        raise DatasetValidationError(
            f"dataset={dataset_id} field=dataset_id expected=same-in-all-files "
            f"received=cuts:{cuts_doc.get('dataset_id')!r},summary:{summary.get('dataset_id')!r}"
        )
    validate_cuts(cuts_doc, dataset_id)
    validate_summary(summary, cuts_doc, dataset_id)
    capabilities = manifest["capabilities"]
    if capabilities["atomic_event_cuts"] and not capabilities["cutflow"]:
        raise DatasetValidationError(
            f"dataset={dataset_id} field=capabilities.atomic_event_cuts "
            "expected=cutflow-enabled received=cutflow-false"
        )
    if capabilities["jet_what_if"] and not (
        capabilities["atomic_event_cuts"] and capabilities["jet_observables"]
    ):
        raise DatasetValidationError(
            f"dataset={dataset_id} field=capabilities.jet_what_if "
            "expected=atomic_event_cuts-and-jet_observables received=unsupported-dependencies"
        )


def validate_events(
    events_doc: dict[str, Any],
    manifest: dict[str, Any],
    cuts_doc: dict[str, Any],
    *,
    expected_count: int | None = None,
    file_name: str = "events.json",
) -> None:
    """Validate an event pack without coercing missing values.

    ``expected_count`` defaults to ``manifest.n_events`` (the primary
    events.json convention). A supplementary geometry pack (a different file,
    a different, typically smaller, curated event count) passes its own
    ``manifest.geometry_pack.event_count`` and ``file_name="geometry_events.json"``
    instead; the array-shape rules below are otherwise identical.
    """

    dataset_id = manifest["dataset_id"]
    if expected_count is None:
        expected_count = manifest.get("n_events")
    if events_doc.get("schema_version") != SCHEMA_VERSION:
        raise DatasetValidationError(
            f"dataset={dataset_id} file={file_name} field=schema_version "
            f"expected={SCHEMA_VERSION} received={events_doc.get('schema_version')!r}"
        )
    if events_doc.get("dataset_id") != dataset_id:
        raise DatasetValidationError(
            f"dataset={dataset_id} file={file_name} field=dataset_id "
            f"expected={dataset_id!r} received={events_doc.get('dataset_id')!r}"
        )
    events = events_doc.get("events")
    if not isinstance(events, list) or not events:
        raise DatasetValidationError(
            f"dataset={dataset_id} file={file_name} field=events expected=non-empty-array "
            f"received={type(events).__name__}"
        )
    if expected_count != len(events):
        raise DatasetValidationError(
            f"dataset={dataset_id} file={file_name} field=events.length "
            f"expected={expected_count!r} received={len(events)}"
        )
    capabilities = manifest["capabilities"]
    if not capabilities.get("atomic_event_cuts"):
        raise DatasetValidationError(
            f"dataset={dataset_id} field=capabilities.atomic_event_cuts "
            "expected=true received=false (events.json requires atomic event cuts)"
        )
    if not (capabilities.get("jet_observables") or capabilities.get("dv_radial") or capabilities.get("dv_xyz")):
        raise DatasetValidationError(
            f"dataset={dataset_id} field=capabilities expected=at-least-one-of("
            "jet_observables,dv_radial,dv_xyz) received=none (events.json would serialize nothing inspectable)"
        )
    # A boolean cut normally lives per-vertex (the frontend ORs across
    # vertices to get the event verdict). A source that only ever computed a
    # jet-blind event-level OR internally (no per-vertex breakdown was ever
    # serialized) may instead declare `predicate_scope: "event"` on the cut,
    # which moves that boolean into `event.predicates` directly. Absence of
    # the field means "vertex", matching every dataset written before this
    # field existed.
    boolean_cuts = [
        cut for cut in cuts_doc["cuts"]
        if cut["kind"] in {"atomic_boolean", "compound_boolean"} and cut["id"] != "jet_selection"
    ]
    event_scope_cut_ids = {cut["id"] for cut in boolean_cuts if cut.get("predicate_scope") == "event"}
    required_vertex_cuts = {cut["id"] for cut in boolean_cuts if cut["id"] not in event_scope_cut_ids}
    has_geometry = bool(capabilities.get("dv_radial") or capabilities.get("dv_xyz"))
    seen_ids: set[int] = set()
    for index, event in enumerate(events):
        where = f"events[{index}]"
        if not isinstance(event, dict):
            raise DatasetValidationError(
                f"dataset={dataset_id} file={file_name} field={where} expected=object received={type(event).__name__}"
            )
        event_id = event.get("event_id")
        if not isinstance(event_id, int) or event_id in seen_ids:
            raise DatasetValidationError(
                f"dataset={dataset_id} file={file_name} field={where}.event_id expected=unique-integer received={event_id!r}"
            )
        seen_ids.add(event_id)
        weight = event.get("weight")
        if not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
            raise DatasetValidationError(
                f"dataset={dataset_id} file={file_name} field={where}.weight expected=non-negative-finite-number received={weight!r}"
            )
        if not isinstance(event.get("valid_weight"), bool):
            raise DatasetValidationError(
                f"dataset={dataset_id} file={file_name} field={where}.valid_weight expected=boolean received={event.get('valid_weight')!r}"
            )
        predicates = event.get("predicates")
        if not isinstance(predicates, dict) or not isinstance(predicates.get("jet_selection"), bool):
            raise DatasetValidationError(
                f"dataset={dataset_id} file={file_name} field={where}.predicates.jet_selection expected=boolean received=missing-or-invalid"
            )
        for cut_id in event_scope_cut_ids:
            if not isinstance(predicates.get(cut_id), bool):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={where}.predicates.{cut_id} "
                    f"expected=boolean received={predicates.get(cut_id)!r}"
                )
        jets = event.get("jets")
        if not isinstance(jets, list):
            raise DatasetValidationError(
                f"dataset={dataset_id} file={file_name} field={where}.jets expected=array received={type(jets).__name__}"
            )
        for jet_index, jet in enumerate(jets):
            if not isinstance(jet, dict):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={where}.jets[{jet_index}] expected=object received={type(jet).__name__}"
                )
            for field in ("rank", "pt_GeV"):
                value = jet.get(field)
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise DatasetValidationError(
                        f"dataset={dataset_id} file={file_name} field={where}.jets[{jet_index}].{field} expected=finite-number received={value!r}"
                    )
            # eta/phi are nullable: some sources serialize jet pT without a
            # reconstructed direction. A jet with unknown direction is never
            # fabricated a position; the frontend renders it as unavailable
            # rather than placing it in 3D. See DATA_CONTRACT.md.
            for field in ("eta", "phi"):
                value = jet.get(field)
                if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                    raise DatasetValidationError(
                        f"dataset={dataset_id} file={file_name} field={where}.jets[{jet_index}].{field} expected=finite-number-or-null received={value!r}"
                    )
        vertices = event.get("vertices")
        if not isinstance(vertices, list):
            raise DatasetValidationError(
                f"dataset={dataset_id} file={file_name} field={where}.vertices expected=array received={type(vertices).__name__}"
            )
        if not has_geometry:
            # No vertex coordinates exist in the source at all (dv_radial and
            # dv_xyz are both false): a per-vertex geometric object cannot be
            # validated without fabricating positions. DV predicates for such
            # a dataset must be declared `predicate_scope: "event"` instead.
            if vertices:
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={where}.vertices "
                    "expected=empty (capabilities.dv_radial and capabilities.dv_xyz are both false) "
                    f"received=non-empty(len={len(vertices)})"
                )
            continue
        for vertex_index, vertex in enumerate(vertices):
            vertex_where = f"{where}.vertices[{vertex_index}]"
            if not isinstance(vertex, dict):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={vertex_where} expected=object received={type(vertex).__name__}"
                )
            for field in ("x_mm", "y_mm", "z_mm", "r_mm", "mass_GeV", "vertex_eff"):
                value = vertex.get(field)
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise DatasetValidationError(
                        f"dataset={dataset_id} file={file_name} field={vertex_where}.{field} expected=finite-number received={value!r}"
                    )
            llp_momentum = vertex.get("llp_momentum_GeV")
            if not isinstance(llp_momentum, dict) or any(
                not isinstance(llp_momentum.get(component), (int, float))
                or not math.isfinite(llp_momentum[component])
                for component in ("px", "py", "pz")
            ):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={vertex_where}.llp_momentum_GeV "
                    "expected=finite-px-py-pz received=missing-or-invalid"
                )
            expected_r = math.hypot(vertex["x_mm"], vertex["y_mm"])
            if not math.isclose(vertex["r_mm"], expected_r, rel_tol=1e-12, abs_tol=1e-12):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={vertex_where}.r_mm expected=hypot(x_mm,y_mm) received={vertex['r_mm']!r}"
                )
            # A vertex must carry at least every predicate_scope="vertex" cut.
            # It may additionally carry a genuine per-vertex breakdown for a
            # cut declared predicate_scope="event" at the dataset level, when
            # this specific event pack (e.g. a curated geometry replay) did
            # compute one — informational detail, never used for the
            # frontend's event-vs-vertex cut-scope routing (see
            # DATA_CONTRACT.md).
            vertex_predicates = vertex.get("predicates")
            if not isinstance(vertex_predicates, dict) or not required_vertex_cuts.issubset(vertex_predicates):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={vertex_where}.predicates "
                    f"expected=keys(at-least {sorted(required_vertex_cuts)}) received={sorted(vertex_predicates) if isinstance(vertex_predicates, dict) else type(vertex_predicates).__name__}"
                )
            if any(not isinstance(value, bool) for value in vertex_predicates.values()):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={vertex_where}.predicates.* expected=boolean received=non-boolean"
                )
            tracks = vertex.get("tracks")
            if not isinstance(tracks, list):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={vertex_where}.tracks expected=array received={type(tracks).__name__}"
                )
            selected_tracks = 0
            impacted_tracks = 0
            for track_index, track in enumerate(tracks):
                track_where = f"{vertex_where}.tracks[{track_index}]"
                if not isinstance(track, dict):
                    raise DatasetValidationError(
                        f"dataset={dataset_id} file={file_name} field={track_where} expected=object received={type(track).__name__}"
                    )
                for field in (
                    "track_index", "pdg_id", "charge", "x_prod_mm", "y_prod_mm", "z_prod_mm",
                    "px_GeV", "py_GeV", "pz_GeV", "d0_mm", "transverse_distance_mm",
                ):
                    value = track.get(field)
                    if not isinstance(value, (int, float)) or not math.isfinite(value):
                        raise DatasetValidationError(
                            f"dataset={dataset_id} file={file_name} field={track_where}.{field} expected=finite-number received={value!r}"
                        )
                for field in ("passes_d0", "selected_for_dv"):
                    if not isinstance(track.get(field), bool):
                        raise DatasetValidationError(
                            f"dataset={dataset_id} file={file_name} field={track_where}.{field} expected=boolean received={track.get(field)!r}"
                        )
                phi = math.atan2(track["py_GeV"], track["px_GeV"])
                phi_prod = math.atan2(track["y_prod_mm"], track["x_prod_mm"])
                delta_phi = phi_prod - phi
                if abs(delta_phi) > math.pi:
                    delta_phi = 2 * math.pi - abs(delta_phi)
                expected_d0 = math.hypot(track["x_prod_mm"], track["y_prod_mm"]) * math.sin(delta_phi)
                if not math.isclose(track["d0_mm"], expected_d0, rel_tol=1e-12, abs_tol=1e-12):
                    raise DatasetValidationError(
                        f"dataset={dataset_id} file={file_name} field={track_where}.d0_mm expected=recast-proxy received={track['d0_mm']!r}"
                    )
                selected_tracks += int(track["selected_for_dv"])
                impacted_tracks += int(track["passes_d0"])
            if selected_tracks != vertex.get("selected_track_count") or impacted_tracks != vertex.get("impacted_track_count"):
                raise DatasetValidationError(
                    f"dataset={dataset_id} file={file_name} field={vertex_where}.tracks expected=count-consistency "
                    f"received=selected:{selected_tracks},impacted:{impacted_tracks}"
                )
