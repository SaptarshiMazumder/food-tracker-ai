import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  ApiResponse,
  UiItem,
  AnalyzeNutritionItem,
  UiTotals,
} from '../models/analyzer.models';

type StreamEvent =
  | { phase: 'recognize'; data: any }
  | { phase: 'ing_quant'; data: any }
  | { phase: 'calories'; data: any }
  | { phase: 'done'; data: ApiResponse }
  | { phase: 'error'; data: any };

@Injectable({ providedIn: 'root' })
export class FoodAnalyzerService {
  constructor(private http: HttpClient) {}

  // Legacy non-streaming (kept for fallback)
  analyze(files: File[], model = 'gemini-2.5-pro'): Observable<ApiResponse> {
    const fd = new FormData();
    files.forEach((f) => fd.append('image', f));
    fd.append('model', model);
    return this.http
      .post<ApiResponse>(`${environment.apiBase}/analyze`, fd)
      .pipe(
        map((resp) => ({
          ...resp,
          timings: resp.timings ?? {},
          total_ms: resp.total_ms ?? 0,
        }))
      );
  }

  // NEW: streaming flow with SSE
  analyzeStream(
    files: File[],
    model = 'gemini-2.5-pro'
  ): Observable<StreamEvent> {
    const fd = new FormData();
    files.forEach((f) => fd.append('image', f));
    fd.append('model', model);

    return new Observable<StreamEvent>((observer) => {
      // 1) Upload files to get a job_id
      this.http
        .post<{ job_id: string }>(`${environment.apiBase}/upload`, fd)
        .subscribe({
          next: ({ job_id }) => {
            const url = `${
              environment.apiBase
            }/analyze_sse?job_id=${encodeURIComponent(
              job_id
            )}&model=${encodeURIComponent(model)}`;
            const es = new EventSource(url);

            const onClose = () => {
              try {
                es.close();
              } catch {}
            };

            es.addEventListener('recognize', (e: MessageEvent) => {
              observer.next({ phase: 'recognize', data: JSON.parse(e.data) });
            });
            es.addEventListener('ing_quant', (e: MessageEvent) => {
              observer.next({ phase: 'ing_quant', data: JSON.parse(e.data) });
            });
            es.addEventListener('calories', (e: MessageEvent) => {
              observer.next({ phase: 'calories', data: JSON.parse(e.data) });
            });
            es.addEventListener('done', (e: MessageEvent) => {
              observer.next({ phase: 'done', data: JSON.parse(e.data) });
              observer.complete();
              onClose();
            });
            es.addEventListener('error', (e: MessageEvent) => {
              try {
                observer.next({ phase: 'error', data: JSON.parse(e.data) });
              } catch {}
              observer.error(e);
              onClose();
            });
            // Some servers send unnamed 'message' events — handle just in case
            es.onmessage = (e) => {
              try {
                const d = JSON.parse(e.data);
                if (d && d.event && d.data) {
                  observer.next({ phase: d.event, data: d.data } as any);
                }
              } catch {}
            };
          },
          error: (err) => observer.error(err),
        });
    });
  }

  /** Build UI items (densities + slider config) from API response */
  buildUiItems(resp: ApiResponse): UiItem[] {
    const gramsList = resp.items_grams || [];
    const nutrList = resp.items_nutrition || [];
    const densityMap = new Map(
      (resp.items_density || []).map((d) => [d.name.toLowerCase(), d])
    );
    const safePerG = (num: number, den: number) => (den > 0 ? num / den : 0);

    return gramsList.map((g) => {
      const nameL = g.name.toLowerCase();
      const n = nutrList.find((x) => x.name.toLowerCase() === nameL) as
        | AnalyzeNutritionItem
        | undefined;

      const kcalPerG =
        densityMap.get(nameL)?.kcal_per_g ?? safePerG(n?.kcal ?? 0, g.grams);
      const proteinPerG =
        densityMap.get(nameL)?.protein_per_g ??
        safePerG(n?.protein_g ?? 0, g.grams);
      const carbsPerG =
        densityMap.get(nameL)?.carbs_per_g ??
        safePerG(n?.carbs_g ?? 0, g.grams);
      const fatPerG =
        densityMap.get(nameL)?.fat_per_g ?? safePerG(n?.fat_g ?? 0, g.grams);

      const base = g.grams || 0;
      const min = Math.max(0, Math.floor(base * 0.2));
      const max = Math.max(20, Math.ceil(base * 2.2));
      const step = 1;

      return {
        name: g.name,
        baseGrams: base,
        min,
        max,
        step,
        kcalPerG,
        proteinPerG,
        carbsPerG,
        fatPerG,
        computedKcal: Math.round(base * kcalPerG),
        computedProtein: +(base * proteinPerG).toFixed(1),
        computedCarbs: +(base * carbsPerG).toFixed(1),
        computedFat: +(base * fatPerG).toFixed(1),
        note: g.note,
      };
    });
  }

  computeTotals(ui: UiItem[], currentGrams: number[]): UiTotals {
    let g = 0,
      k = 0,
      p = 0,
      c = 0,
      f = 0;
    ui.forEach((row, i) => {
      const grams = currentGrams[i] ?? row.baseGrams;
      g += grams;
      k += grams * row.kcalPerG;
      p += grams * row.proteinPerG;
      c += grams * row.carbsPerG;
      f += grams * row.fatPerG;
    });
    return {
      grams: Math.round(g),
      kcal: Math.round(k),
      protein: +p.toFixed(1),
      carbs: +c.toFixed(1),
      fat: +f.toFixed(1),
    };
  }
}
