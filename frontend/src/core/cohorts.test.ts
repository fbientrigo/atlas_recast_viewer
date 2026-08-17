import { describe, expect, it } from 'vitest';
import type { CutDefinition, EventRecord } from '../data/schema';
import { cohortEvents, deterministicPage, eventPassesSelectedCut } from './cohorts';

const cut = { id: 'rxy_gt_4_mm', kind: 'atomic_boolean' } as CutDefinition;
const event = (id: number, pass: boolean): EventRecord => ({
  event_id: id, subrun: 0, source_event_index: id, weight: 1, source_weight_mb: 1, valid_weight: true,
  observables: { sum_pt_GeV: 0, r_max_mm: pass ? 5 : 3 }, predicates: { jet_selection: true },
  response: { vertex_eff: 0, event_eff: 0 }, jets: [], vertices: [{
    llp_index: id, pdg_id: 1000022, x_mm: pass ? 5 : 3, y_mm: 0, z_mm: 0, r_mm: pass ? 5 : 3,
    llp_momentum_GeV: { px: 1, py: 0, pz: 0 }, selected_track_count: 0, impacted_track_count: 0,
    mass_GeV: 0, vertex_eff: 0, predicates: { rxy_gt_4_mm: pass }, tracks: [],
  }],
});

describe('deterministic event cohorts', () => {
  const events = [event(9, false), event(2, true), event(5, false), event(1, true)];
  it('uses the canonical selected predicate exactly', () => {
    expect(eventPassesSelectedCut(events[0], cut)).toBe(false);
    expect(cohortEvents(events, 'fails_selected', cut, []).map((item) => item.event_id)).toEqual([5, 9]);
  });
  it('paginates reproducibly in event-id order', () => {
    const sorted = cohortEvents(events, 'all', cut, []);
    expect(deterministicPage(sorted, 2, 0).map((item) => item.event_id)).toEqual([1, 2]);
    expect(deterministicPage(sorted, 2, 1).map((item) => item.event_id)).toEqual([5, 9]);
  });
});
