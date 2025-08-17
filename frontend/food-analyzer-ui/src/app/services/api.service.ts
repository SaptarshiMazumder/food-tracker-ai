import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface AnalyzeItemGrams {
  name: string;
  grams: number;
  note?: string;
}

export interface AnalyzeItemKcal {
  name: string;
  kcal: number;
  method?: string;
}

export interface AnalyzeNutritionItem {
  name: string;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  method?: string;
}

export interface AnalyzeResponse {
  // recognition
  dish: string;
  dish_confidence: number;
  ingredients_detected: string[];

  // grams estimation
  items_grams: AnalyzeItemGrams[];
  total_grams: number;
  grams_confidence: number;

  // nutrition (LLM)
  items_nutrition?: AnalyzeNutritionItem[]; // NEW
  items_kcal?: AnalyzeItemKcal[]; // keep for back-compat
  total_kcal: number;
  total_protein_g?: number; // NEW
  total_carbs_g?: number; // NEW
  total_fat_g?: number; // NEW
  kcal_confidence: number;

  // misc
  notes?: string;
  overlay_url?: string | null;
  image_url?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiBase;

  constructor(private http: HttpClient) {}

  analyze(file: File, model = 'gemini-2.5-pro'): Observable<AnalyzeResponse> {
    const form = new FormData();
    form.append('image', file, file.name);
    form.append('model', model);

    return this.http.post<AnalyzeResponse>(`${this.base}/analyze`, form).pipe(
      map((res) => {
        const absolutize = (u?: string | null) =>
          u ? (u.startsWith('http') ? u : `${this.base}${u}`) : undefined;
        return {
          ...res,
          overlay_url: absolutize(res.overlay_url),
          image_url: absolutize(res.image_url),
        };
      }),
      catchError((err: HttpErrorResponse) =>
        throwError(() => err.error || { error: 'request_failed' })
      )
    );
  }
}
