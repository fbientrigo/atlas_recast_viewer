<script lang="ts">
  import type { Manifest } from '../data/schema';
  import { manifestText, t, type Language } from '../i18n';

  export let manifest: Manifest;
  export let language: Language;

  $: labels = {
    cutflow: language === 'es' ? 'Cutflow' : 'Cutflow',
    atomic_event_cuts: language === 'es' ? 'Cortes atómicos por evento' : 'Atomic event cuts',
    jet_observables: language === 'es' ? 'Observables de jets' : 'Jet observables',
    jet_what_if: language === 'es' ? 'Contrafactual de jets' : 'Jet what-if',
    dv_radial: language === 'es' ? 'Radio del DV' : 'DV radius',
    dv_xyz: 'DV x/y/z',
    response_weights: language === 'es' ? 'Respuesta por evento' : 'Per-event response',
  };
  $: copy = manifestText(manifest, language);
</script>

<header class="dataset-header">
  <div class="dataset-title">
    <div><p class="eyebrow">{t(language, 'referenceDataset')} · {manifest.schema_version}</p><h1>{copy.title}</h1></div>
    <span class:dirty={manifest.source_dirty} class="source-state">{manifest.source_dirty ? t(language, 'dirtySource') : t(language, 'frozenClean')}</span>
  </div>
  <p class="lede">{copy.reference_sample}</p>

  <dl class="identity-line">
    <div><dt>{t(language, 'source')}</dt><dd>{manifest.source_kind}</dd></div>
    <div><dt>{t(language, 'commit')}</dt><dd><code>{manifest.source_commit.slice(0, 24)}</code></dd></div>
    <div><dt>{t(language, 'generated')}</dt><dd>{manifest.n_events?.toLocaleString(language) ?? t(language, 'unavailable')}</dd></div>
  </dl>

  <details class="capability-details">
    <summary>{t(language, 'capabilities')}</summary>
    <div class="capabilities" aria-label="Dataset capabilities">
      {#each Object.entries(manifest.capabilities) as [name, available]}
        <span class:available class:unavailable={!available}>{labels[name] ?? name}: {available ? t(language, 'available') : t(language, 'unavailableCaps')}</span>
      {/each}
    </div>
  </details>
</header>
