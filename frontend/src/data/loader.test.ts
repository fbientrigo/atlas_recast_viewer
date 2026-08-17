import { describe, expect, it } from 'vitest';
import manifest from '../../../public/data/reference/manifest.json';
import cuts from '../../../public/data/reference/cuts.json';
import summary from '../../../public/data/reference/summary.json';
import localManifest from '../../../public/data/local-reference/manifest.json';
import localCuts from '../../../public/data/local-reference/cuts.json';
import localSummary from '../../../public/data/local-reference/summary.json';
import localEvents from '../../../public/data/local-reference/events.json';
import detectorGeometry from '../../../public/data/detector_geometry.json';
import { DatasetError, validateDetectorGeometry, validateDocuments, validateEventsDocument } from './schema';
import { loadDataset } from './loader';

describe('dataset loader', () => {
  it('loads the reference contract and preserves null', () => {
    const dataset = validateDocuments(manifest, cuts, summary, 'reference');
    expect(dataset.summary.cutflow.stages[0].reference.atlas_parametric_pct).toBeNull();
  });

  it('rejects incompatible schema versions', () => {
    const incompatible = { ...manifest, schema_version: 'viewer.dataset.v2' };
    expect(() => validateDocuments(incompatible, cuts, summary, 'reference')).toThrow(DatasetError);
  });

  it('rejects an invalid cut-geometry boundary', () => {
    const malformed = structuredClone(cuts);
    malformed.cuts[1].geometry_overlay!.r_max_mm = -300;
    expect(() => validateDocuments(manifest, malformed, summary, 'reference')).toThrow(/geometry_overlay.r_max_mm/);
  });

  it('reports a missing required file as its own load state', async () => {
    const fetcher = async () => new Response('', { status: 404 });
    const result = await loadDataset('missing', fetcher as typeof fetch);
    expect(result.status).toBe('missing_required_file');
  });

  it('validates the instrumented event pack without coercing geometry', () => {
    const dataset = validateDocuments(localManifest, localCuts, localSummary, 'local-reference');
    const events = validateEventsDocument(localEvents, dataset);
    expect(events.events).toHaveLength(500);
    expect(events.events[0].vertices[0].r_mm).toBeGreaterThan(0);
    expect(Number.isFinite(events.events[0].vertices[0].tracks[0].z_prod_mm)).toBe(true);
  });

  it('keeps detector hardware, analysis boundaries, and response bins distinct', () => {
    const geometry = validateDetectorGeometry(detectorGeometry);
    expect(new Set(geometry.landmarks.map((item) => item.kind))).toEqual(
      new Set(['detector_hardware', 'analysis_boundary', 'response_bin']),
    );
    expect(geometry.landmarks.find((item) => item.id === 'sct_barrel_1')?.radius_mm).toBe(299);
    expect(geometry.landmarks.find((item) => item.id === 'dv_max_r')?.radius_mm).toBe(300);
    expect(geometry.landmarks.every((item) => item.relevance_es && item.relevance_en)).toBe(true);
  });
});
