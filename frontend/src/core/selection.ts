import type { Capabilities, CutDefinition, EventRecord, EventVertex } from '../data/schema';

export interface AtomicEvent {
  weight: number;
  predicates: Record<string, boolean | null>;
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

export function eventPassesCuts(event: EventRecord, cutIds: string[]): boolean {
  if (!event.valid_weight) return false;
  if (cutIds.includes('jet_selection') && !event.predicates.jet_selection) return false;
  const vertexCuts = cutIds.filter((id) => id !== 'jet_selection');
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
      (sum, event) => sum + (eventPassesCuts(event, active) ? event.weight : 0),
      0,
    );
    result.push({ cutId: cut.id, weightedBefore: previous, weightedAfter: after, disabled: isDisabled });
    previous = after;
  }
  return result;
}

export function booleanAcceptance(
  events: EventRecord[], cuts: CutDefinition[], disabled = new Set<string>(),
): { weightedPassed: number; weightedTotal: number; efficiencyPct: number } {
  const active = enabledBooleanCutIds(cuts, disabled);
  const weightedTotal = events.reduce((sum, event) => sum + event.weight, 0);
  const weightedPassed = events.reduce(
    (sum, event) => sum + (eventPassesCuts(event, active) ? event.weight : 0), 0,
  );
  return {
    weightedPassed,
    weightedTotal,
    efficiencyPct: weightedTotal === 0 ? 0 : 100 * weightedPassed / weightedTotal,
  };
}
