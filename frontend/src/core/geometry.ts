import type { EventTrack } from '../data/schema';

/** Exact proxy used by recast_2301_13866.cc (including its |Δφ|>π folding). */
export function recastD0Mm(track: Pick<EventTrack, 'x_prod_mm' | 'y_prod_mm' | 'px_GeV' | 'py_GeV'>): number {
  const r = Math.hypot(track.x_prod_mm, track.y_prod_mm);
  const phiProd = Math.atan2(track.y_prod_mm, track.x_prod_mm);
  const phiTrack = Math.atan2(track.py_GeV, track.px_GeV);
  let deltaPhi = phiProd - phiTrack;
  if (Math.abs(deltaPhi) > Math.PI) deltaPhi = 2 * Math.PI - Math.abs(deltaPhi);
  return r * Math.sin(deltaPhi);
}

/** Closest point to the beamline origin on the straight transverse truth direction. */
export function transverseClosestApproach(track: Pick<EventTrack, 'x_prod_mm' | 'y_prod_mm' | 'px_GeV' | 'py_GeV'>): { x: number; y: number } {
  const norm = Math.hypot(track.px_GeV, track.py_GeV);
  if (norm === 0) return { x: track.x_prod_mm, y: track.y_prod_mm };
  const ux = track.px_GeV / norm;
  const uy = track.py_GeV / norm;
  const projection = track.x_prod_mm * ux + track.y_prod_mm * uy;
  return { x: track.x_prod_mm - projection * ux, y: track.y_prod_mm - projection * uy };
}

export function directionEndpoint3d(
  origin: { x: number; y: number; z: number },
  momentum: { px: number; py: number; pz: number },
  lengthMm: number,
): { x: number; y: number; z: number } {
  const norm = Math.hypot(momentum.px, momentum.py, momentum.pz);
  if (norm === 0) return origin;
  return {
    x: origin.x + lengthMm * momentum.px / norm,
    y: origin.y + lengthMm * momentum.py / norm,
    z: origin.z + lengthMm * momentum.pz / norm,
  };
}
