<script lang="ts">
  import type { CutDefinition } from '../data/schema';
  import type { Language } from '../i18n';
  import { cutText } from '../i18n';
  import { eventPassesSelectedCut, firstFailedCut } from '../core/cohorts';
  import { eventPassesCuts } from '../core/selection';
  import {
    jetBranchPasses,
    jetThresholdGeV,
    trackPtOverChargeGeV,
    type ResolvedInspection,
  } from '../core/inspection';

  export let inspected: ResolvedInspection | null;
  export let cut: CutDefinition;
  export let cuts: CutDefinition[];
  export let disabledCuts: Set<string>;
  export let language: Language;

  const copy = {
    es: {
      title: 'Inspector físico', selected: 'Objeto seleccionado', layer: 'Capa / límite', vertex: 'Vértice desplazado', track: 'Hija cargada', jet: 'Jet',
      type: 'Tipo', hardware: 'Hardware ATLAS', boundary: 'Límite del análisis', response: 'Bin de respuesta', radius: 'Radio', zExtent: 'Extensión longitudinal', relevance: 'Por qué importa', provenance: 'Procedencia',
      event: 'Evento', vertexIndex: 'Vértice', trackIndex: 'Traza', weight: 'Peso', currentDecision: 'Decisión del corte actual', fullDecision: 'Selección booleana completa', firstFailed: 'Primer corte fallado', none: 'ninguno',
      pass: 'PASA', fail: 'FALLA', notApplicable: 'NO APLICA', selectedTracks: 'Trazas seleccionadas para el DV', impactedTracks: 'Trazas con |d0| > umbral', mass: 'Masa del DV', vertexEfficiency: 'Eficiencia de vértice',
      currentConnection: 'Relación con el corte seleccionado', vertexConnection: 'La decisión del evento usa este DV si satisface conjuntamente todos los cortes de vértice habilitados.',
      trackConnection: 'Esta hija cargada aporta al corte d0 mediante el proxy exacto y, de forma independiente, entra en Ntracks y mDV solo si selected_for_dv=true.',
      jetConnection: 'La rama de este rango se combina con las ramas j4/j5/j6/j7 mediante OR. El evento pasa si existe al menos una rama verdadera.',
      layerConnection: 'Esta referencia permite comparar la posición del DV con una escala física o con una frontera matemática; no convierte la vista en reconstrucción del detector.',
      exactD0: 'd0 serializado', d0Decision: 'Pasa |d0| > 2 mm', selectedForDv: 'Seleccionada para Ntracks y mDV', transverseDistance: 'βγτ transversal', ptOverCharge: 'pT/|q|',
      rank: 'Rango', jetCount: 'Multiplicidad de jets', threshold: 'Umbral', branch: 'Rama individual', eventOr: 'OR completo del evento', etaPhi: 'Dirección η, φ',
      passList: 'Lógica pasa/falla del evento', disabled: 'DESACTIVADO', responseWeight: 'PESO', sourceNote: 'Nota de fuente', otherName: 'Nombre alternativo', noObject: 'Seleccione una capa, un DV, una traza o un jet.',
    },
    en: {
      title: 'Physics inspector', selected: 'Selected object', layer: 'Layer / boundary', vertex: 'Displaced vertex', track: 'Charged daughter', jet: 'Jet',
      type: 'Type', hardware: 'ATLAS hardware', boundary: 'Analysis boundary', response: 'Response bin', radius: 'Radius', zExtent: 'Longitudinal extent', relevance: 'Why it matters', provenance: 'Provenance',
      event: 'Event', vertexIndex: 'Vertex', trackIndex: 'Track', weight: 'Weight', currentDecision: 'Current-cut decision', fullDecision: 'Full boolean selection', firstFailed: 'First failed cut', none: 'none',
      pass: 'PASS', fail: 'FAIL', notApplicable: 'N/A', selectedTracks: 'Tracks selected for the DV', impactedTracks: 'Tracks with |d0| above threshold', mass: 'DV mass', vertexEfficiency: 'Vertex efficiency',
      currentConnection: 'Connection to selected cut', vertexConnection: 'The event decision uses this DV when it jointly satisfies every enabled vertex cut.',
      trackConnection: 'This charged daughter contributes to the d0 cut through the exact proxy and, independently, enters Ntracks and mDV only when selected_for_dv=true.',
      jetConnection: 'This rank branch is OR-combined with j4/j5/j6/j7. The event passes when at least one branch is true.',
      layerConnection: 'This reference compares the DV position with physical scale or a mathematical boundary; it does not turn the view into detector reconstruction.',
      exactD0: 'Serialized d0', d0Decision: 'Passes |d0| > 2 mm', selectedForDv: 'Selected for Ntracks and mDV', transverseDistance: 'Transverse βγτ', ptOverCharge: 'pT/|q|',
      rank: 'Rank', jetCount: 'Jet multiplicity', threshold: 'Threshold', branch: 'Individual branch', eventOr: 'Full event OR', etaPhi: 'η, φ direction',
      passList: 'Event pass/fail logic', disabled: 'DISABLED', responseWeight: 'WEIGHT', sourceNote: 'Source note', otherName: 'Alternative name', noObject: 'Select a layer, DV, track, or jet.',
    },
  } as const;

  $: text = copy[language];
  $: event = inspected && inspected.kind !== 'layer' ? inspected.event : null;
  $: vertex = inspected && (inspected.kind === 'vertex' || inspected.kind === 'track') ? inspected.vertex : null;
  $: enabledCutIds = cuts.filter((item) => item.kind !== 'response_weight' && item.kind !== 'summary' && !disabledCuts.has(item.id)).map((item) => item.id);
  $: eventCurrentPass = event && cut.kind !== 'response_weight' && cut.kind !== 'summary' ? eventPassesSelectedCut(event, cut) : null;
  $: eventFullPass = event ? eventPassesCuts(event, enabledCutIds) : null;
  $: failedId = event ? firstFailedCut(event, cuts, disabledCuts) : null;
  $: failedCut = cuts.find((item) => item.id === failedId);
  $: jetCut = cuts.find((item) => item.id === 'jet_selection');
  $: d0Threshold = cuts.find((item) => item.id === 'd0_gt_2_mm')?.parameters?.track_abs_d0_min_mm ?? null;
  $: trackPtOverCharge = inspected?.kind === 'track' ? trackPtOverChargeGeV(inspected.track) : null;

  function yesNo(value: boolean, ui: typeof copy.es | typeof copy.en): string { return value ? ui.pass : ui.fail; }
  function layerType(kind: string, ui: typeof copy.es | typeof copy.en): string {
    if (kind === 'detector_hardware') return ui.hardware;
    if (kind === 'analysis_boundary') return ui.boundary;
    return ui.response;
  }
  function connectionFor(value: ResolvedInspection, currentCut: CutDefinition, currentD0Threshold: number | null, activeLanguage: Language, ui: typeof copy.es | typeof copy.en): string {
    const es = activeLanguage === 'es';
    if (value.kind === 'layer') {
      const matches = (currentCut.id === 'rxy_gt_4_mm' && value.landmark.id === 'dv_min_r')
        || (currentCut.id === 'fiducial_dv' && ['dv_max_r', 'dv_max_z'].includes(value.landmark.id));
      if (matches) return es
        ? 'Esta es una de las fronteras exactas del corte seleccionado; la posición del DV se compara directamente con ella.'
        : 'This is one of the selected cut’s exact boundaries; the DV position is compared directly with it.';
      return ui.layerConnection;
    }
    if (value.kind === 'vertex') return es
      ? `Para este DV, el predicado ${currentCut.id} es ${currentCut.kind === 'response_weight' ? 'una ponderación, no un booleano' : value.vertex.predicates[currentCut.id] === true ? 'verdadero' : value.vertex.predicates[currentCut.id] === false ? 'falso' : 'no aplicable al vértice'}. La decisión del evento exige un mismo DV que cumpla conjuntamente los cortes habilitados.`
      : `For this DV, predicate ${currentCut.id} is ${currentCut.kind === 'response_weight' ? 'a weight, not a boolean' : value.vertex.predicates[currentCut.id] === true ? 'true' : value.vertex.predicates[currentCut.id] === false ? 'false' : 'not vertex-applicable'}. The event decision requires one DV to jointly pass all enabled cuts.`;
    if (value.kind === 'track') {
      if (currentCut.id === 'd0_gt_2_mm') return es
        ? `Esta traza ${value.track.passes_d0 ? 'satisface' : 'no satisface'} |d0|>${currentD0Threshold ?? 2} mm. El DV pasa este corte si al menos una hija cargada lo satisface.`
        : `This track ${value.track.passes_d0 ? 'passes' : 'fails'} |d0|>${currentD0Threshold ?? 2} mm. The DV passes when at least one charged daughter passes.`;
      if (currentCut.id === 'tracks_ge_5') return es
        ? `selected_for_dv=${value.track.selected_for_dv}; por tanto ${value.track.selected_for_dv ? 'suma una unidad' : 'no suma'} a Ntracks.`
        : `selected_for_dv=${value.track.selected_for_dv}; it therefore ${value.track.selected_for_dv ? 'adds one' : 'does not add'} to Ntracks.`;
      if (currentCut.id === 'mdv_gt_10_gev') return es
        ? `selected_for_dv=${value.track.selected_for_dv}; ${value.track.selected_for_dv ? 'su cuatro-momento entra' : 'su cuatro-momento no entra'} en mDV bajo la hipótesis de masa de pión cargado.`
        : `selected_for_dv=${value.track.selected_for_dv}; its four-momentum ${value.track.selected_for_dv ? 'enters' : 'does not enter'} mDV under the charged-pion mass hypothesis.`;
      return ui.trackConnection;
    }
    return currentCut.id === 'jet_selection' ? ui.jetConnection : es
      ? 'La OR de jets es una preselección del evento. El corte de DV actualmente seleccionado se evalúa después y no cambia la dirección del jet.'
      : 'The jet OR is an event preselection. The currently selected DV cut is evaluated later and does not change the jet direction.';
  }
