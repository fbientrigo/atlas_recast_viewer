import { describe, expect, it } from 'vitest';
import cutsDocument from '../../../public/data/reference/cuts.json';
import manifest from '../../../public/data/reference/manifest.json';
import { diagnosticAvailability, eventPassesCuts, jetExplorerAvailability, recomputeCumulative, recomputeEventCutflow } from './selection';
import type { Capabilities, CutDefinition, EventRecord } from '../data/schema';

describe('selection core', () => {
  it('disables unsupported modules from capabilities', () => {
    const capabilities = manifest.capabilities as Capabilities;
    expect(diagnosticAvailability(capabilities).available).toBe(false);
    expect(jetExplorerAvailability(capabilities).available).toBe(false);
  });

  it('requires both the capability and a loaded atomic event pack', () => {
    const capabilities = { ...manifest.capabilities, atomic_event_cuts: true } as Capabilities;
    expect(diagnosticAvailability(capabilities).available).toBe(false);
    expect(diagnosticAvailability(capabilities, true).available).toBe(true);
  });

  it('recomputes a toy cumulative cutflow event-by-event', () => {
    const toyCuts = (cutsDocument.cuts as CutDefinition[]).slice(0, 2);
    const events = [
      { weight: 2, predicates: { jet_selection: true, fiducial_dv: true } },
      { weight: 1, predicates: { jet_selection: true, fiducial_dv: false } },
      { weight: 4, predicates: { jet_selection: false, fiducial_dv: true } },
    ];
    expect(recomputeCumulative(events, toyCuts)).toEqual([
      { cutId: 'jet_selection', weightedAfter: 3 },
      { cutId: 'fiducial_dv', weightedAfter: 2 },
    ]);
    expect(recomputeCumulative(events, toyCuts, new Set(['jet_selection']))).toEqual([
      { cutId: 'fiducial_dv', weightedAfter: 6 },
    ]);
  });

  it('never treats a missing predicate as pass', () => {
    const toyCuts = (cutsDocument.cuts as CutDefinition[]).slice(0, 1);
    expect(() => recomputeCumulative([{ weight: 1, predicates: {} }], toyCuts)).toThrow('missing atomic predicate');
  });

  it('requires one vertex to satisfy all enabled DV cuts', () => {
    const event = {
      event_id: 1, weight: 1, valid_weight: true, predicates: { jet_selection: true },
      vertices: [
        { predicates: { fiducial_dv: true, rxy_gt_4_mm: false } },
        { predicates: { fiducial_dv: false, rxy_gt_4_mm: true } },
      ],
    } as unknown as EventRecord;
    expect(eventPassesCuts(event, ['jet_selection', 'fiducial_dv', 'rxy_gt_4_mm'])).toBe(false);
    expect(eventPassesCuts(event, ['jet_selection', 'rxy_gt_4_mm'])).toBe(true);
  });

  it('recomputes disabled cuts without deleting downstream stages', () => {
    const toyCuts = (cutsDocument.cuts as CutDefinition[]).slice(0, 3);
    const event = {
      event_id: 1, weight: 2, valid_weight: true, predicates: { jet_selection: true },
      vertices: [{ predicates: { fiducial_dv: false, rxy_gt_4_mm: true } }],
    } as unknown as EventRecord;
    const flow = recomputeEventCutflow([event], toyCuts, new Set(['fiducial_dv']));
    expect(flow.map((stage) => [stage.cutId, stage.weightedAfter, stage.disabled])).toEqual([
      ['jet_selection', 2, false], ['fiducial_dv', 2, true], ['rxy_gt_4_mm', 2, false],
    ]);
  });
});
