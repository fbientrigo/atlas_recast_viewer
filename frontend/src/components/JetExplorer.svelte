<script lang="ts">
  import type { Capabilities, EventRecord, JetLogic } from '../data/schema';
  import { jetExplorerAvailability, jetSelectionPasses } from '../core/selection';
  import { t, type Language } from '../i18n';

  export let logic: JetLogic;
  export let capabilities: Capabilities;
  export let events: EventRecord[] | undefined;
  export let language: Language;
  // Baseline (s=1) unless the toolbar's diagnostic scale control is engaged
  // and this dataset declares threshold_scale.supported.
  export let scale = 1;

  $: availability = jetExplorerAvailability(capabilities);
  $: scaleSupported = Boolean(logic.threshold_scale?.supported);
  $: effectiveScale = scaleSupported ? scale : 1;
  const passesBranch = (event: EventRecord, rank: number, effectiveThreshold: number) => {
    const jet = event.jets.find((candidate) => candidate.rank === rank);
    return jet !== undefined && jet.pt_GeV > effectiveThreshold;
  };
  $: fullPassed = events ? events.filter((event) => jetSelectionPasses(event, logic, effectiveScale)).length : 0;
</script>

<div class="jet-logic">
  <div class="logic-equation">
    {#each logic.branches as branch, index}
      <span>j{branch.jet_rank} pT {branch.comparison} {(branch.threshold_GeV * effectiveScale).toFixed(1)} GeV{#if scaleSupported && effectiveScale !== 1}<em> ({branch.threshold_GeV} × {effectiveScale.toFixed(1)})</em>{/if}</span>
      {#if index < logic.branches.length - 1}<b>{t(language, 'or')}</b>{/if}
    {/each}
    {#if logic.additional_requirement?.supported}
      <b>{t(language, 'and')}</b><span class="additional-leg">{t(language, 'additionalLeg')}</span>
    {/if}
  </div>
  <p>{language === 'es' ? 'j4 corresponde a jets[3]; los jets están ordenados por pT reconstruido decreciente. Si un rango no existe, esa rama es falsa.' : `${logic.rank_indexing}. ${logic.missing_jet_semantics}`}</p>

  {#if scaleSupported && effectiveScale !== logic.threshold_scale?.baseline}
    <div class="scale-diagnostic">{t(language, 'scaleDiagnosticBanner')}</div>
  {/if}

  {#if events}
    <div class="branch-fractions">
      {#each logic.branches as branch}
        {@const effectiveThreshold = branch.threshold_GeV * effectiveScale}
        {@const passed = events.filter((event) => passesBranch(event, branch.jet_rank, effectiveThreshold)).length}
        <span><strong>j{branch.jet_rank}</strong> {((100 * passed) / events.length).toFixed(1)}%</span>
      {/each}
      {#if logic.additional_requirement?.supported}
        {@const additionalId = logic.additional_requirement.predicate_id}
        {@const additionalPassed = events.filter((event) => event.predicates[additionalId] === true).length}
        <span><strong>{t(language, 'additionalLeg')}</strong> {((100 * additionalPassed) / events.length).toFixed(1)}%</span>
      {/if}
      <span class="full-decision"><strong>{t(language, 'ordinaryOr')} ∧ {logic.additional_requirement?.supported ? t(language, 'additionalLeg') : t(language, 'ordinaryOr')}</strong> {((100 * fullPassed) / events.length).toFixed(1)}%</span>
    </div>
  {/if}

  {#if !availability.available}
    <div class="unavailable-panel">
      <strong>{t(language, 'richerJetUnavailable')}</strong>
      <p>{t(language, 'jetMissing')} {language === 'en' ? logic.event_level_note : ''}</p>
    </div>
  {/if}
</div>

<style>
  .additional-leg { font-style: italic; }
  .scale-diagnostic { margin: .5rem 0; padding: .4rem .6rem; border-radius: 6px; background: #fdeee8; color: #9a3412; font-size: .74rem; font-weight: 650; }
  .full-decision { font-weight: 650; }
  em { font-style: normal; color: #7a8790; font-size: .82em; margin-left: .2em; }
</style>
