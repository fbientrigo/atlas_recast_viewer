import type { CutDefinition, Manifest, Summary } from './data/schema';

export type Language = 'es' | 'en';

const messages = {
  es: {
    appTitle: 'Explorador del recast LLP', loading: 'Cargando el conjunto de datos…', validating: 'Validando manifiesto, cortes, resumen y telemetría opcional.',
    loadError: 'No se pudo cargar el conjunto de datos', dataset: 'Conjunto', file: 'Archivo', field: 'Campo', expected: 'Esperado', received: 'Recibido',
    datasetLabel: 'Conjunto de datos', publishedAggregate: 'Benchmark agregado publicado', localInteractive: 'Muestra local interactiva',
    referenceDataset: 'Conjunto de referencia', source: 'Fuente', commit: 'Commit', generated: 'Generados', unavailable: 'No disponible',
    dirtySource: 'FUENTE LOCAL · SIN COMMIT', frozenClean: 'CONGELADO · LIMPIO', capabilities: 'Capacidades del conjunto', available: 'DISPONIBLE', unavailableCaps: 'NO DISPONIBLE',
    analysisPanel: 'Panel de análisis', cutsAndResponse: 'Cortes y respuesta', weightedYields: 'rendimientos ponderados',
    referenceAEff: 'A × eficiencia de referencia', selectedStage: 'Etapa seleccionada', cumulativeAcceptance: 'aceptancia acumulada', responseWeightedYield: 'rendimiento ponderado por respuesta', externalStatus: 'Estado externo',
    stage: 'Etapa', technicalDefinition: 'Definición técnica', physicalIntuition: 'Intuición física', whyUsed: 'Por qué se usa', implementation: 'Implementación y procedencia', requiredFields: 'Campos requeridos',
    cutOnOffUnavailable: 'Cortes ON/OFF — No disponible para este conjunto', aggregateReason: 'Este conjunto solo contiene un cutflow agregado. No es posible reconstruir un contrafactual de forma única.',
    eventPackMissing: 'El manifiesto declara predicados atómicos, pero no se cargó un paquete de eventos validado.', on: 'activo', off: 'inactivo', locked: 'bloqueado', weight: 'peso', lost: 'pérdida', response: 'respuesta', lossNA: 'pérdida n/d',
    diagnosticBanner: 'CONTRAFACTUAL DIAGNÓSTICO · NO ES EL ANÁLISIS PUBLICADO/DE REFERENCIA', baselineMode: 'Selección de referencia',
    jetLogic: 'Lógica de ramas j4 / j5 / j6 / j7', or: 'O', richerJetUnavailable: 'Explorador de jets ampliado — No disponible para este conjunto', jetMissing: 'No se serializaron observables de jets para este conjunto.',
    geometryEyebrow: 'Geometría simplificada del recast', rzMap: 'Mapa R–z', cylindrical3d: 'Evento cilíndrico 3D', population: 'Población', event: 'Evento', previous: 'Anterior', next: 'Siguiente',
    accepted: 'Aceptado', rejected: 'Rechazado', acceptedVertices: 'Vértices que pasan', rejectedVertices: 'Vértices que fallan', selectedEvent: 'Evento seleccionado', jets: 'jets', vertices: 'vértices',
    highlighted: 'Resaltado', noSpatialBoundary: 'Esta etapa no define una frontera espacial.', truthWarning: 'Coordenadas de verdad y objetos simplificados del recast; no son hits reconstruidos de ATLAS ni una simulación completa del detector.',
    eventPointsUnavailable: 'Puntos de eventos no disponibles.', eventPointsReason: 'La ejecución de referencia no serializó coordenadas x/y/z por evento.',
    populationBridge: 'Puente de poblaciones', whatChanges: '¿Qué cambia aquí?', before: 'Antes', after: 'Después', removedByCut: 'Eliminado por corte', responseReduction: 'Reducción por respuesta',
    aggregatePopulationNote: 'Son rendimientos agregados ponderados. No se serializaron identidades de eventos.', eventPopulationNote: 'Los puntos corresponden a eventos y vértices reales de la muestra local; el color se recalcula con los cortes habilitados.',
    responseNote: 'Esta diferencia proviene de pesos de mapas de respuesta; no es una población rechazada por un corte duro.',
    booleanAcceptance: 'Aceptancia booleana actual', publishedResponseFixed: 'La A×eficiencia publicada permanece visible y no se reinterpreta al desactivar cortes.',
    validation: 'Validación', sourceCode: 'Fuente', currentCut: 'Corte actual', allCuts: 'Todos los cortes', geometryMode: 'Modo de geometría',
  },
  en: {
    appTitle: 'LLP recast explorer', loading: 'Loading dataset…', validating: 'Validating manifest, cuts, summary, and optional telemetry.',
    loadError: 'The dataset could not be loaded', dataset: 'Dataset', file: 'File', field: 'Field', expected: 'Expected', received: 'Received',
    datasetLabel: 'Dataset', publishedAggregate: 'Published aggregate benchmark', localInteractive: 'Interactive local sample',
    referenceDataset: 'Reference dataset', source: 'Source', commit: 'Commit', generated: 'Generated', unavailable: 'Not available',
    dirtySource: 'LOCAL SOURCE · UNCOMMITTED', frozenClean: 'FROZEN · CLEAN', capabilities: 'Dataset capabilities', available: 'AVAILABLE', unavailableCaps: 'UNAVAILABLE',
    analysisPanel: 'Analysis panel', cutsAndResponse: 'Cuts and response', weightedYields: 'weighted yields',
    referenceAEff: 'Reference A × efficiency', selectedStage: 'Selected stage', cumulativeAcceptance: 'cumulative acceptance', responseWeightedYield: 'response-weighted yield', externalStatus: 'External status',
    stage: 'Stage', technicalDefinition: 'Technical definition', physicalIntuition: 'Physical intuition', whyUsed: 'Why it is used', implementation: 'Implementation and provenance', requiredFields: 'Required fields',
    cutOnOffUnavailable: 'Cut ON/OFF — Unavailable for this dataset', aggregateReason: 'This dataset contains only aggregate cutflow information. A counterfactual cutflow cannot be reconstructed uniquely.',
    eventPackMissing: 'Atomic predicates are declared, but no validated event pack is loaded.', on: 'on', off: 'off', locked: 'locked', weight: 'weight', lost: 'lost', response: 'response', lossNA: 'loss n/a',
    diagnosticBanner: 'DIAGNOSTIC COUNTERFACTUAL · NOT THE PUBLISHED/REFERENCE ANALYSIS', baselineMode: 'Reference selection',
    jetLogic: 'j4 / j5 / j6 / j7 branch logic', or: 'OR', richerJetUnavailable: 'Richer Jet Explorer — Unavailable for this dataset', jetMissing: 'Jet observables were not serialized for this dataset.',
    geometryEyebrow: 'Simplified recast geometry', rzMap: 'R–z map', cylindrical3d: '3D cylindrical event', population: 'Population', event: 'Event', previous: 'Previous', next: 'Next',
    accepted: 'Accepted', rejected: 'Rejected', acceptedVertices: 'Passing vertices', rejectedVertices: 'Failing vertices', selectedEvent: 'Selected event', jets: 'jets', vertices: 'vertices',
    highlighted: 'Highlighted', noSpatialBoundary: 'This stage has no spatial boundary.', truthWarning: 'Truth coordinates and simplified recast objects only—not reconstructed ATLAS hits or a full detector simulation.',
    eventPointsUnavailable: 'Event points unavailable.', eventPointsReason: 'The reference execution did not serialize per-event x/y/z coordinates.',
    populationBridge: 'Population bridge', whatChanges: 'What changes here?', before: 'Before', after: 'After', removedByCut: 'Removed by cut', responseReduction: 'Response reduction',
    aggregatePopulationNote: 'These are weighted aggregate yields. Event identities were not serialized.', eventPopulationNote: 'Points are real events and vertices from the local sample; colors are recomputed from enabled cuts.',
    responseNote: 'This difference is caused by response-map weights. It is not a population rejected by a hard cut.',
    booleanAcceptance: 'Current boolean acceptance', publishedResponseFixed: 'Published A×eff remains visible and is not reinterpreted when cuts are disabled.',
    validation: 'Validation', sourceCode: 'Source', currentCut: 'Current cut', allCuts: 'All cuts', geometryMode: 'Geometry mode',
  },
} as const;

