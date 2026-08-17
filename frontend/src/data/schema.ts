import { recastD0Mm } from '../core/geometry';

export const SCHEMA_VERSION = 'viewer.dataset.v1' as const;

export type CapabilityName =
  | 'cutflow'
  | 'atomic_event_cuts'
  | 'jet_observables'
  | 'jet_what_if'
  | 'dv_radial'
  | 'dv_xyz'
  | 'response_weights';

export type Capabilities = Record<CapabilityName, boolean>;

export interface SourceArtifact {
  path: string;
  sha256: string;
}

export interface Manifest {
  schema_version: typeof SCHEMA_VERSION;
  dataset_id: string;
  title: string;
  source_kind: string;
  source_repository: string;
  source_commit: string;
  source_dirty: boolean;
  source_artifacts: SourceArtifact[];
  reference_sample: string;
  n_events: number | null;
  event_count_semantics?: Record<string, string | number>;
  created_utc: string;
  generator_command: string;
  capabilities: Capabilities;
  translations?: Record<string, { title: string; reference_sample: string }>;
}

export type CutKind = 'atomic_boolean' | 'compound_boolean' | 'response_weight' | 'summary';

export interface GeometryOverlay {
  view: 'r_z';
  r_min_mm: number | null;
  r_max_mm: number | null;
  abs_z_max_mm: number | null;
}

export interface CutDefinition {
  id: string;
  name: string;
  order: number;
  category: string;
  kind: CutKind;
  mathematical_definition: string;
  mathematical_latex?: string;
  geometry_overlay?: GeometryOverlay;
  physical_meaning: string;
  analysis_rationale: string;
  source_file: string;
  source_line_or_symbol: string;
  published_or_diagnostic: 'published' | 'diagnostic';
  depends_on_parameters: string[];
  parameters?: Record<string, number>;
  requires_fields: string[];
  translations?: Record<string, {
    name: string;
    physical_meaning: string;
    analysis_rationale: string;
  }>;
}

export interface EventJet {
  rank: number;
  pt_GeV: number;
  eta: number;
  phi: number;
}

export interface EventTrack {
  track_index: number;
  pdg_id: number;
  charge: number;
  x_prod_mm: number;
  y_prod_mm: number;
  z_prod_mm: number;
  px_GeV: number;
  py_GeV: number;
  pz_GeV: number;
  d0_mm: number;
  transverse_distance_mm: number;
  passes_d0: boolean;
  selected_for_dv: boolean;
}

export interface EventVertex {
  llp_index: number;
  pdg_id: number;
  x_mm: number;
  y_mm: number;
  z_mm: number;
  r_mm: number;
  llp_momentum_GeV: { px: number; py: number; pz: number };
  selected_track_count: number;
  impacted_track_count: number;
  mass_GeV: number;
  vertex_eff: number;
  predicates: Record<string, boolean>;
  tracks: EventTrack[];
}

export type GeometryLandmarkKind = 'detector_hardware' | 'analysis_boundary' | 'response_bin';

export interface GeometryLandmark {
  id: string;
  display_name_es: string;
  display_name_en: string;
  kind: GeometryLandmarkKind;
  radius_mm: number | null;
  z_extent_mm: number | null;
  abs_z_mm?: number | null;
  source: string;
  source_note: string;
  source_note_es: string;
  source_note_en: string;
  relevance_es: string;
  relevance_en: string;
}

export interface DetectorGeometry {
  schema_version: 'viewer.detector_geometry.v1';
  coordinate_system: string;
  scope_es: string;
  scope_en: string;
  landmarks: GeometryLandmark[];
}

export interface EventRecord {
  event_id: number;
  subrun: number;
  source_event_index: number;
  weight: number;
  source_weight_mb: number;
  valid_weight: boolean;
  observables: { sum_pt_GeV: number; r_max_mm: number };
  predicates: { jet_selection: boolean };
  response: { vertex_eff: number; event_eff: number };
  jets: EventJet[];
  vertices: EventVertex[];
}

export interface EventsDocument {
  schema_version: typeof SCHEMA_VERSION;
  dataset_id: string;
  selection_semantics: Record<string, string>;
  events: EventRecord[];
}

