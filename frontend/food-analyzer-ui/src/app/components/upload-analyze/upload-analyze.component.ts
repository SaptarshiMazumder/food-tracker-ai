import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiResponse, UiItem, UiTotals } from '../../models/analyzer.models';
import { FoodAnalyzerService } from '../../services/food-analyzer.service';
import { ApiService, AnalysisOptions } from '../../services/api.service';
import { MealLoggerService } from '../../services/meal-logger.service';
import { UploadInputComponent } from '../upload-input/upload-input.component';
import { IngredientTableComponent } from '../ingredient-table/ingredient-table.component';
import { TimingsPanelComponent } from '../timings-panel/timings-panel.component';

export type AnalysisMode = 'logmeal' | 'gemini';

@Component({
  selector: 'app-upload-analyze',
  standalone: true,
  imports: [
    CommonModule,
    UploadInputComponent,
    IngredientTableComponent,
    TimingsPanelComponent,
  ],
  templateUrl: 'upload-analyze.component.html',
  styleUrls: ['upload-analyze.component.css'],
})
export class UploadAnalyzeComponent {
  loading = false;
  started = false; // NEW: hide UI until user starts a run
  errorMsg = '';
  showMealLoggedNotification = false;

  // progressive state
  result: Partial<ApiResponse> = {};
  uiItems: UiItem[] = [];
  totals: UiTotals | null = null;

  // phase flags
  gotRecognize = false;
  gotIngr = false;
  gotCalories = false;

  // NEW: Analysis mode and options
  analysisMode: AnalysisMode = 'gemini';
  currentService: 'logmeal' | 'gemini' | null = null;

  constructor(
    private svc: FoodAnalyzerService,
    private apiService: ApiService,
    private mealLoggerService: MealLoggerService,
    private cdr: ChangeDetectorRef
  ) {}

  onAnalyze(req: { files: File[]; model: string }) {
    this.resetPage(); // clears previous run
    this.started = true; // mark that a run has started
    this.loading = true;
    console.log(
      'Analysis started - started:',
      this.started,
      'loading:',
      this.loading
    );

    this.runSingleService(req.files, req.model);
  }

  private runSingleService(files: File[], model: string) {
    const options: AnalysisOptions = {
      use_logmeal: this.analysisMode === 'logmeal',
      model,
    };

    this.currentService = this.analysisMode as 'logmeal' | 'gemini';

    this.svc.analyzeStream(files, model, options).subscribe({
      next: (evt) => {
        console.log('Received event from service:', evt);
        this.handleStreamEvent(evt);
      },
      error: (err) => {
        console.log('Error from service:', err);
        this.handleError(err);
      },
    });
  }

