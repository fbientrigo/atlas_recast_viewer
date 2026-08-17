<script lang="ts">
  import { onMount } from 'svelte';
  import DatasetToolbar from './components/DatasetToolbar.svelte';
  import DatasetHeader from './components/DatasetHeader.svelte';
  import AcceptanceStrip from './components/AcceptanceStrip.svelte';
  import Cutflow from './components/Cutflow.svelte';
  import CutInspector from './components/CutInspector.svelte';
  import GeometryViewer from './components/GeometryViewer.svelte';
  import JetExplorer from './components/JetExplorer.svelte';
  import PopulationView from './components/PopulationView.svelte';
  import { loadDataset, loadDatasetCatalog, loadDetectorGeometry, type DatasetCatalogEntry, type LoadState } from './data/loader';
  import type { CutDefinition, CutflowStage, DetectorGeometry } from './data/schema';
  import { booleanAcceptance, diagnosticAvailability, recomputeEventCutflow } from './core/selection';
  import { t, validationText, type Language } from './i18n';

  let language: Language = 'es';
  let datasetId = 'local-reference';
  let catalog: DatasetCatalogEntry[] = [];
  let state: LoadState = { status: 'loading', datasetId };
  let selectedCut: CutDefinition | null = null;
  let disabledCuts = new Set<string>();
  let detectorGeometry: DetectorGeometry | null = null;

  $: diagnostic = state.status === 'valid'
    ? diagnosticAvailability(state.dataset.manifest.capabilities, Boolean(state.dataset.events))
    : null;
  $: diagnosticReason = state.status === 'valid' && state.dataset.manifest.capabilities.atomic_event_cuts
    ? t(language, 'eventPackMissing') : t(language, 'aggregateReason');
  $: selectedIndex = state.status === 'valid' && selectedCut
    ? state.dataset.cuts.cuts.findIndex((cut) => cut.id === selectedCut?.id) : 0;
  $: interactiveFlow = state.status === 'valid' && state.dataset.events
    ? recomputeEventCutflow(state.dataset.events.events, state.dataset.cuts.cuts, disabledCuts) : null;
  $: displayStages = state.status === 'valid'
    ? state.dataset.summary.cutflow.stages.map((stage, index): CutflowStage => {
        const recomputed = interactiveFlow?.find((candidate) => candidate.cutId === stage.cut_id);
        if (!recomputed) return stage;
        const denominator = state.status === 'valid' ? state.dataset.summary.cutflow.denominator.weighted_events : 0;
        return {
          ...stage,
          n_before: recomputed.weightedBefore,
          n_after: recomputed.weightedAfter,
          conditional_loss: recomputed.weightedBefore === 0 ? null : (recomputed.weightedBefore - recomputed.weightedAfter) / recomputed.weightedBefore,
          cumulative_efficiency_pct: denominator === 0 ? 0 : 100 * recomputed.weightedAfter / denominator,
        };
      }) : [];
  $: currentAcceptance = state.status === 'valid' && state.dataset.events
    ? booleanAcceptance(state.dataset.events.events, state.dataset.cuts.cuts, disabledCuts).efficiencyPct : null;

  function toggleCut(cut: CutDefinition): void {
    if (!diagnostic?.available || cut.kind === 'response_weight') return;
    const next = new Set(disabledCuts);
    if (next.has(cut.id)) next.delete(cut.id); else next.add(cut.id);
    disabledCuts = next;
  }

  async function selectDataset(nextId: string): Promise<void> {
    datasetId = nextId;
    state = { status: 'loading', datasetId };
    selectedCut = null;
    disabledCuts = new Set();
    state = await loadDataset(datasetId);
    if (state.status === 'valid') {
      selectedCut = state.dataset.events
        ? state.dataset.cuts.cuts.find((cut) => cut.id === 'rxy_gt_4_mm') ?? state.dataset.cuts.cuts[0]
        : state.dataset.cuts.cuts.find((cut) => cut.geometry_overlay) ?? state.dataset.cuts.cuts[0];
    }
  }

  function selectLanguage(nextLanguage: Language): void {
    language = nextLanguage;
    localStorage.setItem('recast-viewer-language', language);
    document.documentElement.lang = language;
  }

  onMount(async () => {
    const savedLanguage = localStorage.getItem('recast-viewer-language');
    if (savedLanguage === 'es' || savedLanguage === 'en') language = savedLanguage;
    document.documentElement.lang = language;
    [catalog, detectorGeometry] = await Promise.all([loadDatasetCatalog(), loadDetectorGeometry()]);
    await selectDataset(datasetId);
  });
