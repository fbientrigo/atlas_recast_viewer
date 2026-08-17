<script lang="ts">
  import type { DatasetCatalogEntry } from '../data/loader';
  import { t, type Language } from '../i18n';

  export let catalog: DatasetCatalogEntry[];
  export let datasetId: string;
  export let language: Language;
  export let onDataset: (datasetId: string) => void;
  export let onLanguage: (language: Language) => void;
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
  <div class="language-toggle" aria-label="Idioma / Language">
    <button class:active={language === 'es'} aria-pressed={language === 'es'} on:click={() => onLanguage('es')}>ES</button>
    <button class:active={language === 'en'} aria-pressed={language === 'en'} on:click={() => onLanguage('en')}>EN</button>
  </div>
</nav>
{#each catalog.filter((entry) => entry.dataset_id === datasetId) as current}
  <p class="dataset-description">{current.description[language]}</p>
{/each}