export type MessageKey = keyof typeof messages.es;

export function t(language: Language, key: MessageKey): string {
  return messages[language][key];
}

export function cutText(cut: CutDefinition, language: Language) {
  const translated = cut.translations?.[language];
  return {
    name: translated?.name ?? cut.name,
    physical_meaning: translated?.physical_meaning ?? cut.physical_meaning,
    analysis_rationale: translated?.analysis_rationale ?? cut.analysis_rationale,
  };
}

export function manifestText(manifest: Manifest, language: Language) {
  const translated = manifest.translations?.[language];
  return { title: translated?.title ?? manifest.title, reference_sample: translated?.reference_sample ?? manifest.reference_sample };
}

export function validationText(summary: Summary, language: Language) {
  const source = summary.external_validation;
  const translated = source.translations?.[language];
  return { scope: translated?.scope ?? source.scope, reference: translated?.reference ?? source.reference, note: translated?.note ?? source.note };
}

export function categoryLabel(category: string, language: Language): string {
  const labels: Record<string, { es: string; en: string }> = {
    jet_kinematics: { es: 'cinemática de jets', en: 'jet kinematics' }, geometry: { es: 'geometría', en: 'geometry' },
    track_displacement: { es: 'desplazamiento de trazas', en: 'track displacement' }, dv_quality: { es: 'calidad del DV', en: 'DV quality' },
    response_weight: { es: 'peso de respuesta', en: 'response weight' }, compound_selection: { es: 'selección compuesta', en: 'compound selection' },
  };
  return labels[category]?.[language] ?? category.replaceAll('_', ' ');
}

export function kindLabel(kind: CutDefinition['kind'], language: Language): string {
  const labels = {
    atomic_boolean: { es: 'booleano atómico', en: 'atomic boolean' }, compound_boolean: { es: 'booleano compuesto', en: 'compound boolean' },
    response_weight: { es: 'peso de respuesta', en: 'response weight' }, summary: { es: 'resumen', en: 'summary' },
  };
  return labels[kind][language];
}
