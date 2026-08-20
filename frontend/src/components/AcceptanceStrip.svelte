<script lang="ts">
  import type { CutDefinition, CutflowStage, Summary } from '../data/schema';
  import { t, type Language } from '../i18n';

  export let summary: Summary;
  export let selectedCut: CutDefinition;
  export let selectedStage: CutflowStage;
  export let language: Language;
  export let currentBooleanAcceptance: number | null = null;
  // Present only when the interactive/display event pack is a bounded
  // subsample of a larger statistics-scope population (Step 3E): the
  // authoritative summary above always uses the full population, but
  // currentBooleanAcceptance is necessarily computed over whatever events.json
  // serializes. Both numbers come straight from manifest metadata — no
  // source-specific branch decides whether this note renders.
  export let displayEventCount: number | null = null;
  export let statisticsEventCount: number | null = null;
  // Present only when manifest.geometry_pack exists (a curated subset with
  // real DV/track/jet geometry recovered by telemetry replay). Never an
  // unbiased sample of the statistics population — see DATA_CONTRACT.md.
  export let geometryPackCount: number | null = null;

  $: finalStage = summary.cutflow.stages.at(-1)!;
  $: selectedLabel = selectedCut.kind === 'response_weight' ? t(language, 'responseWeightedYield') : t(language, 'cumulativeAcceptance');
  $: scopesDiffer = displayEventCount !== null && statisticsEventCount !== null && displayEventCount !== statisticsEventCount;
</script>

<aside class="acceptance-strip" aria-label={t(language, 'cumulativeAcceptance')}>
  <div>
    <span>{t(language, 'referenceAEff')}</span>
    <strong>{finalStage.cumulative_efficiency_pct.toFixed(2)}%</strong>
  </div>
  <div>
    <span>{currentBooleanAcceptance === null ? `${t(language, 'selectedStage')} · ${selectedLabel}` : t(language, 'booleanAcceptance')}</span>
    <strong>{(currentBooleanAcceptance ?? selectedStage.cumulative_efficiency_pct).toFixed(2)}%</strong>
    {#if scopesDiffer && currentBooleanAcceptance !== null}
      <small class="scope-note">{t(language, 'statisticsScope')}: {statisticsEventCount} · {t(language, 'displayScope')}: {displayEventCount}</small>
    {/if}
    {#if geometryPackCount !== null}
      <small class="scope-note" title={t(language, 'geometryPackTooltip')}>{t(language, 'geometryScope')}: {geometryPackCount}</small>
    {/if}
  </div>
  <div class="validation-mark">
    <span>{t(language, 'externalStatus')}</span>
    <strong>{summary.external_validation.status}</strong>
  </div>
</aside>

<style>
  .scope-note { display: block; margin-top: .2rem; font-size: .62rem; font-weight: 500; color: #7a8790; }
</style>
