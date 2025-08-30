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
  error?: string;
  msg?: string;
}

export async function uploadAnalyzeImage(uri: string, options?: { model?: string; useLogmeal?: boolean }): Promise<AnalysisResponse> {
  const base = getBaseUrl();
  const form = new FormData();
  const filename = uri.split('/').pop() || 'image.jpg';
  const ext = (filename.split('.').pop() || 'jpg').toLowerCase();
  const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';

  // React Native's fetch supports file-like objects with uri, but TS types don't.
  // Cast to any to avoid incorrect DOM FormData typing issues in RN.
  form.append('image', { uri, name: filename, type: mime } as any);
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


