import { describe, expect, it } from 'vitest';
import geometryJson from '../../../public/data/detector_geometry.json';
import type { CutDefinition, DetectorGeometry, EventRecord } from '../data/schema';
import {
  jetBranchPasses,
  radialTickValues,
  resolveInspectionTarget,
  targetKey,
  trackPtOverChargeGeV,
  type InspectionTarget,
} from './inspection';

const event = {
  event_id: 7,
  jets: [{ rank: 4, pt_GeV: 251, eta: 0.2, phi: 1 }],
  vertices: [{ tracks: [{ charge: -1, px_GeV: 3, py_GeV: 4 }] }],
} as EventRecord;
const cut = { parameters: { highpt_j4_pt_GeV: 250 } } as unknown as CutDefinition;

describe('linked physics inspection', () => {
  it('resolves only real canonical objects', () => {
    const geometry = geometryJson as DetectorGeometry;
    expect(resolveInspectionTarget({ kind: 'layer', landmarkId: 'ibl' }, [event], geometry)?.kind).toBe('layer');
    expect(resolveInspectionTarget({ kind: 'jet', eventId: 7, jetRank: 4 }, [event], geometry)?.kind).toBe('jet');
    expect(resolveInspectionTarget({ kind: 'track', eventId: 7, vertexIndex: 0, trackIndex: 0 }, [event], geometry)?.kind).toBe('track');
    expect(resolveInspectionTarget({ kind: 'track', eventId: 7, vertexIndex: 0, trackIndex: 9 }, [event], geometry)).toBeNull();
  });

  it('keeps the jet OR branch threshold explicit', () => {
    expect(jetBranchPasses(cut, event.jets[0])).toBe(true);
    expect(jetBranchPasses(cut, { ...event.jets[0], rank: 3 })).toBeNull();
  });

  it('derives track pT/|q| without coercing a neutral charge', () => {
    expect(trackPtOverChargeGeV(event.vertices[0].tracks[0])).toBe(5);
    expect(trackPtOverChargeGeV({ ...event.vertices[0].tracks[0], charge: 0 })).toBeNull();
  });

  it('provides deterministic radial scales and stable target keys', () => {
    expect(radialTickValues(50)).toEqual([0, 10, 20, 30, 40, 50]);
    expect(radialTickValues(4)).toEqual([0, 1, 2, 3, 4]);
    expect(radialTickValues(330)).toEqual([0, 50, 100, 150, 200, 250, 300]);
    const target: InspectionTarget = { kind: 'track', eventId: 7, vertexIndex: 0, trackIndex: 3 };
    expect(targetKey(target)).toBe('track:7:0:3');
  });
});
