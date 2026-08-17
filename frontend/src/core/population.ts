import type { CutDefinition, CutflowStage } from '../data/schema';

export interface StagePopulation {
  before: number;
  after: number;
  reduction: number;
  reductionFraction: number | null;
  reductionLabel: 'removed by this boolean stage' | 'response-weight reduction';
}

export function stagePopulation(stage: CutflowStage, cut: CutDefinition): StagePopulation {
  const reduction = stage.n_before - stage.n_after;
  return {
    before: stage.n_before,
    after: stage.n_after,
    reduction,
    reductionFraction: stage.n_before === 0 ? null : reduction / stage.n_before,
    reductionLabel: cut.kind === 'response_weight'
      ? 'response-weight reduction'
      : 'removed by this boolean stage',
  };
}