  private handleStreamEvent(evt: any) {
    console.log('Handling stream event:', evt.phase, evt.data);

    if (evt.phase === 'recognize') {
      console.log('Processing recognize event');
      this.gotRecognize = true;
      const d = evt.data || {};
      this.result.dish = d.dish;
      this.result.dish_confidence = d.dish_confidence;
      this.result.ingredients_detected = d.ingredients_detected || [];
      this.result.timings = {
        ...(this.result.timings || {}),
        ...(d.timings || {}),
      };
      console.log(
        'After recognize - gotRecognize:',
        this.gotRecognize,
        'result:',
        this.result
      );
      this.cdr.detectChanges(); // Trigger change detection
    } else if (evt.phase === 'ing_quant') {
      console.log('Processing ing_quant event');
      this.gotIngr = true;
      const d = evt.data || {};
      this.result.items_grams = d.items_grams || [];
      this.result.total_grams = d.total_grams || 0;
      this.result.grams_confidence = d.grams_confidence || 0;
      this.result.notes = d.notes || this.result.notes;
      this.result.timings = {
        ...(this.result.timings || {}),
        ...(d.timings || {}),
      };
      console.log(
        'After ing_quant - gotIngr:',
        this.gotIngr,
        'total_grams:',
        this.result.total_grams
      );
      this.cdr.detectChanges(); // Trigger change detection
    } else if (evt.phase === 'calories') {
      console.log('Processing calories event');
      this.gotCalories = true;
      const d = evt.data || {};
      this.result.items_nutrition = d.items_nutrition || [];
      this.result.items_kcal = d.items_kcal || [];
      this.result.items_density = d.items_density || [];
      this.result.total_kcal = d.total_kcal || 0;
      this.result.total_protein_g = d.total_protein_g || 0;
      this.result.total_carbs_g = d.total_carbs_g || 0;
      this.result.total_fat_g = d.total_fat_g || 0;
      this.result.kcal_confidence = d.kcal_confidence || 0;
      this.result.notes = d.notes || this.result.notes;
      this.result.timings = {
        ...(this.result.timings || {}),
        ...(d.timings || {}),
      };

      if (this.result.items_grams && this.result.items_nutrition) {
        this.uiItems = this.svc.buildUiItems(this.result as ApiResponse);
        this.totals = this.svc.computeTotals(
          this.uiItems,
          this.uiItems.map((u) => u.baseGrams)
        );
      }
      console.log(
        'After calories - gotCalories:',
        this.gotCalories,
        'total_kcal:',
        this.result.total_kcal,
        'uiItems length:',
        this.uiItems.length
      );
      this.cdr.detectChanges(); // Trigger change detection
    } else if (evt.phase === 'done') {
      console.log('Processing done event');
      const d = evt.data as ApiResponse;
      this.result = { ...this.result, ...d };
      if (!this.uiItems.length && d.items_grams && d.items_nutrition) {
        this.uiItems = this.svc.buildUiItems(d);
        this.totals = this.svc.computeTotals(
          this.uiItems,
          this.uiItems.map((u) => u.baseGrams)
        );
      }

      // Log the meal automatically when analysis is complete
      this.logMeal();

      this.loading = false;
      this.showMealLoggedNotification = true;
      setTimeout(() => {
        this.showMealLoggedNotification = false;
      }, 3000);
      console.log(
        'After done - loading:',
        this.loading,
        'result keys:',
        Object.keys(this.result)
      );
      this.cdr.detectChanges(); // Trigger change detection
    } else if (evt.phase === 'error') {
      console.log('Processing error event');
      this.errorMsg =
        (evt.data && (evt.data.msg || evt.data.error)) || 'Streaming error';
      this.loading = false;
      this.cdr.detectChanges(); // Trigger change detection
    }
  }

  private handleError(err: any) {
    this.errorMsg =
      (err?.error && (err.error.msg || err.error.error)) ||
      err.message ||
      'Analyze failed';
    this.loading = false;
  }

  onClear() {
    this.resetPage();
  }

  onTotals(t: UiTotals) {
    this.totals = t;
  }

  // NEW: Get service display name
  getServiceDisplayName(): string {
    if (this.currentService) {
      return this.currentService === 'logmeal' ? 'Model A' : 'Model B';
    }
    return this.analysisMode === 'logmeal' ? 'Model A' : 'Model B';
  }

  private resetPage() {
    this.loading = false;
    this.started = false; // NEW: hide result panel on first load/after clear
    this.errorMsg = '';
    this.showMealLoggedNotification = false;
    this.result = {};
    this.uiItems = [];
    this.totals = null;
    this.gotRecognize = this.gotIngr = this.gotCalories = false;
    this.currentService = null;
  }

  /**
   * Log the current meal to the meal logger service
   */
  private logMeal(): void {
    if (!this.result.dish || !this.currentService) {
      console.log('Cannot log meal: missing dish or service information');
      return;
    }

    try {
      const loggedMeal = this.mealLoggerService.logMeal(
        this.result as any,
        this.analysisMode,
        this.currentService,
        (this.result as any).image_url,
        (this.result as any).overlay_url
      );

      console.log('Meal logged successfully:', loggedMeal);
    } catch (error) {
      console.error('Error logging meal:', error);
    }
  }
}