</script>

<article class="object-inspector" aria-live="polite">
  <div class="inspector-heading"><h3>{text.title}</h3>{#if inspected}<span>{text.selected}</span>{/if}</div>
  {#if !inspected}
    <p class="empty">{text.noObject}</p>
  {:else if inspected.kind === 'layer'}
    {@const landmark = inspected.landmark}
    <div class="object-title"><span class={`kind-mark ${landmark.kind}`}></span><div><strong>{language === 'es' ? landmark.display_name_es : landmark.display_name_en}</strong><small>{text.otherName}: {language === 'es' ? landmark.display_name_en : landmark.display_name_es}</small></div></div>
    <dl class="metrics">
      <div><dt>{text.type}</dt><dd>{layerType(landmark.kind, text)}</dd></div>
      <div><dt>{text.radius}</dt><dd>{landmark.radius_mm === null ? '—' : `${landmark.radius_mm} mm`}</dd></div>
      <div><dt>{text.zExtent}</dt><dd>{landmark.abs_z_mm ? `|z| = ${landmark.abs_z_mm} mm` : landmark.z_extent_mm === null ? '—' : `|z| ≲ ${landmark.z_extent_mm} mm`}</dd></div>
    </dl>
    <section><h4>{text.relevance}</h4><p>{language === 'es' ? landmark.relevance_es : landmark.relevance_en}</p></section>
    <section><h4>{text.currentConnection}</h4><p>{connectionFor(inspected, cut, d0Threshold, language, text)}</p></section>
    <section><h4>{text.sourceNote}</h4><p>{language === 'es' ? landmark.source_note_es : landmark.source_note_en}</p></section>
    <p class="source"><strong>{text.provenance}:</strong> {#if landmark.source.startsWith('http')}<a href={landmark.source} target="_blank" rel="noreferrer">{landmark.source}</a>{:else}<code>{landmark.source}</code>{/if}</p>
  {:else}
    <div class="object-title"><span class={`object-mark ${inspected.kind}`}></span><div><strong>{inspected.kind === 'vertex' ? text.vertex : inspected.kind === 'track' ? text.track : text.jet}</strong><small>{text.event} #{event?.event_id}</small></div></div>
    <div class="decision-grid">
      <div><span>{text.currentDecision}</span><strong class:pass={eventCurrentPass === true} class:fail={eventCurrentPass === false}>{eventCurrentPass === null ? text.notApplicable : yesNo(eventCurrentPass, text)}</strong></div>
      <div><span>{text.fullDecision}</span><strong class:pass={eventFullPass === true} class:fail={eventFullPass === false}>{yesNo(Boolean(eventFullPass), text)}</strong></div>
    </div>

    {#if vertex}
      <dl class="metrics prominent">
        <div><dt>R</dt><dd>{vertex.r_mm.toFixed(3)} mm</dd></div><div><dt>z</dt><dd>{vertex.z_mm.toFixed(3)} mm</dd></div>
        <div><dt>{text.selectedTracks}</dt><dd>{vertex.selected_track_count}</dd></div><div><dt>{text.impactedTracks}</dt><dd>{vertex.impacted_track_count}</dd></div>
        <div><dt>{text.mass}</dt><dd>{vertex.mass_GeV.toFixed(3)} GeV</dd></div><div><dt>{text.vertexEfficiency}</dt><dd>{vertex.vertex_eff.toFixed(4)}</dd></div>
      </dl>
    {/if}

    {#if inspected.kind === 'track'}
      {@const track = inspected.track}
      <dl class="metrics prominent">
        <div><dt>{text.trackIndex}</dt><dd>#{track.track_index}</dd></div><div><dt>PDG ID / q</dt><dd>{track.pdg_id} / {track.charge > 0 ? '+' : ''}{track.charge}</dd></div>
        <div><dt>{text.exactD0}</dt><dd>{track.d0_mm.toFixed(4)} mm</dd></div><div><dt>{text.d0Decision}</dt><dd class:pass={track.passes_d0} class:fail={!track.passes_d0}>{yesNo(track.passes_d0, text)}</dd></div>
        <div><dt>{text.selectedForDv}</dt><dd class:pass={track.selected_for_dv} class:fail={!track.selected_for_dv}>{yesNo(track.selected_for_dv, text)}</dd></div>
        <div><dt>{text.transverseDistance}</dt><dd>{track.transverse_distance_mm.toFixed(1)} mm</dd></div>
        <div><dt>{text.ptOverCharge}</dt><dd>{trackPtOverCharge === null ? '—' : `${trackPtOverCharge.toFixed(3)} GeV`}</dd></div><div><dt>{text.threshold}</dt><dd>{d0Threshold === null ? '—' : `|d0| > ${d0Threshold} mm`}</dd></div>
      </dl>
      <section><h4>{text.currentConnection}</h4><p>{connectionFor(inspected, cut, d0Threshold, language, text)}</p></section>
      <p class="formula">d0 = rprod · sin(φprod − φtrack)</p>
    {:else if inspected.kind === 'jet'}
      {@const threshold = jetCut ? jetThresholdGeV(jetCut, inspected.jet.rank) : null}
      {@const branchPass = jetCut ? jetBranchPasses(jetCut, inspected.jet) : null}
      <dl class="metrics prominent">
        <div><dt>{text.rank}</dt><dd>j{inspected.jet.rank}</dd></div><div><dt>pT</dt><dd>{inspected.jet.pt_GeV.toFixed(2)} GeV</dd></div>
        <div><dt>{text.etaPhi}</dt><dd>{inspected.jet.eta.toFixed(3)}, {inspected.jet.phi.toFixed(3)}</dd></div><div><dt>{text.jetCount}</dt><dd>{inspected.event.jets.length}</dd></div>
        <div><dt>{text.threshold}</dt><dd>{threshold === null ? '—' : `${threshold} GeV`}</dd></div><div><dt>{text.branch}</dt><dd class:pass={branchPass === true} class:fail={branchPass === false}>{branchPass === null ? text.notApplicable : yesNo(branchPass, text)}</dd></div>
        <div><dt>{text.eventOr}</dt><dd class:pass={inspected.event.predicates.jet_selection} class:fail={!inspected.event.predicates.jet_selection}>{yesNo(inspected.event.predicates.jet_selection, text)}</dd></div>
      </dl>
      <section><h4>{text.currentConnection}</h4><p>{connectionFor(inspected, cut, d0Threshold, language, text)}</p></section>
    {:else}
      <section><h4>{text.currentConnection}</h4><p>{connectionFor(inspected, cut, d0Threshold, language, text)}</p></section>
    {/if}

    <details class="pass-list"><summary>{text.passList}</summary>{#each cuts as item}<div><span>{cutText(item, language).name}</span>{#if item.kind === 'response_weight'}<b>{text.responseWeight}</b>{:else if item.kind === 'summary'}<b>—</b>{:else if disabledCuts.has(item.id)}<b>{text.disabled}</b>{:else}<b class:pass={event ? eventPassesSelectedCut(event, item) : false} class:fail={event ? !eventPassesSelectedCut(event, item) : false}>{event ? yesNo(eventPassesSelectedCut(event, item), text) : '—'}</b>{/if}</div>{/each}</details>
    <dl class="event-meta"><div><dt>{text.weight}</dt><dd>{event?.weight.toPrecision(5)}</dd></div><div><dt>{text.firstFailed}</dt><dd>{failedCut ? cutText(failedCut, language).name : text.none}</dd></div></dl>
  {/if}
</article>

<style>
  .object-inspector { border: 1px solid #cfdadd; border-radius: 10px; padding: .85rem; background: #fbfcfc; min-width: 0; }
  .inspector-heading, .object-title, .decision-grid > div, .metrics > div, .event-meta > div, .pass-list div { display: flex; align-items: center; }
  .inspector-heading { justify-content: space-between; gap: 1rem; margin-bottom: .65rem; }.inspector-heading h3 { margin: 0; font-size: .92rem; }.inspector-heading span { color: #68777e; font-size: .68rem; text-transform: uppercase; letter-spacing: .07em; }
  .object-title { gap: .55rem; margin-bottom: .65rem; }.object-title div { display: grid; gap: .08rem; }.object-title small { color: #68777e; font-size: .7rem; }
  .kind-mark, .object-mark { width: 12px; height: 12px; flex: 0 0 auto; border-radius: 50%; }.detector_hardware { background: #8c9aa1; }.analysis_boundary { background: #d16b19; }.response_bin { background: repeating-linear-gradient(90deg,#7e929d 0 2px,transparent 2px 4px); border: 1px solid #7e929d; }.vertex { background: #f2b134; }.track { background: #236f93; }.jet { background: #7651a6; }
  .decision-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .45rem; margin-bottom: .65rem; }.decision-grid > div { justify-content: space-between; gap: .5rem; padding: .4rem .5rem; background: white; border: 1px solid #e0e7e9; border-radius: 6px; font-size: .72rem; }
  .metrics { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: .3rem .8rem; margin: .5rem 0; }.metrics > div { justify-content: space-between; gap: .5rem; border-bottom: 1px solid #e2e8ea; padding: .22rem 0; }.metrics dt { color: #66767d; font-size: .7rem; line-height: 1.25; }.metrics dd { margin: 0; flex: 0 0 auto; white-space: nowrap; font-size: .74rem; font-weight: 650; text-align: right; }.prominent { background: #eef4f5; border-radius: 7px; padding: .45rem .55rem; }
  section { margin: .65rem 0; } section h4 { margin: 0 0 .18rem; color: #53646c; font-size: .68rem; text-transform: uppercase; letter-spacing: .055em; } section p, .source, .empty { margin: 0; font-size: .76rem; line-height: 1.45; overflow-wrap: anywhere; }.source a { color: #176c83; }.source code { font-size: .68rem; }
  .formula { padding: .45rem .55rem; border-left: 3px solid #236f93; background: white; font: .74rem ui-monospace,SFMono-Regular,monospace; }
  .pass-list { margin-top: .7rem; font-size: .72rem; }.pass-list summary { cursor: pointer; font-weight: 650; }.pass-list div { justify-content: space-between; gap: 1rem; padding: .22rem 0; border-bottom: 1px solid #e4eaec; }
  .event-meta { display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin: .6rem 0 0; }.event-meta > div { justify-content: space-between; gap: .4rem; font-size: .7rem; }.event-meta dd { margin: 0; font-weight: 650; }
  .pass { color: #116d62; }.fail { color: #b44b38; }
  @media (max-width: 600px) { .decision-grid, .metrics, .event-meta { grid-template-columns: 1fr; } }
</style>
