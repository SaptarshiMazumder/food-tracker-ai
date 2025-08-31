import RNEventSource from 'react-native-event-source';
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

const getBaseUrl = () => {
  // Read from process.env style at runtime with Expo (via app config or env plugin)
  const url = process.env.EXPO_PUBLIC_API_BASE_URL;
  return url || 'http://10.0.2.2:5000'; // Android emulator default to host machine
};

export async function apiRequest<T>(path: string, options?: { method?: HttpMethod; body?: any; headers?: Record<string, string> }) {
  const method = options?.method || 'GET';
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };
  const body = options?.body ? JSON.stringify(options.body) : undefined;
  const base = getBaseUrl();
  const response = await fetch(`${base}${path}`, { method, headers, body });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}

export interface AnalysisResponse {
  dish?: string;
  dish_confidence?: number;
  ingredients_detected?: string[];
  items_grams?: Array<{ name: string; grams: number; note?: string }>;
  items_nutrition?: Array<{ name: string; kcal: number; protein_g: number; carbs_g: number; fat_g: number; method?: string }>; 
  items_kcal?: Array<{ name: string; kcal: number; method?: string }>;
  items_density?: Array<{ name: string; kcal_per_g: number; protein_per_g: number; carbs_per_g: number; fat_per_g: number }>;
  total_kcal?: number;
  total_protein_g?: number;
  total_carbs_g?: number;
  total_fat_g?: number;
  grams_confidence?: number;
  kcal_confidence?: number;
  total_grams?: number;
  total_ms?: number;
  timings?: Record<string, number>;
  notes?: string;
  // Optional health score result from backend
  health_score?: HealthScoreOutput;
  error?: string;
  msg?: string;
}

// Health Score types and API
export interface HealthScoreInput {
  total_kcal: number;
  total_grams: number;
  total_fat_g: number;
  total_protein_g: number;
  items_grams: Array<{ name: string; grams: number }>;
  kcal_confidence: number;
  use_confidence_dampen: boolean;
}

export interface HealthComponentScores {
  energy_density: number;
  protein_density: number;
  fat_balance: number;
  carb_quality: number;
  sodium_proxy: number;
  whole_foods: number;
}

export interface HealthScoreOutput {
  health_score: number; // 1..10
  component_scores: HealthComponentScores;
  weights: { [k: string]: number };
  drivers_positive: string[];
  drivers_negative: string[];
  debug: { [k: string]: number };
  classification: Array<{ name: string; category: string }>;
}

export async function uploadAnalyzeImage(uriOrUris: string | string[], options?: { model?: string; useLogmeal?: boolean }): Promise<AnalysisResponse> {
  const base = getBaseUrl();
  const form = new FormData();
  const uris = Array.isArray(uriOrUris) ? uriOrUris : [uriOrUris];
  for (const uri of uris) {
    const filename = uri.split('/').pop() || 'image.jpg';
    const ext = (filename.split('.').pop() || 'jpg').toLowerCase();
    const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';
    form.append('image', { uri, name: filename, type: mime } as any);
  }
  if (options?.model) form.append('model', options.model);
  if (typeof options?.useLogmeal !== 'undefined') form.append('use_logmeal', String(options.useLogmeal));

  const res = await fetch(`${base}/analyze`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      // Don't set Content-Type; let fetch set multipart boundary
    } as any,
    body: form as any,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return (await res.json()) as AnalysisResponse;
}

export type StreamEvent =
  | { phase: 'recognize'; data: any }
  | { phase: 'ing_quant'; data: any }
  | { phase: 'calories'; data: any }
  | { phase: 'done'; data: AnalysisResponse }
  | { phase: 'error'; data: any };

export async function analyzeStream(
  uriOrUris: string | string[],
  opts: { model?: string; useLogmeal?: boolean } = {}
): Promise<AsyncGenerator<StreamEvent, void, unknown>> {
  const base = getBaseUrl();
  const form = new FormData();
  const uris = Array.isArray(uriOrUris) ? uriOrUris : [uriOrUris];
  for (const uri of uris) {
    const filename = uri.split('/').pop() || 'image.jpg';
    const ext = (filename.split('.').pop() || 'jpg').toLowerCase();
    const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';
    form.append('image', { uri, name: filename, type: mime } as any);
  }
  form.append('model', opts.model || 'gemini-2.5-pro');
  if (typeof opts.useLogmeal !== 'undefined') form.append('use_logmeal', String(opts.useLogmeal));

  const uploadRes = await fetch(`${base}/upload`, { method: 'POST', body: form as any });
  if (!uploadRes.ok) {
    throw new Error(`Upload failed: ${uploadRes.status} ${await uploadRes.text()}`);
  }
  const { job_id } = (await uploadRes.json()) as { job_id: string };

  const query = new URLSearchParams({ job_id, model: opts.model || 'gemini-2.5-pro' });
  if (typeof opts.useLogmeal !== 'undefined') query.set('use_logmeal', String(opts.useLogmeal));
  const url = `${base}/analyze_sse?${query.toString()}`;
  const es = new RNEventSource(url);

  async function* iterator() {
    const queue: StreamEvent[] = [];
    let done = false;
    const push = (ev: StreamEvent) => queue.push(ev);

    es.addEventListener('recognize', (e: any) => push({ phase: 'recognize', data: JSON.parse(e.data) }));
    es.addEventListener('ing_quant', (e: any) => push({ phase: 'ing_quant', data: JSON.parse(e.data) }));
    es.addEventListener('calories', (e: any) => push({ phase: 'calories', data: JSON.parse(e.data) }));
    es.addEventListener('done', (e: any) => {
      push({ phase: 'done', data: JSON.parse(e.data) });
      done = true;
      try { es.close(); } catch {}
    });
    es.addEventListener('error', (e: any) => push({ phase: 'error', data: e }));

    while (!done || queue.length) {
      if (queue.length) {
        yield queue.shift() as StreamEvent;
      } else {
        await new Promise((r) => setTimeout(r, 50));
      }
    }
  }

  return iterator();
}

export async function getHealthScore(input: HealthScoreInput): Promise<HealthScoreOutput> {
  return apiRequest<HealthScoreOutput>('/health-score', { method: 'POST', body: input });
}