export interface JetLogic {
  region: string;
  rank_indexing: string;
  missing_jet_semantics: string;
  combination: string;
  branches: Array<{ jet_rank: number; threshold_GeV: number; comparison: string }>;
  event_level_note: string;
}

export interface CutsDocument {
  schema_version: typeof SCHEMA_VERSION;
  dataset_id: string;
  unit_conventions: {
    energy: 'GeV';
    length: 'mm';
    angles: 'radians';
    adapter_conversions: string[];
  };
  cuts: CutDefinition[];
  jet_logic?: JetLogic;
}

export interface CutflowStage {
  cut_id: string;
  n_before: number;
  n_after: number;
  conditional_loss: number | null;
  cumulative_efficiency_pct: number;
  reference: {
    authors_recast_efficiency_pct: number | null;
    atlas_full_sim_pct: number | null;
    atlas_parametric_pct: number | null;
    paper_recast_pct: number | null;
    relative_difference_reproduction_vs_authors: number | null;
  };
}

export interface Summary {
  schema_version: typeof SCHEMA_VERSION;
  dataset_id: string;
  cutflow: {
    region: string;
    count_semantics: 'weighted_events';
    denominator: {
      weighted_events: number;
      raw_recast_events: number | null;
      generated_events: number | null;
    };
    stages: CutflowStage[];
  };
  external_validation: {
    status: string;
    scope: string;
    reference: string;
    uncertainty_status: unknown;
    note: string;
    translations?: Record<string, { scope: string; reference: string; note: string }>;
  };
}

export interface ViewerDataset {
  manifest: Manifest;
  cuts: CutsDocument;
  summary: Summary;
  events?: EventsDocument;
}

export class DatasetError extends Error {
  constructor(
    public readonly dataset: string,
    public readonly file: string,
    public readonly field: string,
    public readonly expected: string,
    public readonly received: unknown,
  ) {
    super(
      `dataset=${dataset} file=${file} field=${field} expected=${expected} received=${JSON.stringify(received)}`,
    );
  }
}

const capabilityNames: CapabilityName[] = [
  'cutflow',
  'atomic_event_cuts',
  'jet_observables',
  'jet_what_if',
  'dv_radial',
  'dv_xyz',
  'response_weights',
];

function record(value: unknown, dataset: string, file: string, field = '$'): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new DatasetError(dataset, file, field, 'object', value);
  }
  return value as Record<string, unknown>;
}

function stringField(object: Record<string, unknown>, key: string, dataset: string, file: string): string {
  if (typeof object[key] !== 'string') throw new DatasetError(dataset, file, key, 'string', object[key]);
  return object[key];
}

function numberField(object: Record<string, unknown>, key: string, dataset: string, file: string): number {
  if (typeof object[key] !== 'number' || !Number.isFinite(object[key])) {
    throw new DatasetError(dataset, file, key, 'finite number', object[key]);
  }
  return object[key];
}

function nullableNumberField(object: Record<string, unknown>, key: string, dataset: string, file: string): number | null {
  if (object[key] === null) return null;
  return numberField(object, key, dataset, file);
}

function stringArrayField(object: Record<string, unknown>, key: string, dataset: string, file: string): string[] {
  const value = object[key];
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
    throw new DatasetError(dataset, file, key, 'string array', value);
  }
  return value;
}

function schema(object: Record<string, unknown>, dataset: string, file: string): void {
  const received = object.schema_version;
  if (received !== SCHEMA_VERSION) {
    throw new DatasetError(dataset, file, 'schema_version', SCHEMA_VERSION, received);
  }
}

