import { describe, expect, it } from 'vitest';
import { recastD0Mm, transverseClosestApproach } from './geometry';

describe('recast d0 geometry', () => {
  it('reproduces r_prod sin(phi_prod - phi_track)', () => {
    const track = { x_prod_mm: 3, y_prod_mm: 4, px_GeV: 1, py_GeV: 0 };
    expect(recastD0Mm(track)).toBeCloseTo(4, 12);
    expect(Math.hypot(...Object.values(transverseClosestApproach(track)))).toBeCloseTo(Math.abs(recastD0Mm(track)), 12);
  });

  it('preserves the recast folding across the phi boundary', () => {
    const track = { x_prod_mm: -1, y_prod_mm: -0.01, px_GeV: -1, py_GeV: 0.01 };
    const value = recastD0Mm(track);
    expect(Number.isFinite(value)).toBe(true);
    expect(Math.abs(value)).toBeLessThan(0.03);
  });
});
