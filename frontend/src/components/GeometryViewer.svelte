<script lang="ts">
  import type { Capabilities, CutDefinition, DetectorGeometry, EventRecord, EventTrack, EventVertex, JetLogic } from '../data/schema';
  import type { Language } from '../i18n';
  import { t } from '../i18n';
  import { borderlineDefinition, cohortEvents, deterministicPage, type CohortId } from '../core/cohorts';
  import { transverseClosestApproach } from '../core/geometry';
  import { radialTickValues, resolveInspectionTarget, targetKey, type InspectionTarget } from '../core/inspection';
  import type { JetScaleContext } from '../core/selection';
  import ThreeEventScene from './ThreeEventScene.svelte';
  import ObjectInspector from './ObjectInspector.svelte';

  export let cut: CutDefinition;
  export let cuts: CutDefinition[];
  export let capabilities: Capabilities;
  export let events: EventRecord[] | undefined;
  export let detectorGeometry: DetectorGeometry | null = null;
  export let disabledCuts: Set<string>;
  export let language: Language;
  export let jetLogic: JetLogic | undefined = undefined;
  export let jetScale = 1;

  $: jetScaleContext = { jetLogic, scale: jetScale } as JetScaleContext;

  let cohort: CohortId = 'fails_selected';
  let displayCount = 10;
  let page = 0;
  let selectedEventId: number | null = null;
  let selectedVertexIndex = 0;
  let selectedTrackIndex = 0;
  let inspectedTarget: InspectionTarget | null = null;
  let hoveredTarget: InspectionTarget | null = null;
  let showDetector = true;
  let showAnalysis = true;
  let showResponse = false;
  let showLabels = true;
  let threeScene: ThreeEventScene;
  let previousCutId = '';
  let previousCohort = cohort;
  let previousCount = displayCount;

  const plotSize = 360;
  const plotMargin = 34;

  $: booleanCuts = cuts.filter((candidate) => candidate.kind !== 'response_weight' && candidate.kind !== 'summary' && !disabledCuts.has(candidate.id));
  $: selectedCutIsBoolean = cut.kind !== 'response_weight' && cut.kind !== 'summary';
  $: enabledCutIds = booleanCuts.map((candidate) => candidate.id);
  $: borderline = borderlineDefinition(cut);
  $: if (cohort === 'borderline' && !borderline) cohort = 'fails_selected';
  $: if (!selectedCutIsBoolean && ['passes_selected', 'fails_selected', 'borderline'].includes(cohort)) cohort = 'all';
  $: candidates = events ? cohortEvents(events, cohort, cut, enabledCutIds, cuts, jetScaleContext) : [];
  $: displayedEvents = deterministicPage(candidates, displayCount, page);
  $: if (cut.id !== previousCutId || cohort !== previousCohort || displayCount !== previousCount) {
    previousCutId = cut.id; previousCohort = cohort; previousCount = displayCount; page = 0;
  }
  $: if (displayedEvents.length && !displayedEvents.some((event) => event.event_id === selectedEventId)) {
    selectedEventId = displayedEvents[0].event_id; selectedVertexIndex = 0; selectedTrackIndex = 0;
    if (inspectedTarget?.kind !== 'layer') inspectedTarget = { kind: 'vertex', eventId: displayedEvents[0].event_id, vertexIndex: 0 };
  }
  $: selectedEvent = displayedEvents.find((event) => event.event_id === selectedEventId) ?? displayedEvents[0];
  $: selectedVertex = selectedEvent?.vertices[Math.min(selectedVertexIndex, Math.max(0, selectedEvent.vertices.length - 1))];
  $: selectedTracks = selectedVertex?.tracks ?? [];
  $: if (selectedTrackIndex >= selectedTracks.length) selectedTrackIndex = 0;
  $: selectedTrack = selectedTracks[selectedTrackIndex];
  $: inspected = detectorGeometry ? resolveInspectionTarget(inspectedTarget, displayedEvents, detectorGeometry) : null;
  $: hovered = detectorGeometry ? resolveInspectionTarget(hoveredTarget, displayedEvents, detectorGeometry) : null;
  $: eventPoints = displayedEvents.flatMap((event) => event.vertices.map((vertex, vertexIndex) => ({ event, vertex, vertexIndex })));
  $: rzExtent = cut.id === 'rxy_gt_4_mm' ? 50 : 330;
  $: xyExtent = cut.id === 'd0_gt_2_mm' && selectedVertex ? Math.max(4, Math.min(60, selectedVertex.r_mm + 4)) : cut.id === 'rxy_gt_4_mm' ? 50 : 330;
  $: rzTicks = radialTickValues(rzExtent);
  $: xyTicks = radialTickValues(xyExtent);
  $: showTrackDirections = ['d0_gt_2_mm', 'tracks_ge_5', 'mdv_gt_10_gev'].includes(cut.id) || inspected?.kind === 'track';
  $: hardware = detectorGeometry?.landmarks.filter((item) => item.kind === 'detector_hardware' && item.radius_mm !== null) ?? [];
  $: responseBins = detectorGeometry?.landmarks.filter((item) => item.kind === 'response_bin' && item.radius_mm !== null) ?? [];
  $: rMinMm = cuts.find((candidate) => candidate.id === 'rxy_gt_4_mm')?.parameters?.dv_r_min_mm ?? null;
  $: fiducialRMaxMm = cuts.find((candidate) => candidate.id === 'fiducial_dv')?.parameters?.dv_r_max_mm ?? null;
  $: fiducialZMaxMm = cuts.find((candidate) => candidate.id === 'fiducial_dv')?.parameters?.dv_abs_z_max_mm ?? null;
  $: d0MinMm = cuts.find((candidate) => candidate.id === 'd0_gt_2_mm')?.parameters?.track_abs_d0_min_mm ?? null;

  function selectVertex(eventId: number, vertexIndex: number): void {
    selectedEventId = eventId;
    selectedVertexIndex = vertexIndex;
    const vertex = displayedEvents.find((event) => event.event_id === eventId)?.vertices[vertexIndex];
    if (cut.id === 'd0_gt_2_mm' && vertex?.tracks.length) {
      selectedTrackIndex = vertex.tracks.reduce((best, track, index, tracks) =>
        Math.abs(Math.abs(track.d0_mm) - (d0MinMm ?? 0)) < Math.abs(Math.abs(tracks[best].d0_mm) - (d0MinMm ?? 0)) ? index : best, 0);
    } else selectedTrackIndex = 0;
    inspectedTarget = { kind: 'vertex', eventId, vertexIndex };
  }

  function inspectTarget(target: InspectionTarget): void {
    inspectedTarget = target;
    if (target.kind === 'layer') return;
    selectedEventId = target.eventId;
    if (target.kind === 'jet') return;
    selectedVertexIndex = target.vertexIndex;
    if (target.kind === 'track') selectedTrackIndex = target.trackIndex;
  }

  function hoverLabel(value: typeof hovered, activeLanguage: Language): string | null {
    if (!value) return null;
    if (value.kind === 'layer') return `${activeLanguage === 'es' ? value.landmark.display_name_es : value.landmark.display_name_en}${value.landmark.radius_mm === null ? '' : ` · R=${value.landmark.radius_mm} mm`}`;
    if (value.kind === 'vertex') return `DV #${value.event.event_id}/${value.vertexIndex} · R=${value.vertex.r_mm.toFixed(2)} mm · z=${value.vertex.z_mm.toFixed(2)} mm`;
    if (value.kind === 'track') return `${activeLanguage === 'es' ? 'Traza' : 'Track'} #${value.track.track_index} · |d0|=${Math.abs(value.track.d0_mm).toFixed(2)} mm`;
    return `j${value.jet.rank} · pT=${value.jet.pt_GeV.toFixed(1)} GeV`;
  }

  function scaleX(value: number, extent: number): number { return plotMargin + ((value + extent) / (2 * extent)) * (plotSize - 2 * plotMargin); }
  function scaleR(value: number, extent: number): number { return plotSize - plotMargin - Math.min(value, extent) / extent * (plotSize - 2 * plotMargin); }
  function vertexClass(event: EventRecord, vertex: EventVertex, vertexIndex: number): string {
    if (event.event_id === selectedEventId && vertexIndex === selectedVertexIndex) return 'selected-point';
    if (!selectedCutIsBoolean) return 'neutral-point';
    const passes = cut.id === 'jet_selection' ? event.predicates.jet_selection : vertex.predicates[cut.id] === true;
    return passes ? 'pass-point' : 'fail-point';
  }
  function trackLine(track: EventTrack, extent: number): { x1: number; y1: number; x2: number; y2: number } {
    const norm = Math.hypot(track.px_GeV, track.py_GeV) || 1;
    const length = extent * 0.75;
    return {
      x1: scaleX(track.x_prod_mm, extent), y1: scaleX(-track.y_prod_mm, extent),
      x2: scaleX(track.x_prod_mm + length * track.px_GeV / norm, extent),
      y2: scaleX(-(track.y_prod_mm + length * track.py_GeV / norm), extent),
    };
  }
  const geometryMessages = {
    es: {
      count: 'Eventos mostrados', cohort: 'Cohorte', all: 'Todos', accepted: 'Aceptados', passes: 'Pasa el corte seleccionado', fails: 'Falla el corte seleccionado', borderline: 'En el borde', nextSubset: 'Siguiente subconjunto', reset: 'Restablecer vista', detector: 'Capas del detector', analysis: 'Límites del análisis', response: 'Bins de respuesta', labels: 'Etiquetas', radialScale: 'Escala radial seleccionable', source: 'Fuente', rz: 'Proyección R–z', xy: 'Plano transversal x–y', inspector: 'Inspector del evento', eventId: 'Evento', weight: 'Peso', firstFailed: 'Primer corte fallado', none: 'ninguno', selectedTracks: 'trazas seleccionadas', threshold: 'umbral', pass: 'PASA', fail: 'FALLA', d0Intuition: 'd0 mide qué tan lejos del punto de interacción pasa la trayectoria en el plano transversal.', d0Technical: 'Proxy exacto del recast: d0 = rprod·sin(φprod−φtraza), con el mismo plegado angular del C++.', pion: 'Hipótesis de masa de pión cargado', constituents: 'trazas que entran en mDV', selectedDaughter: 'Hija cargada', sampleEmpty: 'No hay eventos en esta cohorte.', selectedDecision: 'Decisión del corte seleccionado', fullDecision: 'Selección booleana completa', controls: 'Arrastre izquierdo: rotar · rueda: zoom · arrastre derecho: desplazar · clic: inspeccionar', truthTrack: 'dirección recta de verdad/recast; sin propagación magnética', hardwareVsCut: 'Hardware ATLAS (gris) · límites de análisis (naranja) · bins de respuesta (punteados)', radialDistance: 'Distancia a la línea del haz', clickHint: 'Clic en capa, DV, traza o jet para fijar la inspección',
    },
    en: {
      count: 'Events shown', cohort: 'Cohort', all: 'All', accepted: 'Accepted', passes: 'Passes selected cut', fails: 'Fails selected cut', borderline: 'Borderline', nextSubset: 'Next subset', reset: 'Reset view', detector: 'Detector layers', analysis: 'Analysis boundaries', response: 'Response bins', labels: 'Labels', radialScale: 'Selectable radial scale', source: 'Source', rz: 'R–z projection', xy: 'Transverse x–y plane', inspector: 'Event inspector', eventId: 'Event', weight: 'Weight', firstFailed: 'First failed cut', none: 'none', selectedTracks: 'selected tracks', threshold: 'threshold', pass: 'PASS', fail: 'FAIL', d0Intuition: 'd0 measures how far from the interaction point the trajectory passes in the transverse plane.', d0Technical: 'Exact recast proxy: d0 = rprod·sin(φprod−φtrack), with the same C++ angular folding.', pion: 'Charged-pion mass hypothesis', constituents: 'tracks entering mDV', selectedDaughter: 'Charged daughter', sampleEmpty: 'No events in this cohort.', selectedDecision: 'Selected-cut decision', fullDecision: 'Full boolean selection', controls: 'Left drag: rotate · wheel: zoom · right drag: pan · click: inspect', truthTrack: 'straight truth/recast direction; no magnetic propagation', hardwareVsCut: 'ATLAS hardware (grey) · analysis boundaries (orange) · response bins (dashed)', radialDistance: 'Distance from beam line', clickHint: 'Click a layer, DV, track, or jet to pin inspection',
    },
  };
  $: text = geometryMessages[language];