export function validateDocuments(
  manifestValue: unknown,
  cutsValue: unknown,
  summaryValue: unknown,
  requestedDataset = 'unknown',
): ViewerDataset {
  const manifestObject = record(manifestValue, requestedDataset, 'manifest.json');
  const dataset = typeof manifestObject.dataset_id === 'string' ? manifestObject.dataset_id : requestedDataset;
  schema(manifestObject, dataset, 'manifest.json');
  for (const key of [
    'dataset_id', 'title', 'source_kind', 'source_repository', 'source_commit',
    'reference_sample', 'created_utc', 'generator_command',
  ]) stringField(manifestObject, key, dataset, 'manifest.json');
  if (typeof manifestObject.source_dirty !== 'boolean') {
    throw new DatasetError(dataset, 'manifest.json', 'source_dirty', 'boolean', manifestObject.source_dirty);
  }
  if (manifestObject.n_events !== null && (typeof manifestObject.n_events !== 'number' || !Number.isFinite(manifestObject.n_events))) {
    throw new DatasetError(dataset, 'manifest.json', 'n_events', 'finite number or null', manifestObject.n_events);
  }
  if (!Array.isArray(manifestObject.source_artifacts)) {
    throw new DatasetError(dataset, 'manifest.json', 'source_artifacts', 'array', manifestObject.source_artifacts);
  }
  if (manifestObject.translations !== undefined) {
    const translations = record(manifestObject.translations, dataset, 'manifest.json', 'translations');
    for (const [language, rawTranslation] of Object.entries(translations)) {
      const translation = record(rawTranslation, dataset, 'manifest.json', `translations.${language}`);
      stringField(translation, 'title', dataset, 'manifest.json');
      stringField(translation, 'reference_sample', dataset, 'manifest.json');
    }
  }
  for (const [index, rawArtifact] of manifestObject.source_artifacts.entries()) {
    const artifact = record(rawArtifact, dataset, 'manifest.json', `source_artifacts[${index}]`);
    stringField(artifact, 'path', dataset, 'manifest.json');
    const digest = stringField(artifact, 'sha256', dataset, 'manifest.json');
    if (!/^[0-9a-f]{64}$/.test(digest)) {
      throw new DatasetError(dataset, 'manifest.json', `source_artifacts[${index}].sha256`, '64 lowercase hex characters', digest);
    }
  }
  const capabilities = record(manifestObject.capabilities, dataset, 'manifest.json', 'capabilities');
  for (const name of capabilityNames) {
    if (typeof capabilities[name] !== 'boolean') {
      throw new DatasetError(dataset, 'manifest.json', `capabilities.${name}`, 'boolean', capabilities[name]);
    }
  }

  const cutsObject = record(cutsValue, dataset, 'cuts.json');
  schema(cutsObject, dataset, 'cuts.json');
  if (cutsObject.dataset_id !== dataset) {
    throw new DatasetError(dataset, 'cuts.json', 'dataset_id', dataset, cutsObject.dataset_id);
  }
  const units = record(cutsObject.unit_conventions, dataset, 'cuts.json', 'unit_conventions');
  for (const [key, expected] of Object.entries({ energy: 'GeV', length: 'mm', angles: 'radians' })) {
    if (units[key] !== expected) throw new DatasetError(dataset, 'cuts.json', `unit_conventions.${key}`, expected, units[key]);
  }
  stringArrayField(units, 'adapter_conversions', dataset, 'cuts.json');
  if (!Array.isArray(cutsObject.cuts) || cutsObject.cuts.length === 0) {
    throw new DatasetError(dataset, 'cuts.json', 'cuts', 'non-empty array', cutsObject.cuts);
  }
  let previousOrder = -Infinity;
  for (const [index, rawCut] of cutsObject.cuts.entries()) {
    const cut = record(rawCut, dataset, 'cuts.json', `cuts[${index}]`);
    for (const key of [
      'id', 'name', 'category', 'kind', 'mathematical_definition', 'physical_meaning',
      'analysis_rationale', 'source_file', 'source_line_or_symbol', 'published_or_diagnostic',
    ]) stringField(cut, key, dataset, 'cuts.json');
    if (!['atomic_boolean', 'compound_boolean', 'response_weight', 'summary'].includes(String(cut.kind))) {
      throw new DatasetError(dataset, 'cuts.json', `cuts[${index}].kind`, 'known cut kind', cut.kind);
    }
    if (!['published', 'diagnostic'].includes(String(cut.published_or_diagnostic))) {
      throw new DatasetError(dataset, 'cuts.json', `cuts[${index}].published_or_diagnostic`, 'published or diagnostic', cut.published_or_diagnostic);
    }
    const order = numberField(cut, 'order', dataset, 'cuts.json');
    if (order <= previousOrder) throw new DatasetError(dataset, 'cuts.json', `cuts[${index}].order`, `>${previousOrder}`, order);
    previousOrder = order;
    stringArrayField(cut, 'depends_on_parameters', dataset, 'cuts.json');
    if (cut.parameters !== undefined) {
      const parameters = record(cut.parameters, dataset, 'cuts.json', `cuts[${index}].parameters`);
      for (const [name, value] of Object.entries(parameters)) {
        if (typeof value !== 'number' || !Number.isFinite(value)) throw new DatasetError(dataset, 'cuts.json', `cuts[${index}].parameters.${name}`, 'finite number', value);
      }
    }
    stringArrayField(cut, 'requires_fields', dataset, 'cuts.json');
    if (cut.mathematical_latex !== undefined && typeof cut.mathematical_latex !== 'string') {
      throw new DatasetError(dataset, 'cuts.json', `cuts[${index}].mathematical_latex`, 'string', cut.mathematical_latex);
    }
    if (cut.translations !== undefined) {
      const translations = record(cut.translations, dataset, 'cuts.json', `cuts[${index}].translations`);
      for (const [language, rawTranslation] of Object.entries(translations)) {
        const translation = record(rawTranslation, dataset, 'cuts.json', `cuts[${index}].translations.${language}`);
        for (const key of ['name', 'physical_meaning', 'analysis_rationale']) {
          stringField(translation, key, dataset, 'cuts.json');
        }
      }
    }
    if (cut.geometry_overlay !== undefined) {
      const overlay = record(cut.geometry_overlay, dataset, 'cuts.json', `cuts[${index}].geometry_overlay`);
      if (overlay.view !== 'r_z') {
        throw new DatasetError(dataset, 'cuts.json', `cuts[${index}].geometry_overlay.view`, 'r_z', overlay.view);
      }
      for (const key of ['r_min_mm', 'r_max_mm', 'abs_z_max_mm']) {
        if (overlay[key] !== null && (typeof overlay[key] !== 'number' || !Number.isFinite(overlay[key]) || overlay[key] < 0)) {
          throw new DatasetError(dataset, 'cuts.json', `cuts[${index}].geometry_overlay.${key}`, 'non-negative finite number or null', overlay[key]);
        }
      }
    }
  }
  if (cutsObject.jet_logic !== undefined) {
    const logic = record(cutsObject.jet_logic, dataset, 'cuts.json', 'jet_logic');
    for (const key of ['region', 'rank_indexing', 'missing_jet_semantics', 'combination', 'event_level_note']) {
      stringField(logic, key, dataset, 'cuts.json');
    }
    if (!Array.isArray(logic.branches)) throw new DatasetError(dataset, 'cuts.json', 'jet_logic.branches', 'array', logic.branches);
    for (const [index, rawBranch] of logic.branches.entries()) {
      const branch = record(rawBranch, dataset, 'cuts.json', `jet_logic.branches[${index}]`);
      numberField(branch, 'jet_rank', dataset, 'cuts.json');
      numberField(branch, 'threshold_GeV', dataset, 'cuts.json');
      stringField(branch, 'comparison', dataset, 'cuts.json');
    }
  }

  const summaryObject = record(summaryValue, dataset, 'summary.json');
  schema(summaryObject, dataset, 'summary.json');
  if (summaryObject.dataset_id !== dataset) {
    throw new DatasetError(dataset, 'summary.json', 'dataset_id', dataset, summaryObject.dataset_id);
  }
  const cutflow = record(summaryObject.cutflow, dataset, 'summary.json', 'cutflow');
  stringField(cutflow, 'region', dataset, 'summary.json');
  if (cutflow.count_semantics !== 'weighted_events') {
    throw new DatasetError(dataset, 'summary.json', 'cutflow.count_semantics', 'weighted_events', cutflow.count_semantics);
  }
  const denominator = record(cutflow.denominator, dataset, 'summary.json', 'cutflow.denominator');
  let previous = numberField(denominator, 'weighted_events', dataset, 'summary.json');
  nullableNumberField(denominator, 'raw_recast_events', dataset, 'summary.json');
  nullableNumberField(denominator, 'generated_events', dataset, 'summary.json');
  if (!Array.isArray(cutflow.stages) || cutflow.stages.length !== cutsObject.cuts.length) {
    throw new DatasetError(dataset, 'summary.json', 'cutflow.stages', `${cutsObject.cuts.length} stages`, cutflow.stages);
  }
  for (const [index, rawStage] of cutflow.stages.entries()) {
    const stage = record(rawStage, dataset, 'summary.json', `cutflow.stages[${index}]`);
    const expectedCut = record(cutsObject.cuts[index], dataset, 'cuts.json');
    if (stage.cut_id !== expectedCut.id) {
      throw new DatasetError(dataset, 'summary.json', `cutflow.stages[${index}].cut_id`, String(expectedCut.id), stage.cut_id);
    }
    const before = numberField(stage, 'n_before', dataset, 'summary.json');
    const after = numberField(stage, 'n_after', dataset, 'summary.json');
    if (before !== previous) throw new DatasetError(dataset, 'summary.json', `cutflow.stages[${index}].n_before`, String(previous), before);
    if (after < 0 || after > before) throw new DatasetError(dataset, 'summary.json', `cutflow.stages[${index}].n_after`, `0..${before}`, after);
    if (stage.conditional_loss !== null && (typeof stage.conditional_loss !== 'number' || !Number.isFinite(stage.conditional_loss))) {
      throw new DatasetError(dataset, 'summary.json', `cutflow.stages[${index}].conditional_loss`, 'number or null', stage.conditional_loss);
    }
    numberField(stage, 'cumulative_efficiency_pct', dataset, 'summary.json');
    const reference = record(stage.reference, dataset, 'summary.json', `cutflow.stages[${index}].reference`);
    for (const key of [
      'authors_recast_efficiency_pct', 'atlas_full_sim_pct', 'atlas_parametric_pct',
      'paper_recast_pct', 'relative_difference_reproduction_vs_authors',
    ]) nullableNumberField(reference, key, dataset, 'summary.json');
    previous = after;
  }
  const externalValidation = record(summaryObject.external_validation, dataset, 'summary.json', 'external_validation');
  for (const key of ['status', 'scope', 'reference', 'note']) {
    stringField(externalValidation, key, dataset, 'summary.json');
  }
  if (!Object.hasOwn(externalValidation, 'uncertainty_status')) {
    throw new DatasetError(dataset, 'summary.json', 'external_validation.uncertainty_status', 'present', undefined);
  }
  if (externalValidation.translations !== undefined) {
    const translations = record(externalValidation.translations, dataset, 'summary.json', 'external_validation.translations');
    for (const [language, rawTranslation] of Object.entries(translations)) {
      const translation = record(rawTranslation, dataset, 'summary.json', `external_validation.translations.${language}`);
      for (const key of ['scope', 'reference', 'note']) stringField(translation, key, dataset, 'summary.json');
    }
  }
  if (capabilities.jet_what_if && !(capabilities.atomic_event_cuts && capabilities.jet_observables)) {
    throw new DatasetError(dataset, 'manifest.json', 'capabilities.jet_what_if', 'requires atomic_event_cuts and jet_observables', true);
  }

  return { manifest: manifestValue as Manifest, cuts: cutsValue as CutsDocument, summary: summaryValue as Summary };
}

