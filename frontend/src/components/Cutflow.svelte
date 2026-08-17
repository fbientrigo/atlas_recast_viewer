<script lang="ts">
  import type { CutDefinition, CutflowStage } from '../data/schema';
  import { categoryLabel, cutText, t, type Language } from '../i18n';

  export let stages: CutflowStage[];
  export let cuts: CutDefinition[];
  export let selectedCutId: string;
  export let diagnosticAvailable: boolean;
  export let diagnosticReason: string | undefined;
  export let disabledCuts = new Set<string>();
  export let onSelect: (cut: CutDefinition) => void;
  export let onToggle: (cut: CutDefinition) => void;
  export let language: Language;

  $: denominator = stages[0]?.n_before ?? 1;
  $: formatYield = (value: number) => value.toLocaleString(language, { maximumFractionDigits: 2 });
</script>

<div class="cutflow-list" aria-label={t(language, 'cutsAndResponse')}>
  {#each stages as stage, index}
    {@const cut = cuts[index]}
    {@const copy = cutText(cut, language)}
    <article class:selected={selectedCutId === cut.id} class:response={cut.kind === 'response_weight'} class:disabled-cut={disabledCuts.has(cut.id)} class="cut-row">
      <button class="stage-select" on:click={() => onSelect(cut)} aria-pressed={selectedCutId === cut.id}>
        <span class="stage-number">{String(cut.order).padStart(2, '0')}</span>
        <span class="stage-copy"><strong>{copy.name}</strong><small>{categoryLabel(cut.category, language)}</small></span>
        <span class="stage-yield">
          <strong>{formatYield(stage.n_after)}</strong>
          <small>{stage.cumulative_efficiency_pct.toFixed(2)}% · {stage.conditional_loss === null ? t(language, 'lossNA') : `${(stage.conditional_loss * 100).toFixed(2)}% ${cut.kind === 'response_weight' ? t(language, 'response') : t(language, 'lost')}`}</small>
        </span>
      </button>
      <label class="row-toggle" title={diagnosticReason}>
        <input
          type="checkbox"
          checked={!disabledCuts.has(cut.id)}
          disabled={!diagnosticAvailable || cut.kind === 'response_weight'}
          on:change={() => onToggle(cut)}
        />
        <span>{cut.kind === 'response_weight' ? t(language, 'weight') : diagnosticAvailable ? (disabledCuts.has(cut.id) ? t(language, 'off') : t(language, 'on')) : t(language, 'locked')}</span>
      </label>
      <div class="yield-track"><span style={`width: ${(stage.n_after / denominator) * 100}%`}></span></div>
    </article>
  {/each}
</div>
