<script lang="ts">
  import type { CutDefinition, CutflowStage } from '../data/schema';
  import { stagePopulation } from '../core/population';
  import { t, type Language } from '../i18n';

  export let cut: CutDefinition;
  export let stage: CutflowStage;
  export let language: Language;
  export let eventLevel = false;

  $: population = stagePopulation(stage, cut);
  $: afterPercent = population.before === 0 ? 0 : (population.after / population.before) * 100;
  $: reductionPercent = 100 - afterPercent;
  $: formatYield = (value: number) => value.toLocaleString(language, { maximumFractionDigits: 3 });
</script>

<section class="population-view" aria-labelledby="population-heading">
  <div class="panel-title">
    <div><p class="eyebrow">{t(language, 'populationBridge')}</p><h3 id="population-heading">{t(language, 'whatChanges')}</h3></div>
    <span class:response={cut.kind === 'response_weight'}>{population.reductionFraction === null ? '—' : `${(population.reductionFraction * 100).toFixed(2)}%`}</span>
  </div>

  <div class="population-bar" aria-label={`${afterPercent.toFixed(2)} percent remains after this stage`}>
    <div class="survives" style={`width: ${afterPercent}%`}></div>
    <div class:response={cut.kind === 'response_weight'} class="removed" style={`width: ${reductionPercent}%`}></div>
  </div>
  <div class="population-key">
    <div><i class="before"></i><span>{t(language, 'before')}</span><strong>{formatYield(population.before)}</strong></div>
    <div><i class="after"></i><span>{t(language, 'after')}</span><strong>{formatYield(population.after)}</strong></div>
    <div><i class:response={cut.kind === 'response_weight'} class="loss"></i><span>{cut.kind === 'response_weight' ? t(language, 'responseReduction') : t(language, 'removedByCut')}</span><strong>{formatYield(population.reduction)}</strong></div>
  </div>
  {#if cut.kind === 'response_weight'}
    <p class="semantic-note">{t(language, 'responseNote')}</p>
  {:else if eventLevel}
    <p class="semantic-note">{t(language, 'eventPopulationNote')}</p>
  {:else}
    <p class="semantic-note">{t(language, 'aggregatePopulationNote')}</p>
  {/if}
</section>
