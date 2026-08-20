import { describe, expect, it } from 'vitest';
import cutsDocument from '../../../public/data/reference/cuts.json';
import manifest from '../../../public/data/reference/manifest.json';
import h2CutsDocument from '../../../public/data/h2-m150/cuts.json';
import {
  diagnosticAvailability, eventPassesCuts, jetExplorerAvailability, jetSelectionPasses,
  recomputeCumulative, recomputeEventCutflow, thresholdScaleAvailability,
} from './selection';
import type { Capabilities, CutDefinition, EventRecord, JetLogic } from '../data/schema';

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

describe('diagnostic jet-threshold scale s', () => {
  const h2JetLogic = h2CutsDocument.jet_logic as unknown as JetLogic;

  it('is disabled for a dataset without threshold_scale metadata (reference)', () => {
    expect(thresholdScaleAvailability(cutsDocument.jet_logic as unknown as JetLogic).available).toBe(false);
  });

  it('is enabled purely from H2 jet_logic metadata', () => {
    expect(thresholdScaleAvailability(h2JetLogic).available).toBe(true);
  });

  function eventWithJets(jets: Array<{ rank: number; pt_GeV: number }>, additionalPasses = true): EventRecord {
    return {
      event_id: 1, valid_weight: true, weight: 1,
      predicates: { jet_selection: true, trackless_additional: additionalPasses },
      jets: jets.map((jet) => ({ ...jet, eta: null, phi: null })),
      vertices: [],
    } as unknown as EventRecord;
  }

  it('scales only the ordinary branch thresholds, with a strict > comparison', () => {
    // baseline j4 threshold is 137 GeV
    expect(jetSelectionPasses(eventWithJets([{ rank: 4, pt_GeV: 137 }]), h2JetLogic, 1.0)).toBe(false); // strict >
    expect(jetSelectionPasses(eventWithJets([{ rank: 4, pt_GeV: 137.01 }]), h2JetLogic, 1.0)).toBe(true);
    // at s=0.5 the effective threshold is 68.5 GeV
    expect(jetSelectionPasses(eventWithJets([{ rank: 4, pt_GeV: 69 }]), h2JetLogic, 0.5)).toBe(true);
    expect(jetSelectionPasses(eventWithJets([{ rank: 4, pt_GeV: 69 }]), h2JetLogic, 1.0)).toBe(false);
  });

  it('treats a missing rank as branch-false, and combines branches with OR', () => {
    // only j7 present and passing: ordinary OR should still pass
    expect(jetSelectionPasses(eventWithJets([{ rank: 7, pt_GeV: 60 }]), h2JetLogic, 1.0)).toBe(true);
    expect(jetSelectionPasses(eventWithJets([]), h2JetLogic, 1.0)).toBe(false);
  });

  it('requires the additional leg independent of s (s never scales it)', () => {
    const event = eventWithJets([{ rank: 4, pt_GeV: 500 }], false);
    expect(jetSelectionPasses(event, h2JetLogic, 1.0)).toBe(false);
    expect(jetSelectionPasses(event, h2JetLogic, 0.1)).toBe(false);
  });

  it('falls back to the stored baseline predicate when threshold_scale is unsupported', () => {
    const referenceLogic = cutsDocument.jet_logic as unknown as JetLogic;
    const passingEvent = { predicates: { jet_selection: true }, jets: [] } as unknown as EventRecord;
    const failingEvent = { predicates: { jet_selection: false }, jets: [] } as unknown as EventRecord;
    expect(jetSelectionPasses(passingEvent, referenceLogic, 0.1)).toBe(true);
    expect(jetSelectionPasses(failingEvent, referenceLogic, 0.1)).toBe(false);
  });
});

describe('event-scoped predicates (no per-vertex breakdown)', () => {
  it('reads an event-scoped DV cut directly from event.predicates, not empty vertices', () => {
    const h2Cuts = h2CutsDocument.cuts as unknown as CutDefinition[];
    const event = {
      event_id: 1, valid_weight: true, weight: 1,
      predicates: { jet_selection: true, fiducial_dv: true, rxy_gt_4_mm: false },
      vertices: [],
    } as unknown as EventRecord;
    expect(eventPassesCuts(event, ['jet_selection', 'fiducial_dv'], h2Cuts)).toBe(true);
    expect(eventPassesCuts(event, ['jet_selection', 'rxy_gt_4_mm'], h2Cuts)).toBe(false);
  });
});