</script>

<svelte:head><title>{t(language, 'appTitle')}</title></svelte:head>

<main>
  <DatasetToolbar {catalog} {datasetId} {language} onDataset={selectDataset} onLanguage={selectLanguage} />
  {#if state.status === 'loading'}
    <div class="state-panel"><h1>{t(language, 'loading')}</h1><p>{t(language, 'validating')}</p></div>
  {:else if state.status !== 'valid'}
    <div class="state-panel error">
      <p class="eyebrow">{state.status.replaceAll('_', ' ')}</p>
      <h1>{t(language, 'loadError')}</h1>
      <dl>
        <div><dt>{t(language, 'dataset')}</dt><dd>{state.error.dataset}</dd></div>
        <div><dt>{t(language, 'file')}</dt><dd>{state.error.file}</dd></div>
        <div><dt>{t(language, 'field')}</dt><dd>{state.error.field}</dd></div>
        <div><dt>{t(language, 'expected')}</dt><dd>{state.error.expected}</dd></div>
        <div><dt>{t(language, 'received')}</dt><dd><code>{JSON.stringify(state.error.received)}</code></dd></div>
      </dl>
    </div>
  {:else}
    {@const dataset = state.dataset}
    <DatasetHeader manifest={dataset.manifest} {language} />

    {#if selectedCut}
      {@const selectedStage = displayStages[selectedIndex]}
      <AcceptanceStrip summary={dataset.summary} {selectedCut} {selectedStage} {language} currentBooleanAcceptance={currentAcceptance} />

      {#if disabledCuts.size > 0}<div class="diagnostic-banner">{t(language, 'diagnosticBanner')}</div>{/if}

      <div class="explorer-grid">
        <section class="analysis-panel" aria-labelledby="analysis-flow">
          <div class="panel-title">
            <div><p class="eyebrow">{t(language, 'analysisPanel')}</p><h2 id="analysis-flow">{t(language, 'cutsAndResponse')}</h2></div>
            <span class="count-semantics">{t(language, 'weightedYields')}</span>
          </div>
          <Cutflow
            stages={displayStages}
            cuts={dataset.cuts.cuts}
            selectedCutId={selectedCut.id}
            diagnosticAvailable={diagnostic?.available ?? false}
            diagnosticReason={diagnosticReason}
            {disabledCuts}
            {language}
            onSelect={(cut) => selectedCut = cut}
            onToggle={toggleCut}
          />
          <CutInspector cut={selectedCut} {language} />

          {#if selectedCut.id === 'jet_selection' && dataset.cuts.jet_logic}
            <details class="jet-details" open>
              <summary>{t(language, 'jetLogic')}</summary>
              <JetExplorer logic={dataset.cuts.jet_logic} capabilities={dataset.manifest.capabilities} events={dataset.events?.events} {language} />
            </details>
          {/if}

          {#if diagnostic && !diagnostic.available}
            <div class="unavailable-panel compact">
              <strong>{t(language, 'cutOnOffUnavailable')}</strong>
              <p>{diagnosticReason}</p>
            </div>
          {:else if disabledCuts.size > 0}
            <div class="diagnostic-note">{t(language, 'publishedResponseFixed')}</div>
          {/if}
        </section>

        <aside class="visual-panel" aria-label={t(language, 'geometryMode')}>
          <GeometryViewer cut={selectedCut} cuts={dataset.cuts.cuts} capabilities={dataset.manifest.capabilities} events={dataset.events?.events} {detectorGeometry} {disabledCuts} {language} />
          <PopulationView cut={selectedCut} stage={selectedStage} {language} eventLevel={Boolean(dataset.events)} />
        </aside>
      </div>
    {/if}

    {@const validation = validationText(dataset.summary, language)}
    <footer class="page-footer">
      <p><strong>{t(language, 'validation')}:</strong> {dataset.summary.external_validation.status} · {validation.scope}</p>
      <p>{validation.note}</p>
    </footer>
  {/if}
</main>
