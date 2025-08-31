import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, of } from 'rxjs';
import { map, catchError, switchMap, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { RAGQueryResponse, RAGQueryRequest } from '../models/rag.models';
import { HealthScoreInput, HealthScoreOutput } from '../models/analyzer.models';

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
  total_ms?: number;
}

// NEW: A/B test result interface
export interface ABTestResult {
  logmeal: AnalyzeResponse;
  gemini: AnalyzeResponse;
  winner: 'logmeal' | 'gemini' | 'tie';
  comparison: {
    logmeal_time: number;
    gemini_time: number;
    logmeal_confidence: number;
    gemini_confidence: number;
    logmeal_items: number;
    gemini_items: number;
  };
}

// NEW: Analysis options
export interface AnalysisOptions {
  use_logmeal?: boolean;
  enable_ab_test?: boolean;
  enable_fallback?: boolean;
  model?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiBase;

  constructor(private http: HttpClient) {}

  private analyze(
    file: File,
    options: AnalysisOptions = {}
  ): Observable<AnalyzeResponse> {
    const form = new FormData();
    form.append('image', file, file.name);
    form.append('model', options.model || 'gemini-2.5-pro');

    if (options.use_logmeal !== undefined) {
      form.append('use_logmeal', options.use_logmeal.toString());
    }

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

  // NEW: A/B test both services
  analyzeABTest(
    file: File,
    model = 'gemini-2.5-pro'
  ): Observable<ABTestResult> {
    const logmealRequest = this.analyze(file, { use_logmeal: true, model });
    const geminiRequest = this.analyze(file, { use_logmeal: false, model });

    return logmealRequest.pipe(
      switchMap((logmealResult) =>
        geminiRequest.pipe(
          map((geminiResult) => {
            const logmealTime = logmealResult.total_ms || 0;
            const geminiTime = geminiResult.total_ms || 0;
            const logmealConf = logmealResult.grams_confidence || 0;
            const geminiConf = geminiResult.grams_confidence || 0;
            const logmealItems = logmealResult.items_grams?.length || 0;
            const geminiItems = geminiResult.items_grams?.length || 0;

            // Determine winner based on confidence and speed
            let winner: 'logmeal' | 'gemini' | 'tie' = 'tie';
            if (logmealConf > geminiConf && logmealTime <= geminiTime * 1.5) {
              winner = 'logmeal';
            } else if (
              geminiConf > logmealConf &&
              geminiTime <= logmealTime * 1.5
            ) {
              winner = 'gemini';
            } else if (logmealTime < geminiTime * 0.7) {
              winner = 'logmeal';
            } else if (geminiTime < logmealTime * 0.7) {
              winner = 'gemini';
            }

            return {
              logmeal: logmealResult,
              gemini: geminiResult,
              winner,
              comparison: {
                logmeal_time: logmealTime,
                gemini_time: geminiTime,
                logmeal_confidence: logmealConf,
                gemini_confidence: geminiConf,
                logmeal_items: logmealItems,
                gemini_items: geminiItems,
              },
            };
          })
        )
      ),
      catchError((err: HttpErrorResponse) =>
        throwError(() => err.error || { error: 'ab_test_failed' })
      )
    );
  }

  // NEW: Analyze with fallback (try LogMeal first, fallback to Gemini)
  analyzeWithFallback(
    file: File,
    model = 'gemini-2.5-pro'
  ): Observable<AnalyzeResponse> {
    return this.analyze(file, { use_logmeal: true, model }).pipe(
      catchError((logmealError) => {
        console.log('LogMeal failed, falling back to Gemini:', logmealError);
        return this.analyze(file, { use_logmeal: false, model });
      })
    );
  }

  // RAG Query method
  queryRAG(request: RAGQueryRequest): Observable<RAGQueryResponse> {
    const params = new URLSearchParams();
    params.append('i', request.ingredients.join(', '));
    if (request.top) {
      params.append('top', request.top.toString());
    }
    if (request.mode) {
      params.append('mode', request.mode);
    }

    const url = `${this.base}/query?${params.toString()}`;

    return this.http.get<RAGQueryResponse>(url).pipe(
      catchError((err: HttpErrorResponse) => {
        return throwError(() => err.error || { error: 'rag_query_failed' });
      })
    );
  }

  // Recipe Details method (for strict mode)
  getRecipeDetails(
    dishName: string,
    ingredients: string[]
  ): Observable<{ dish_name: string; ingredients: string[]; sources: any[] }> {
    const params = new URLSearchParams();
    params.append('dish_name', dishName);
    if (ingredients.length > 0) {
      params.append('ingredients', ingredients.join(', '));
    }

    const url = `${this.base}/recipe_details?${params.toString()}`;

    return this.http
      .get<{ dish_name: string; ingredients: string[]; sources: any[] }>(url)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          return throwError(
            () => err.error || { error: 'recipe_details_failed' }
          );
        })
      );
  }

  // NEW: Health Score method
  getHealthScore(input: HealthScoreInput): Observable<HealthScoreOutput> {
    return this.http
      .post<HealthScoreOutput>(`${this.base}/health-score`, input)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          return throwError(
            () => err.error || { error: 'health_score_failed' }
          );
        })
      );
  }
}