</script>

<section class="geometry-view" aria-labelledby="geometry-heading">
  <div class="panel-title geometry-heading">
    <div><p class="eyebrow">{t(language, 'geometryEyebrow')}</p><h2 id="geometry-heading">3D + R–z + x–y</h2></div>
    <span class="cut-focus">{language === 'es' ? 'Énfasis' : 'Focus'}: {cut.translations?.[language]?.name ?? cut.name}</span>
  </div>

  {#if events && detectorGeometry && capabilities.dv_xyz}
    <div class="population-controls">
      <label>{text.count}<select bind:value={displayCount}>{#each [1, 10, 25] as amount}<option value={amount}>{amount}</option>{/each}</select></label>
      <label>{text.cohort}<select bind:value={cohort}>
        <option value="all">{text.all}</option><option value="accepted">{text.accepted}</option>
        {#if selectedCutIsBoolean}<option value="passes_selected">{text.passes}</option><option value="fails_selected">{text.fails}</option>
        {#if borderline}<option value="borderline">{text.borderline}</option>{/if}{/if}
      </select></label>
      <button on:click={() => page += 1} disabled={candidates.length <= displayCount}>{text.nextSubset}</button>
      <span>{displayedEvents.length}/{candidates.length}</span>
      {#if candidates.length === 0}<strong class="empty-cohort">{text.sampleEmpty}</strong>{/if}
      {#if cohort === 'borderline' && borderline}<span class="window-note">{borderline.window[language]}</span>{/if}
    </div>

    <div class="layer-controls">
      <label><input type="checkbox" bind:checked={showDetector} /> {text.detector}</label>
      <label><input type="checkbox" bind:checked={showAnalysis} /> {text.analysis}</label>
      <label><input type="checkbox" bind:checked={showResponse} /> {text.response}</label>
      <label><input type="checkbox" bind:checked={showLabels} /> {text.labels}</label>
    </div>

    <div class="three-toolbar">
      <button on:click={() => threeScene.setPreset('3d')}>3D</button><button on:click={() => threeScene.setPreset('rz')}>R–z</button><button on:click={() => threeScene.setPreset('xy')}>x–y</button>
      <button on:click={() => threeScene.resetView()}>{text.reset}</button><span>{text.controls}</span>
    </div>
    <div class="scene-wrap">
      <ThreeEventScene bind:this={threeScene} geometry={detectorGeometry} {showDetector} {showAnalysis} {showResponse} {selectedEventId} {selectedVertexIndex} selectedTarget={inspectedTarget} selectedCutId={cut.id} selectedCutKind={cut.kind} events={displayedEvents} onInspect={inspectTarget} onHover={(target) => hoveredTarget = target} />
      {#if hoverLabel(hovered, language)}<div class="geometry-hover">{hoverLabel(hovered, language)}</div>{/if}
      <div class="click-hint">{text.clickHint}</div>
    </div>
    <div class="semantic-legend">{text.hardwareVsCut}{#if ['d0_gt_2_mm', 'tracks_ge_5', 'mdv_gt_10_gev'].includes(cut.id)} · {language === 'es' ? 'trazas seleccionadas (azul), candidatas no seleccionadas (gris tenue)' : 'selected tracks (blue), unselected candidates (faint grey)'}{/if}</div>

    <div class:d0-focus={cut.id === 'd0_gt_2_mm'} class="projection-grid">
      <article class="projection-card rz-card">
        <h3>{text.rz}</h3>
        <svg viewBox={`0 0 ${plotSize} ${plotSize}`} role="img">
          <rect x={plotMargin} y={plotMargin} width={plotSize - 2 * plotMargin} height={plotSize - 2 * plotMargin} class="plot-bg" />
          {#each rzTicks as tick}<line x1={plotMargin - 3} x2={plotSize - plotMargin} y1={scaleR(tick, rzExtent)} y2={scaleR(tick, rzExtent)} class="scale-grid" /><text x={plotMargin - 6} y={scaleR(tick, rzExtent) + 3} text-anchor="end" class="scale-label">{tick}</text>{/each}
          {#if showDetector}{#each hardware.filter((item) => item.radius_mm! <= rzExtent) as layer}<line x1={scaleX(-(layer.z_extent_mm ?? rzExtent), rzExtent)} x2={scaleX(layer.z_extent_mm ?? rzExtent, rzExtent)} y1={scaleR(layer.radius_mm!, rzExtent)} y2={scaleR(layer.radius_mm!, rzExtent)} class:selected-geometry={targetKey(inspectedTarget) === `layer:${layer.id}`} class="hardware-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: layer.id })} on:mouseenter={() => hoveredTarget = { kind: 'layer', landmarkId: layer.id }} on:mouseleave={() => hoveredTarget = null} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: layer.id })}><title>{language === 'es' ? layer.display_name_es : layer.display_name_en}: R={layer.radius_mm} mm · {layer.source}</title></line>{/each}{/if}
          {#if showResponse}{#each responseBins.filter((item) => item.radius_mm! <= rzExtent) as layer}<line x1={scaleX(-rzExtent, rzExtent)} x2={scaleX(rzExtent, rzExtent)} y1={scaleR(layer.radius_mm!, rzExtent)} y2={scaleR(layer.radius_mm!, rzExtent)} class:selected-geometry={targetKey(inspectedTarget) === `layer:${layer.id}`} class="response-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: layer.id })} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: layer.id })} />{/each}{/if}
          {#if showAnalysis}
            {#if rMinMm !== null}<line x1={scaleX(-rzExtent, rzExtent)} x2={scaleX(rzExtent, rzExtent)} y1={scaleR(rMinMm, rzExtent)} y2={scaleR(rMinMm, rzExtent)} class:emphasized={cut.id === 'rxy_gt_4_mm'} class:selected-geometry={targetKey(inspectedTarget) === 'layer:dv_min_r'} class="analysis-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: 'dv_min_r' })} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: 'dv_min_r' })} />{/if}
            {#if fiducialRMaxMm !== null && fiducialZMaxMm !== null && rzExtent >= fiducialRMaxMm}<line x1={scaleX(-rzExtent, rzExtent)} x2={scaleX(rzExtent, rzExtent)} y1={scaleR(fiducialRMaxMm, rzExtent)} y2={scaleR(fiducialRMaxMm, rzExtent)} class:selected-geometry={targetKey(inspectedTarget) === 'layer:dv_max_r'} class="analysis-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: 'dv_max_r' })} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: 'dv_max_r' })} /><line x1={scaleX(-fiducialZMaxMm, rzExtent)} x2={scaleX(-fiducialZMaxMm, rzExtent)} y1={scaleR(0, rzExtent)} y2={scaleR(fiducialRMaxMm, rzExtent)} class:selected-geometry={targetKey(inspectedTarget) === 'layer:dv_max_z'} class="analysis-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: 'dv_max_z' })} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: 'dv_max_z' })} /><line x1={scaleX(fiducialZMaxMm, rzExtent)} x2={scaleX(fiducialZMaxMm, rzExtent)} y1={scaleR(0, rzExtent)} y2={scaleR(fiducialRMaxMm, rzExtent)} class:selected-geometry={targetKey(inspectedTarget) === 'layer:dv_max_z'} class="analysis-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: 'dv_max_z' })} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: 'dv_max_z' })} />{/if}
          {/if}
          {#each eventPoints as point}<circle cx={scaleX(point.vertex.z_mm, rzExtent)} cy={scaleR(point.vertex.r_mm, rzExtent)} r={point.event.event_id === selectedEventId && point.vertexIndex === selectedVertexIndex ? 5 : 3} class={vertexClass(point.event, point.vertex, point.vertexIndex)} role="button" tabindex="0" on:click={() => selectVertex(point.event.event_id, point.vertexIndex)} on:keydown={(event) => event.key === 'Enter' && selectVertex(point.event.event_id, point.vertexIndex)}><title>#{point.event.event_id} · R={point.vertex.r_mm.toFixed(2)} mm · z={point.vertex.z_mm.toFixed(2)} mm</title></circle>{/each}
          <text x={plotSize / 2} y={plotSize - 7} text-anchor="middle">z [mm]</text><text x="13" y={plotSize / 2} transform={`rotate(-90 13 ${plotSize / 2})`} text-anchor="middle">R [mm]</text>
          {#if showLabels && rMinMm !== null}<text x={plotMargin + 4} y={scaleR(rMinMm, rzExtent) - 4} class="analysis-label">R={rMinMm} mm</text>{#if fiducialRMaxMm !== null && rzExtent >= fiducialRMaxMm}<text x={plotMargin + 4} y={scaleR(fiducialRMaxMm, rzExtent) - 4} class="analysis-label">R={fiducialRMaxMm} mm</text>{/if}{/if}
        </svg>
      </article>

      <article class="projection-card xy-card">
        <h3>{text.xy}</h3>
        <svg viewBox={`0 0 ${plotSize} ${plotSize}`} role="img">
          <rect x={plotMargin} y={plotMargin} width={plotSize - 2 * plotMargin} height={plotSize - 2 * plotMargin} class="plot-bg" />
          {#each xyTicks.filter((tick) => tick > 0) as tick}<circle cx={scaleX(0, xyExtent)} cy={scaleX(0, xyExtent)} r={(tick / (2 * xyExtent)) * (plotSize - 2 * plotMargin)} class="scale-grid" />{#if showLabels}<text x={scaleX(0, xyExtent) + (tick / (2 * xyExtent)) * (plotSize - 2 * plotMargin) + 2} y={scaleX(0, xyExtent) - 3} class="scale-label">{tick}</text>{/if}{/each}
          {#if showDetector}{#each hardware.filter((item) => item.radius_mm! <= xyExtent) as layer}<circle cx={scaleX(0, xyExtent)} cy={scaleX(0, xyExtent)} r={(layer.radius_mm! / (2 * xyExtent)) * (plotSize - 2 * plotMargin)} class:selected-geometry={targetKey(inspectedTarget) === `layer:${layer.id}`} class="hardware-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: layer.id })} on:mouseenter={() => hoveredTarget = { kind: 'layer', landmarkId: layer.id }} on:mouseleave={() => hoveredTarget = null} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: layer.id })}><title>{language === 'es' ? layer.display_name_es : layer.display_name_en} · R={layer.radius_mm} mm · {text.source}: {layer.source}</title></circle>{/each}{/if}
          {#if showResponse}{#each responseBins.filter((item) => item.radius_mm! <= xyExtent) as layer}<circle cx={scaleX(0, xyExtent)} cy={scaleX(0, xyExtent)} r={(layer.radius_mm! / (2 * xyExtent)) * (plotSize - 2 * plotMargin)} class:selected-geometry={targetKey(inspectedTarget) === `layer:${layer.id}`} class="response-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: layer.id })} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: layer.id })} />{/each}{/if}
          {#if showAnalysis && rMinMm !== null}<circle cx={scaleX(0, xyExtent)} cy={scaleX(0, xyExtent)} r={(rMinMm / (2 * xyExtent)) * (plotSize - 2 * plotMargin)} class:emphasized={cut.id === 'rxy_gt_4_mm'} class:selected-geometry={targetKey(inspectedTarget) === 'layer:dv_min_r'} class="analysis-guide inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'layer', landmarkId: 'dv_min_r' })} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'layer', landmarkId: 'dv_min_r' })} />{/if}
          <circle cx={scaleX(0, xyExtent)} cy={scaleX(0, xyExtent)} r="3" class="origin-point"><title>IP / beamline</title></circle>
          {#each eventPoints as point}<circle cx={scaleX(point.vertex.x_mm, xyExtent)} cy={scaleX(-point.vertex.y_mm, xyExtent)} r={point.event.event_id === selectedEventId && point.vertexIndex === selectedVertexIndex ? 5 : 3} class={vertexClass(point.event, point.vertex, point.vertexIndex)} role="button" tabindex="0" on:click={() => selectVertex(point.event.event_id, point.vertexIndex)} on:keydown={(event) => event.key === 'Enter' && selectVertex(point.event.event_id, point.vertexIndex)} />{/each}
          {#if showTrackDirections && selectedEvent && selectedVertex}{#each selectedTracks as track, trackIndex}{@const candidateLine = trackLine(track, xyExtent)}<line x1={candidateLine.x1} y1={candidateLine.y1} x2={candidateLine.x2} y2={candidateLine.y2} class:selected-track-line={trackIndex === selectedTrackIndex} class:selected-for-dv={track.selected_for_dv} class="candidate-track-line inspectable" role="button" tabindex="0" on:click={() => inspectTarget({ kind: 'track', eventId: selectedEvent.event_id, vertexIndex: selectedVertexIndex, trackIndex })} on:mouseenter={() => hoveredTarget = { kind: 'track', eventId: selectedEvent.event_id, vertexIndex: selectedVertexIndex, trackIndex }} on:mouseleave={() => hoveredTarget = null} on:keydown={(event) => event.key === 'Enter' && inspectTarget({ kind: 'track', eventId: selectedEvent.event_id, vertexIndex: selectedVertexIndex, trackIndex })}><title>#{track.track_index} · |d0|={Math.abs(track.d0_mm).toFixed(3)} mm</title></line>{/each}{/if}
          {#if (cut.id === 'd0_gt_2_mm' || inspected?.kind === 'track') && selectedTrack}
            {@const trackGeometry = trackLine(selectedTrack, xyExtent)}
            {@const closest = transverseClosestApproach(selectedTrack)}
            <line x1={scaleX(0, xyExtent)} y1={scaleX(0, xyExtent)} x2={scaleX(selectedTrack.x_prod_mm, xyExtent)} y2={scaleX(-selectedTrack.y_prod_mm, xyExtent)} class="production-radius" />
            <line x1={trackGeometry.x1} y1={trackGeometry.y1} x2={trackGeometry.x2} y2={trackGeometry.y2} class="selected-track-line" />
            <line x1={scaleX(0, xyExtent)} y1={scaleX(0, xyExtent)} x2={scaleX(closest.x, xyExtent)} y2={scaleX(-closest.y, xyExtent)} class="d0-distance" />
            <circle cx={scaleX(closest.x, xyExtent)} cy={scaleX(-closest.y, xyExtent)} r="3" class="closest-point" />
            <text x={scaleX(closest.x, xyExtent) + 5} y={scaleX(-closest.y, xyExtent) - 5} class="d0-label">|d0|={Math.abs(selectedTrack.d0_mm).toFixed(2)} mm</text>
            <text x={scaleX(selectedTrack.x_prod_mm, xyExtent) + 5} y={scaleX(-selectedTrack.y_prod_mm, xyExtent) + 12} class="radius-label">rprod={Math.hypot(selectedTrack.x_prod_mm, selectedTrack.y_prod_mm).toFixed(2)} mm</text>
          {/if}
          <text x={plotSize / 2} y={plotSize - 7} text-anchor="middle">x [mm]</text><text x="13" y={plotSize / 2} transform={`rotate(-90 13 ${plotSize / 2})`} text-anchor="middle">y [mm]</text>
        </svg>
      </article>
    </div>

    {#if selectedEvent}
      <nav class="object-shortcuts" aria-label={language === 'es' ? 'Objetos del evento' : 'Event objects'}>
        <strong>{language === 'es' ? 'Objetos' : 'Objects'}:</strong>
        {#each selectedEvent.vertices as _vertex, vertexIndex}<button class:active={targetKey(inspectedTarget) === `vertex:${selectedEvent.event_id}:${vertexIndex}`} on:click={() => inspectTarget({ kind: 'vertex', eventId: selectedEvent.event_id, vertexIndex })}>DV {vertexIndex}</button>{/each}
        {#each selectedEvent.jets as jet}<button class:active={targetKey(inspectedTarget) === `jet:${selectedEvent.event_id}:${jet.rank}`} on:click={() => inspectTarget({ kind: 'jet', eventId: selectedEvent.event_id, jetRank: jet.rank })}>j{jet.rank}</button>{/each}
        {#if selectedTracks.length}<label>{language === 'es' ? 'Traza' : 'Track'}<select value={selectedTrackIndex} on:change={(event) => inspectTarget({ kind: 'track', eventId: selectedEvent.event_id, vertexIndex: selectedVertexIndex, trackIndex: Number(event.currentTarget.value) })}>{#each selectedTracks as track, trackIndex}<option value={trackIndex}>#{track.track_index} · |d0|={Math.abs(track.d0_mm).toFixed(2)} mm</option>{/each}</select></label>{/if}
      </nav>
    {/if}

    <div class="geometry-lower">
      <article class="radial-legend">
        <h3>{text.radialScale}</h3>
        {#if showDetector}{#each hardware as layer}<button class:selected={targetKey(inspectedTarget) === `layer:${layer.id}`} on:click={() => inspectTarget({ kind: 'layer', landmarkId: layer.id })} title={`${text.source}: ${layer.source}`}><span class="hardware-swatch"></span><span>{language === 'es' ? layer.display_name_es : layer.display_name_en}</span><strong>{layer.radius_mm} mm</strong></button>{/each}{/if}
        {#if showAnalysis && rMinMm !== null && fiducialRMaxMm !== null}<button class:selected={targetKey(inspectedTarget) === 'layer:dv_min_r'} on:click={() => inspectTarget({ kind: 'layer', landmarkId: 'dv_min_r' })}><span class="analysis-swatch"></span><span>R DV min</span><strong>{rMinMm} mm</strong></button><button class:selected={targetKey(inspectedTarget) === 'layer:dv_max_r'} on:click={() => inspectTarget({ kind: 'layer', landmarkId: 'dv_max_r' })}><span class="analysis-swatch"></span><span>R DV max</span><strong>{fiducialRMaxMm} mm</strong></button>{/if}
        <div class="ruler"><span>0</span><i></i><span>{hardware.at(-1)?.radius_mm ?? fiducialRMaxMm ?? 300} mm</span></div>
      </article>

      <ObjectInspector {inspected} {cut} {cuts} {disabledCuts} {language} {jetLogic} {jetScale} />
    </div>
  {:else}
    <div class="inline-unavailable"><strong>{t(language, 'eventPointsUnavailable')}</strong> {t(language, 'eventPointsReason')}</div>
  {/if}

  <p class="truth-warning">{t(language, 'truthWarning')}</p>
  {#if disabledCuts.size > 0}<p class="diagnostic-label">{t(language, 'diagnosticBanner')}</p>{/if}
</section>

<style>
  .geometry-view { display: grid; gap: .8rem; }
  .geometry-heading { align-items: end; }
  .cut-focus { max-width: 48%; color: #51616a; font-size: .82rem; text-align: right; }
  .population-controls, .layer-controls, .three-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: .55rem .8rem; }
  .population-controls, .layer-controls { padding: .65rem .75rem; border: 1px solid #dce4e7; border-radius: 9px; background: #fbfcfc; }
  label { display: inline-flex; align-items: center; gap: .38rem; font-size: .79rem; color: #36464e; }
  select, button { border: 1px solid #bdcbd0; border-radius: 6px; background: white; color: #203039; padding: .35rem .52rem; font: inherit; }
  button { cursor: pointer; } button:disabled { cursor: not-allowed; opacity: .45; }
  .window-note { color: #6b4e16; font-size: .76rem; }
  .empty-cohort { color: #a24635; font-size: .76rem; }
  .three-toolbar span { color: #65757d; font-size: .74rem; margin-left: auto; }
  .scene-wrap { position: relative; }.geometry-hover { position: absolute; top: .65rem; left: .65rem; max-width: calc(100% - 1.3rem); padding: .36rem .5rem; border: 1px solid #bdcbd0; border-radius: 6px; background: rgba(255,255,255,.94); color: #263a43; font-size: .72rem; pointer-events: none; }.click-hint { position: absolute; right: .65rem; bottom: .55rem; padding: .25rem .42rem; border-radius: 5px; background: rgba(255,255,255,.82); color: #617078; font-size: .66rem; pointer-events: none; }
  .semantic-legend { color: #5d6b72; font-size: .74rem; text-align: center; }
  .projection-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .8rem; }
  .projection-card { border: 1px solid #dce4e7; border-radius: 10px; padding: .65rem; background: #fff; min-width: 0; }
  .projection-card h3, .geometry-lower h3 { margin: 0 0 .35rem; font-size: .9rem; }
  .projection-card svg { width: 100%; max-height: 340px; display: block; }
  .d0-focus .xy-card { border-color: #d89229; box-shadow: 0 0 0 2px rgba(216,146,41,.14); }
  .projection-grid.d0-focus { grid-template-columns: .8fr 1.2fr; }
  .plot-bg { fill: #f9fbfb; stroke: #e5ebed; }
  .scale-grid { fill: none; stroke: #dce5e8; stroke-width: .65; }.scale-label { fill: #87949a; font-size: 8px; }
  .hardware-guide { fill: none; stroke: #8c9aa1; stroke-width: 1; opacity: .7; }
  .analysis-guide { fill: none; stroke: #d16b19; stroke-width: 1.8; }
  .analysis-guide.emphasized { stroke: #df4628; stroke-width: 3; }
  .response-guide { fill: none; stroke: #7e929d; stroke-width: 1; stroke-dasharray: 3 4; opacity: .45; }
  .inspectable { cursor: pointer; pointer-events: stroke; }.selected-geometry { stroke: #315e73 !important; stroke-width: 3 !important; opacity: 1 !important; }
  .pass-point { fill: #18786d; stroke: white; stroke-width: 1; cursor: pointer; }
  .fail-point { fill: #c65a43; stroke: white; stroke-width: 1; cursor: pointer; }
  .selected-point { fill: #f2b134; stroke: #4f3b0d; stroke-width: 1.5; cursor: pointer; }
  .neutral-point { fill: #71858e; stroke: white; stroke-width: 1; cursor: pointer; }
  .origin-point { fill: #27343b; }
  .candidate-track-line { stroke: #9aa7ae; stroke-width: 1; opacity: .22; }.candidate-track-line.selected-for-dv { stroke: #236f93; opacity: .42; }.candidate-track-line.selected-track-line { stroke: #f2a91f; stroke-width: 2.6; opacity: 1; }
  .selected-track-line { stroke: #236f93; stroke-width: 2; }
  .d0-distance { stroke: #df4628; stroke-width: 2; stroke-dasharray: 3 2; }
  .production-radius { stroke: #687981; stroke-width: 1.2; stroke-dasharray: 2 2; }
  .closest-point { fill: #df4628; }
  .d0-label, .analysis-label { fill: #a43f28; font-size: 10px; font-weight: 650; }.radius-label { fill: #53656d; font-size: 9px; }
  svg text { fill: #52626a; font-size: 10px; }
  .object-shortcuts { display: flex; align-items: center; gap: .35rem; overflow-x: auto; padding: .45rem .55rem; border: 1px solid #dce4e7; border-radius: 8px; background: #fbfcfc; font-size: .7rem; }.object-shortcuts strong { color: #586870; }.object-shortcuts button { padding: .2rem .36rem; white-space: nowrap; }.object-shortcuts button.active { border-color: #315e73; background: #eaf2f5; color: #224c60; }.object-shortcuts label { margin-left: auto; white-space: nowrap; }
  .geometry-lower { display: grid; grid-template-columns: minmax(220px,.72fr) minmax(300px,1.28fr); gap: .8rem; }
  .radial-legend { border: 1px solid #dce4e7; border-radius: 10px; padding: .8rem; background: #fbfcfc; }
  .radial-legend > button { display: grid; grid-template-columns: 13px 1fr auto; width: 100%; gap: .45rem; align-items: center; padding: .28rem .3rem; border-color: transparent; color: #33454e; text-align: left; font-size: .72rem; }.radial-legend > button:hover, .radial-legend > button.selected { border-color: #9eb2ba; background: #edf3f5; }
  .ruler { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: .35rem; margin-top: .55rem; color: #65757d; font-size: .66rem; }.ruler i { height: 5px; border: solid #687a82; border-width: 0 1px 1px; }
  .hardware-swatch { width: 12px; border-top: 2px solid #8c9aa1; }.analysis-swatch { width: 12px; border-top: 3px solid #d16b19; }
  .truth-warning { margin: 0; }
  @media (max-width: 900px) { .projection-grid, .projection-grid.d0-focus, .geometry-lower { grid-template-columns: 1fr; }.three-toolbar span { width: 100%; margin-left: 0; }.cut-focus { max-width: none; } }
</style>
