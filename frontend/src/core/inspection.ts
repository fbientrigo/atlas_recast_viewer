import type {
  CutDefinition,
  DetectorGeometry,
  EventJet,
  EventRecord,
  EventTrack,
  EventVertex,
  GeometryLandmark,
} from '../data/schema';

export type InspectionTarget =
  | { kind: 'layer'; landmarkId: string }
  | { kind: 'vertex'; eventId: number; vertexIndex: number }
  | { kind: 'track'; eventId: number; vertexIndex: number; trackIndex: number }
  | { kind: 'jet'; eventId: number; jetRank: number };

export type ResolvedInspection =
  | { kind: 'layer'; landmark: GeometryLandmark }
  | { kind: 'vertex'; event: EventRecord; vertex: EventVertex; vertexIndex: number }
  | { kind: 'track'; event: EventRecord; vertex: EventVertex; vertexIndex: number; track: EventTrack; trackIndex: number }
  | { kind: 'jet'; event: EventRecord; jet: EventJet };

export function resolveInspectionTarget(
  target: InspectionTarget | null,
  events: EventRecord[],
  geometry: DetectorGeometry,
): ResolvedInspection | null {
  if (!target) return null;
  if (target.kind === 'layer') {
    const landmark = geometry.landmarks.find((item) => item.id === target.landmarkId);
    return landmark ? { kind: 'layer', landmark } : null;
  }
  const event = events.find((item) => item.event_id === target.eventId);
  if (!event) return null;
  if (target.kind === 'jet') {
    const jet = event.jets.find((item) => item.rank === target.jetRank);
    return jet ? { kind: 'jet', event, jet } : null;
  }
  const vertex = event.vertices[target.vertexIndex];
  if (!vertex) return null;
  if (target.kind === 'vertex') return { kind: 'vertex', event, vertex, vertexIndex: target.vertexIndex };
  const track = vertex.tracks[target.trackIndex];
  return track ? { kind: 'track', event, vertex, vertexIndex: target.vertexIndex, track, trackIndex: target.trackIndex } : null;
}

export function jetThresholdGeV(cut: CutDefinition, rank: number): number | null {
  const value = cut.parameters?.[`highpt_j${rank}_pt_GeV`];
  return typeof value === 'number' ? value : null;
}

export function jetBranchPasses(cut: CutDefinition, jet: EventJet): boolean | null {
  const threshold = jetThresholdGeV(cut, jet.rank);
  return threshold === null ? null : jet.pt_GeV > threshold;
}

export function trackPtOverChargeGeV(track: EventTrack): number | null {
  const charge = Math.abs(track.charge);
  return charge === 0 ? null : Math.hypot(track.px_GeV, track.py_GeV) / charge;
}

/** Numeric R ticks for the two display scales; special cut values remain separate annotations. */
export function radialTickValues(extentMm: number): number[] {
  if (extentMm <= 10) {
    const step = extentMm <= 5 ? 1 : 2;
    return Array.from({ length: Math.floor(extentMm / step) + 1 }, (_, index) => index * step);
  }
  if (extentMm <= 60) return [0, 10, 20, 30, 40, 50].filter((value) => value <= extentMm);
  return [0, 50, 100, 150, 200, 250, 300].filter((value) => value <= extentMm);
}

export function targetKey(target: InspectionTarget | null): string {
  if (!target) return '';
  if (target.kind === 'layer') return `layer:${target.landmarkId}`;
  if (target.kind === 'jet') return `jet:${target.eventId}:${target.jetRank}`;
  if (target.kind === 'track') return `track:${target.eventId}:${target.vertexIndex}:${target.trackIndex}`;
  return `vertex:${target.eventId}:${target.vertexIndex}`;
}
