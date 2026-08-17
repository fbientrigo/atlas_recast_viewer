<script lang="ts">
  import type { CutDefinition, CutflowStage, Summary } from '../data/schema';
  import { t, type Language } from '../i18n';

  export let summary: Summary;
  export let selectedCut: CutDefinition;
  export let selectedStage: CutflowStage;
  export let language: Language;
  export let currentBooleanAcceptance: number | null = null;

  $: finalStage = summary.cutflow.stages.at(-1)!;
  $: selectedLabel = selectedCut.kind === 'response_weight' ? t(language, 'responseWeightedYield') : t(language, 'cumulativeAcceptance');
</script>

<aside class="acceptance-strip" aria-label={t(language, 'cumulativeAcceptance')}>
  <div>
    <span>{t(language, 'referenceAEff')}</span>
    <strong>{finalStage.cumulative_efficiency_pct.toFixed(2)}%</strong>
  </div>
  <div>
    <span>{currentBooleanAcceptance === null ? `${t(language, 'selectedStage')} · ${selectedLabel}` : t(language, 'booleanAcceptance')}</span>
    <strong>{(currentBooleanAcceptance ?? selectedStage.cumulative_efficiency_pct).toFixed(2)}%</strong>
  </div>
  <div class="validation-mark">
    <span>{t(language, 'externalStatus')}</span>
    <strong>{summary.external_validation.status}</strong>
  </div>
</aside>
