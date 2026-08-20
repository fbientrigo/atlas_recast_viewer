import type { Capabilities, CutDefinition, EventRecord, EventVertex, JetLogic } from '../data/schema';

export interface AtomicEvent {
  weight: number;
  predicates: Record<string, boolean | null>;
}

/** Diagnostic jet-threshold scale context (Step 3C generic selection engine). */
export interface JetScaleContext {
  jetLogic: JetLogic | undefined;
  scale: number;
}

/**
 * Recompute the jet_selection verdict from serialized jets[] and jet_logic
 * metadata at an arbitrary threshold scale `s`, generalizing the stored
 * baseline predicate. No physics constants are hardcoded here: thresholds,
 * the additional-leg predicate id, and s-support all come from jet_logic.
 * A dataset without threshold_scale.supported simply returns the stored
 * baseline predicate unchanged (matches every dataset written before this
 * capability existed, e.g. the High-pT reference).
 */
export function jetSelectionPasses(event: EventRecord, jetLogic: JetLogic | undefined, scale: number): boolean {
  if (!jetLogic?.threshold_scale?.supported) return event.predicates.jet_selection === true;
  const jetByRank = new Map(event.jets.map((jet) => [jet.rank, jet]));
  const ordinary = jetLogic.branches.some((branch) => {
    const jet = jetByRank.get(branch.jet_rank);
    return jet !== undefined && jet.pt_GeV > branch.threshold_GeV * scale;
  });
  const additional = jetLogic.additional_requirement;
  const additionalPass = !additional?.supported || event.predicates[additional.predicate_id] === true;
  return ordinary && additionalPass;
}

export interface ModuleAvailability {
  available: boolean;
  reason?: string;
}

export function diagnosticAvailability(
  capabilities: Capabilities,
  atomicEventsLoaded = false,
): ModuleAvailability {
  if (!capabilities.atomic_event_cuts) {
    return {
      available: false,
      reason: 'This dataset contains only aggregate cutflow information. A counterfactual cutflow cannot be reconstructed uniquely.',
    };
  }
  if (!atomicEventsLoaded) {
    return {
      available: false,
      reason: 'Atomic predicates are declared, but no validated event pack is loaded.',
    };
  }
  return { available: true };
}

export function jetExplorerAvailability(capabilities: Capabilities): ModuleAvailability {
  if (!capabilities.jet_observables) {
    return { available: false, reason: 'Jet observables were not serialized for this dataset.' };
  }
  return { available: true };
}

/** Whether the `s` diagnostic control should be enabled, from metadata alone. */
export function thresholdScaleAvailability(jetLogic: JetLogic | undefined): ModuleAvailability {
  if (!jetLogic?.threshold_scale?.supported) {
    return { available: false, reason: 'This dataset does not declare a diagnostic jet-threshold scale.' };
  }
  return { available: true };
}

export function recomputeCumulative(
  events: AtomicEvent[],
  cuts: CutDefinition[],
  disabled = new Set<string>(),
): Array<{ cutId: string; weightedAfter: number }> {
  const active = cuts.filter((cut) => cut.kind !== 'response_weight' && !disabled.has(cut.id));
  return active.map((cut, index) => {
    const required = active.slice(0, index + 1).map((candidate) => candidate.id);
    const weightedAfter = events.reduce((total, event) => {
      const passes = required.every((id) => {
        const value = event.predicates[id];
        if (value === null || value === undefined) throw new Error(`missing atomic predicate: ${id}`);
        return value;
      });
      return total + (passes ? event.weight : 0);
    }, 0);
    return { cutId: cut.id, weightedAfter };
  });
}

export function vertexPassesCuts(vertex: EventVertex, cutIds: string[]): boolean {
  return cutIds.every((id) => {
    const value = vertex.predicates[id];
    if (value === undefined) throw new Error(`missing vertex predicate: ${id}`);
    return value;
  });
}

export function eventPassesCuts(
  event: EventRecord,
  cutIds: string[],
  cuts: CutDefinition[] = [],
  jetScale?: JetScaleContext,
): boolean {
  if (!event.valid_weight) return false;
  if (cutIds.includes('jet_selection')) {
    const passes = jetScale ? jetSelectionPasses(event, jetScale.jetLogic, jetScale.scale) : event.predicates.jet_selection;
    if (!passes) return false;
  }
  const cutById = new Map(cuts.map((cut) => [cut.id, cut]));
  const eventScopeIds = cutIds.filter((id) => id !== 'jet_selection' && cutById.get(id)?.predicate_scope === 'event');
  for (const id of eventScopeIds) {
    const value = event.predicates[id];
    if (value === undefined) throw new Error(`missing event-scoped predicate: ${id}`);
    if (!value) return false;
  }
  const vertexCuts = cutIds.filter((id) => id !== 'jet_selection' && !eventScopeIds.includes(id));
  return vertexCuts.length === 0 || event.vertices.some((vertex) => vertexPassesCuts(vertex, vertexCuts));
}

export function enabledBooleanCutIds(cuts: CutDefinition[], disabled: Set<string>): string[] {
  return cuts
    .filter((cut) => cut.kind !== 'response_weight' && cut.kind !== 'summary' && !disabled.has(cut.id))
    .map((cut) => cut.id);
}

export function recomputeEventCutflow(
  events: EventRecord[],
  cuts: CutDefinition[],
  disabled = new Set<string>(),
  jetScale?: JetScaleContext,
): Array<{ cutId: string; weightedBefore: number; weightedAfter: number; disabled: boolean }> {
  const denominator = events.reduce((sum, event) => sum + event.weight, 0);
  let previous = denominator;
  const active: string[] = [];
  const result = [];
  for (const cut of cuts) {
    if (cut.kind === 'response_weight' || cut.kind === 'summary') continue;
    const isDisabled = disabled.has(cut.id);
    if (!isDisabled) active.push(cut.id);
    const after = events.reduce(
      (sum, event) => sum + (eventPassesCuts(event, active, cuts, jetScale) ? event.weight : 0),
      0,
    );
    result.push({ cutId: cut.id, weightedBefore: previous, weightedAfter: after, disabled: isDisabled });
    previous = after;
  }
  return result;
}

export function booleanAcceptance(
  events: EventRecord[], cuts: CutDefinition[], disabled = new Set<string>(), jetScale?: JetScaleContext,
): { weightedPassed: number; weightedTotal: number; efficiencyPct: number } {
  const active = enabledBooleanCutIds(cuts, disabled);
  const weightedTotal = events.reduce((sum, event) => sum + event.weight, 0);
  const weightedPassed = events.reduce(
    (sum, event) => sum + (eventPassesCuts(event, active, cuts, jetScale) ? event.weight : 0), 0,
  );
  return {
    weightedPassed,
    weightedTotal,
    efficiencyPct: weightedTotal === 0 ? 0 : 100 * weightedPassed / weightedTotal,
  };
}
