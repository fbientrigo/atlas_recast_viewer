import type { CutDefinition, EventRecord, EventVertex } from '../data/schema';
import { eventPassesCuts } from './selection';

export type CohortId = 'all' | 'accepted' | 'passes_selected' | 'fails_selected' | 'borderline';

export interface BorderlineDefinition { window: { es: string; en: string }; matches: (event: EventRecord) => boolean }

export function eventPassesSelectedCut(event: EventRecord, cut: CutDefinition): boolean {
  if (cut.kind === 'response_weight' || cut.kind === 'summary') return false;
  if (cut.id === 'jet_selection') return event.predicates.jet_selection;
  return event.vertices.some((vertex) => vertex.predicates[cut.id] === true);
}

function anyVertex(event: EventRecord, predicate: (vertex: EventVertex) => boolean): boolean {
  return event.vertices.some(predicate);
}

export function borderlineDefinition(cut: CutDefinition): BorderlineDefinition | null {
  const parameters = cut.parameters ?? {};
  if (cut.id === 'rxy_gt_4_mm' && parameters.dv_r_min_mm !== undefined) return { window: { es: `|R − ${parameters.dv_r_min_mm} mm| ≤ 1 mm`, en: `|R − ${parameters.dv_r_min_mm} mm| ≤ 1 mm` }, matches: (event) => anyVertex(event, (v) => Math.abs(v.r_mm - parameters.dv_r_min_mm) <= 1) };
  if (cut.id === 'fiducial_dv' && parameters.dv_r_max_mm !== undefined && parameters.dv_abs_z_max_mm !== undefined) return {
    window: { es: `distancia a R=${parameters.dv_r_max_mm} mm o |z|=${parameters.dv_abs_z_max_mm} mm ≤ 10 mm`, en: `distance to R=${parameters.dv_r_max_mm} mm or |z|=${parameters.dv_abs_z_max_mm} mm ≤ 10 mm` },
    matches: (event) => anyVertex(event, (v) => Math.min(Math.abs(v.r_mm - parameters.dv_r_max_mm), Math.abs(Math.abs(v.z_mm) - parameters.dv_abs_z_max_mm)) <= 10),
  };
  if (cut.id === 'd0_gt_2_mm' && parameters.track_abs_d0_min_mm !== undefined) return {
    window: { es: `alguna hija con ||d0| − ${parameters.track_abs_d0_min_mm} mm| ≤ 0,5 mm`, en: `a daughter with ||d0| − ${parameters.track_abs_d0_min_mm} mm| ≤ 0.5 mm` },
    matches: (event) => anyVertex(event, (v) => v.tracks.some((track) => Math.abs(Math.abs(track.d0_mm) - parameters.track_abs_d0_min_mm) <= 0.5)),
  };
  if (cut.id === 'tracks_ge_5' && parameters.selected_track_count_min !== undefined) return { window: { es: `Ntrazas seleccionadas = ${parameters.selected_track_count_min - 1} o ${parameters.selected_track_count_min}`, en: `selected tracks = ${parameters.selected_track_count_min - 1} or ${parameters.selected_track_count_min}` }, matches: (event) => anyVertex(event, (v) => Math.abs(v.selected_track_count - parameters.selected_track_count_min) <= 1 && v.selected_track_count <= parameters.selected_track_count_min) };
  if (cut.id === 'mdv_gt_10_gev' && parameters.dv_mass_min_GeV !== undefined) return { window: { es: `|mDV − ${parameters.dv_mass_min_GeV} GeV| ≤ 2 GeV`, en: `|mDV − ${parameters.dv_mass_min_GeV} GeV| ≤ 2 GeV` }, matches: (event) => anyVertex(event, (v) => Math.abs(v.mass_GeV - parameters.dv_mass_min_GeV) <= 2) };
  return null;
}

export function cohortEvents(
  events: EventRecord[],
  cohort: CohortId,
  selectedCut: CutDefinition,
  enabledCutIds: string[],
): EventRecord[] {
  const borderline = borderlineDefinition(selectedCut);
  return [...events].sort((a, b) => a.event_id - b.event_id).filter((event) => {
    if (cohort === 'all') return true;
    if (cohort === 'accepted') return eventPassesCuts(event, enabledCutIds);
    if (cohort === 'passes_selected') return eventPassesSelectedCut(event, selectedCut);
    if (cohort === 'fails_selected') return !eventPassesSelectedCut(event, selectedCut);
    return Boolean(borderline?.matches(event));
  });
}

export function deterministicPage<T>(items: T[], count: number, page: number): T[] {
  if (items.length === 0 || count <= 0) return [];
  const start = (Math.max(0, page) * count) % items.length;
  return Array.from({ length: Math.min(count, items.length) }, (_, index) => items[(start + index) % items.length]);
}

export function firstFailedCut(event: EventRecord, cuts: CutDefinition[], disabledCuts: Set<string>): string | null {
  for (const cut of cuts) {
    if (disabledCuts.has(cut.id) || cut.kind === 'response_weight' || cut.kind === 'summary') continue;
    if (!eventPassesCuts(event, [cut.id])) return cut.id;
  }
  return null;
}
