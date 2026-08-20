<script lang="ts">
  import type { DatasetCatalogEntry } from '../data/loader';
  import type { JetLogicThresholdScale } from '../data/schema';
  import { t, type Language } from '../i18n';

  export let catalog: DatasetCatalogEntry[];
  export let datasetId: string;
  export let language: Language;
  export let onDataset: (datasetId: string) => void;
  export let onLanguage: (language: Language) => void;
  // Generic diagnostic jet-threshold scale control. Enabled purely from
  // dataset metadata (jet_logic.threshold_scale.supported) — never from
  // dataset_id or source_kind (Step 1E/2C).
  export let thresholdScale: JetLogicThresholdScale | undefined = undefined;
  export let scale = 1;
  export let onScale: (value: number) => void = () => {};
</script>

<nav class="dataset-toolbar" aria-label={t(language, 'datasetLabel')}>
  <label>
    <span>{t(language, 'datasetLabel')}</span>
    <select value={datasetId} on:change={(event) => onDataset(event.currentTarget.value)}>
      {#each catalog as entry}
        <option value={entry.dataset_id}>{entry.labels[language]}</option>
      {/each}
    </select>
  </label>
  <label class="scale-control" class:disabled={!thresholdScale?.supported}>
    <span>{thresholdScale?.parameter_symbol ?? 's'}</span>
    {#if thresholdScale?.supported}
      <select value={scale} on:change={(event) => onScale(Number(event.currentTarget.value))}>
        {#each thresholdScale.values as value}
          <option value={value}>{value.toFixed(1)}</option>
        {/each}
      </select>
    {:else}
      <select disabled><option>{t(language, 'notApplicableShort')}</option></select>
    {/if}
  </label>
  <div class="language-toggle" aria-label="Idioma / Language">
    <button class:active={language === 'es'} aria-pressed={language === 'es'} on:click={() => onLanguage('es')}>ES</button>
    <button class:active={language === 'en'} aria-pressed={language === 'en'} on:click={() => onLanguage('en')}>EN</button>
  </div>
</nav>
{#each catalog.filter((entry) => entry.dataset_id === datasetId) as current}
  <p class="dataset-description">{current.description[language]}</p>
{/each}

<style>
  .scale-control { display: inline-flex; align-items: center; gap: .38rem; font-size: .79rem; color: #36464e; }
  .scale-control.disabled { opacity: .55; }
</style>
