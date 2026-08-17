import { describe, expect, it } from 'vitest';
import { stagePopulation } from './population';
import type { CutDefinition, CutflowStage } from '../data/schema';

const cut = { kind: 'atomic_boolean' } as CutDefinition;
const response = { kind: 'response_weight' } as CutDefinition;
const stage = { n_before: 100, n_after: 30 } as CutflowStage;

describe('stage population semantics', () => {
  it('labels boolean losses as removed populations', () => {
    expect(stagePopulation(stage, cut)).toEqual({
      before: 100,
      after: 30,
      reduction: 70,
      reductionFraction: 0.7,
      reductionLabel: 'removed by this boolean stage',
    });
  });

  it('does not call response weighting an event cut', () => {
    expect(stagePopulation(stage, response).reductionLabel).toBe('response-weight reduction');
  });
});
