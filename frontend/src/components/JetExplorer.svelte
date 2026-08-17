<script lang="ts">
  import type { Capabilities, EventRecord, JetLogic } from '../data/schema';
  import { jetExplorerAvailability } from '../core/selection';
  import { t, type Language } from '../i18n';

  export let logic: JetLogic;
  export let capabilities: Capabilities;
  export let events: EventRecord[] | undefined;
  export let language: Language;

  $: availability = jetExplorerAvailability(capabilities);
  const passesBranch = (event: EventRecord, rank: number, threshold: number) => {
    const jet = event.jets.find((candidate) => candidate.rank === rank);
    return jet !== undefined && jet.pt_GeV > threshold;
  };
</script>

<div class="jet-logic">
  <div class="logic-equation">
    {#each logic.branches as branch, index}
      <span>j{branch.jet_rank} pT {branch.comparison} {branch.threshold_GeV} GeV</span>
      {#if index < logic.branches.length - 1}<b>{t(language, 'or')}</b>{/if}
    {/each}
  </div>
  <p>{language === 'es' ? 'j4 corresponde a jets[3]; los jets están ordenados por pT reconstruido decreciente. Si un rango no existe, esa rama es falsa.' : `${logic.rank_indexing}. ${logic.missing_jet_semantics}`}</p>

  {#if events}
    <div class="branch-fractions">
      {#each logic.branches as branch}
        {@const passed = events.filter((event) => passesBranch(event, branch.jet_rank, branch.threshold_GeV)).length}
        <span><strong>j{branch.jet_rank}</strong> {((100 * passed) / events.length).toFixed(1)}%</span>
      {/each}
    </div>
  {/if}

  {#if !availability.available}
    <div class="unavailable-panel">
      <strong>{t(language, 'richerJetUnavailable')}</strong>
      <p>{t(language, 'jetMissing')} {language === 'en' ? logic.event_level_note : ''}</p>
    </div>
  {/if}
</div>