export function validateEventsDocument(
  eventsValue: unknown,
  dataset: ViewerDataset,
): EventsDocument {
  const { dataset_id: datasetId, n_events: expectedEvents } = dataset.manifest;
  const document = record(eventsValue, datasetId, 'events.json');
  schema(document, datasetId, 'events.json');
  if (document.dataset_id !== datasetId) {
    throw new DatasetError(datasetId, 'events.json', 'dataset_id', datasetId, document.dataset_id);
  }
  const semantics = record(document.selection_semantics, datasetId, 'events.json', 'selection_semantics');
  for (const [key, value] of Object.entries(semantics)) {
    if (typeof value !== 'string') throw new DatasetError(datasetId, 'events.json', `selection_semantics.${key}`, 'string', value);
  }
  if (!Array.isArray(document.events) || document.events.length === 0) {
    throw new DatasetError(datasetId, 'events.json', 'events', 'non-empty array', document.events);
  }
  if (expectedEvents !== null && document.events.length !== expectedEvents) {
    throw new DatasetError(datasetId, 'events.json', 'events.length', String(expectedEvents), document.events.length);
  }
  const vertexCutIds = new Set(
    dataset.cuts.cuts
      .filter((cut) => cut.id !== 'jet_selection' && cut.kind !== 'response_weight' && cut.kind !== 'summary')
      .map((cut) => cut.id),
  );
  const eventIds = new Set<number>();
  for (const [eventIndex, rawEvent] of document.events.entries()) {
    const event = record(rawEvent, datasetId, 'events.json', `events[${eventIndex}]`);
    const eventId = numberField(event, 'event_id', datasetId, 'events.json');
    if (!Number.isInteger(eventId) || eventIds.has(eventId)) {
      throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].event_id`, 'unique integer', eventId);
    }
    eventIds.add(eventId);
    const weight = numberField(event, 'weight', datasetId, 'events.json');
    if (weight < 0) throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].weight`, 'non-negative number', weight);
    if (typeof event.valid_weight !== 'boolean') {
      throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].valid_weight`, 'boolean', event.valid_weight);
    }
    const predicates = record(event.predicates, datasetId, 'events.json', `events[${eventIndex}].predicates`);
    if (typeof predicates.jet_selection !== 'boolean') {
      throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].predicates.jet_selection`, 'boolean', predicates.jet_selection);
    }
    const response = record(event.response, datasetId, 'events.json', `events[${eventIndex}].response`);
    numberField(response, 'vertex_eff', datasetId, 'events.json');
    numberField(response, 'event_eff', datasetId, 'events.json');
    if (!Array.isArray(event.jets)) throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].jets`, 'array', event.jets);
    for (const [jetIndex, rawJet] of event.jets.entries()) {
      const jet = record(rawJet, datasetId, 'events.json', `events[${eventIndex}].jets[${jetIndex}]`);
      for (const field of ['rank', 'pt_GeV', 'eta', 'phi']) numberField(jet, field, datasetId, 'events.json');
    }
    if (!Array.isArray(event.vertices)) throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].vertices`, 'array', event.vertices);
    for (const [vertexIndex, rawVertex] of event.vertices.entries()) {
      const vertex = record(rawVertex, datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}]`);
      for (const field of ['llp_index', 'pdg_id', 'x_mm', 'y_mm', 'z_mm', 'r_mm', 'selected_track_count', 'impacted_track_count', 'mass_GeV', 'vertex_eff']) {
        numberField(vertex, field, datasetId, 'events.json');
      }
      const expectedR = Math.hypot(vertex.x_mm as number, vertex.y_mm as number);
      if (Math.abs((vertex.r_mm as number) - expectedR) > 1e-9 * Math.max(1, expectedR)) {
        throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].r_mm`, 'hypot(x_mm,y_mm)', vertex.r_mm);
      }
      const llpMomentum = record(vertex.llp_momentum_GeV, datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].llp_momentum_GeV`);
      for (const component of ['px', 'py', 'pz']) numberField(llpMomentum, component, datasetId, 'events.json');
      const vertexPredicates = record(vertex.predicates, datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].predicates`);
      if (vertexCutIds.size !== Object.keys(vertexPredicates).length || [...vertexCutIds].some((id) => typeof vertexPredicates[id] !== 'boolean')) {
        throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].predicates`, `boolean keys ${[...vertexCutIds].join(',')}`, vertex.predicates);
      }
      if (!Array.isArray(vertex.tracks)) throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].tracks`, 'array', vertex.tracks);
      let selectedTracks = 0;
      let impactedTracks = 0;
      for (const [trackIndex, rawTrack] of vertex.tracks.entries()) {
        const track = record(rawTrack, datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].tracks[${trackIndex}]`);
        for (const field of ['track_index', 'pdg_id', 'charge', 'x_prod_mm', 'y_prod_mm', 'z_prod_mm', 'px_GeV', 'py_GeV', 'pz_GeV', 'd0_mm', 'transverse_distance_mm']) {
          numberField(track, field, datasetId, 'events.json');
        }
        for (const field of ['passes_d0', 'selected_for_dv']) {
          if (typeof track[field] !== 'boolean') throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].tracks[${trackIndex}].${field}`, 'boolean', track[field]);
        }
        selectedTracks += Number(track.selected_for_dv);
        impactedTracks += Number(track.passes_d0);
        const expectedD0 = recastD0Mm(track as unknown as EventTrack);
        if (Math.abs((track.d0_mm as number) - expectedD0) > 1e-9 * Math.max(1, Math.abs(expectedD0))) {
          throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].tracks[${trackIndex}].d0_mm`, 'recast d0 proxy', track.d0_mm);
        }
      }
      if (selectedTracks !== vertex.selected_track_count || impactedTracks !== vertex.impacted_track_count) {
        throw new DatasetError(datasetId, 'events.json', `events[${eventIndex}].vertices[${vertexIndex}].tracks`, 'counts matching vertex summaries', { selectedTracks, impactedTracks });
      }
    }
  }
  return eventsValue as EventsDocument;
}

export function validateDetectorGeometry(value: unknown): DetectorGeometry {
  const dataset = 'detector-geometry';
  const document = record(value, dataset, 'detector_geometry.json');
  if (document.schema_version !== 'viewer.detector_geometry.v1') {
    throw new DatasetError(dataset, 'detector_geometry.json', 'schema_version', 'viewer.detector_geometry.v1', document.schema_version);
  }
  stringField(document, 'coordinate_system', dataset, 'detector_geometry.json');
  stringField(document, 'scope_es', dataset, 'detector_geometry.json');
  stringField(document, 'scope_en', dataset, 'detector_geometry.json');
  if (!Array.isArray(document.landmarks)) throw new DatasetError(dataset, 'detector_geometry.json', 'landmarks', 'array', document.landmarks);
  const ids = new Set<string>();
  for (const [index, rawLandmark] of document.landmarks.entries()) {
    const landmark = record(rawLandmark, dataset, 'detector_geometry.json', `landmarks[${index}]`);
    for (const field of [
      'id', 'display_name_es', 'display_name_en', 'source', 'source_note',
      'source_note_es', 'source_note_en', 'relevance_es', 'relevance_en',
    ]) stringField(landmark, field, dataset, 'detector_geometry.json');
    if (ids.has(String(landmark.id))) throw new DatasetError(dataset, 'detector_geometry.json', `landmarks[${index}].id`, 'unique', landmark.id);
    ids.add(String(landmark.id));
    if (!['detector_hardware', 'analysis_boundary', 'response_bin'].includes(String(landmark.kind))) {
      throw new DatasetError(dataset, 'detector_geometry.json', `landmarks[${index}].kind`, 'known landmark kind', landmark.kind);
    }
    for (const field of ['radius_mm', 'z_extent_mm']) {
      if (landmark[field] !== null && (typeof landmark[field] !== 'number' || !Number.isFinite(landmark[field]) || landmark[field] < 0)) {
        throw new DatasetError(dataset, 'detector_geometry.json', `landmarks[${index}].${field}`, 'non-negative finite number or null', landmark[field]);
      }
    }
    if (landmark.abs_z_mm !== undefined && landmark.abs_z_mm !== null && (typeof landmark.abs_z_mm !== 'number' || !Number.isFinite(landmark.abs_z_mm) || landmark.abs_z_mm < 0)) {
      throw new DatasetError(dataset, 'detector_geometry.json', `landmarks[${index}].abs_z_mm`, 'non-negative finite number or null', landmark.abs_z_mm);
    }
  }
  return value as DetectorGeometry;
}
