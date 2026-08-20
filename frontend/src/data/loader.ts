import { DatasetError, validateDetectorGeometry, validateDocuments, validateEventsDocument, type DetectorGeometry, type ViewerDataset } from './schema';

export interface DatasetCatalogEntry {
  dataset_id: string;
  labels: { es: string; en: string };
  description: { es: string; en: string };
}

export type LoadState =
  | { status: 'loading'; datasetId: string }
  | { status: 'valid'; dataset: ViewerDataset }
  | { status: 'unsupported_schema_version'; error: DatasetError }
  | { status: 'missing_required_file'; error: DatasetError }
  | { status: 'invalid_schema'; error: DatasetError };

async function fetchJson(fetcher: typeof fetch, url: string, datasetId: string, file: string): Promise<unknown> {
  const response = await fetcher(url);
  if (!response.ok) {
    throw new DatasetError(datasetId, file, '$', 'HTTP 200', `HTTP ${response.status}`);
  }
  try {
    return await response.json();
  } catch (error) {
    throw new DatasetError(datasetId, file, '$', 'valid JSON', String(error));
  }
}

export async function loadDataset(datasetId: string, fetcher: typeof fetch = fetch): Promise<LoadState> {
  const base = `/data/${encodeURIComponent(datasetId)}`;
  try {
    const [manifest, cuts, summary] = await Promise.all([
      fetchJson(fetcher, `${base}/manifest.json`, datasetId, 'manifest.json'),
      fetchJson(fetcher, `${base}/cuts.json`, datasetId, 'cuts.json'),
      fetchJson(fetcher, `${base}/summary.json`, datasetId, 'summary.json'),
    ]);
    const dataset = validateDocuments(manifest, cuts, summary, datasetId);
    const needsEvents = dataset.manifest.capabilities.atomic_event_cuts
      || dataset.manifest.capabilities.dv_xyz
      || dataset.manifest.capabilities.jet_observables;
    if (needsEvents) {
      const eventsValue = await fetchJson(fetcher, `${base}/events.json`, datasetId, 'events.json');
      dataset.events = validateEventsDocument(eventsValue, dataset);
    }
    if (dataset.manifest.geometry_pack) {
      const geometryValue = await fetchJson(fetcher, `${base}/geometry_events.json`, datasetId, 'geometry_events.json');
      // geometry_events.json has real coordinates even when the primary
      // events.json (and therefore dataset.manifest.capabilities) truthfully
      // does not; validate it against a capabilities override, mirroring
      // preprocess/geometry_replay.py's geometry_manifest override.
      const geometryDatasetView: ViewerDataset = {
        ...dataset,
        manifest: { ...dataset.manifest, capabilities: { ...dataset.manifest.capabilities, dv_radial: true, dv_xyz: true } },
      };
      dataset.geometryEvents = validateEventsDocument(
        geometryValue,
        geometryDatasetView,
        dataset.manifest.geometry_pack.event_count,
        'geometry_events.json',
      );
    }
    return { status: 'valid', dataset };
  } catch (error) {
    const datasetError = error instanceof DatasetError
      ? error
      : new DatasetError(datasetId, 'unknown', '$', 'loadable dataset', String(error));
    if (datasetError.field === 'schema_version') {
      return { status: 'unsupported_schema_version', error: datasetError };
    }
    if (String(datasetError.received).startsWith('HTTP 404')) {
      return { status: 'missing_required_file', error: datasetError };
    }
    return { status: 'invalid_schema', error: datasetError };
  }
}

export async function loadDatasetCatalog(fetcher: typeof fetch = fetch): Promise<DatasetCatalogEntry[]> {
  const response = await fetcher('/data/catalog.json');
  if (!response.ok) throw new Error(`dataset catalog: expected HTTP 200, received HTTP ${response.status}`);
  const value: unknown = await response.json();
  if (!Array.isArray(value)) throw new Error('dataset catalog: expected array');
  return value.map((raw, index) => {
    if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) throw new Error(`dataset catalog[${index}]: expected object`);
    const entry = raw as Record<string, unknown>;
    const labels = entry.labels as Record<string, unknown> | undefined;
    const description = entry.description as Record<string, unknown> | undefined;
    if (typeof entry.dataset_id !== 'string' || typeof labels?.es !== 'string' || typeof labels?.en !== 'string'
      || typeof description?.es !== 'string' || typeof description?.en !== 'string') {
      throw new Error(`dataset catalog[${index}]: invalid bilingual entry`);
    }
    return entry as unknown as DatasetCatalogEntry;
  });
}

export async function loadDetectorGeometry(fetcher: typeof fetch = fetch): Promise<DetectorGeometry> {
  return validateDetectorGeometry(await fetchJson(fetcher, '/data/detector_geometry.json', 'detector-geometry', 'detector_geometry.json'));
}
