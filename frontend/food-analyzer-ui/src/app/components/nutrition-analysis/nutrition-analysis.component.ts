import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, AnalyzeResponse } from '../../services/api.service';
import { FoodAnalyzerService } from '../../services/food-analyzer.service';
import { MealLoggerService } from '../../services/meal-logger.service';
import { IngredientTableComponent } from '../ingredient-table/ingredient-table.component';
import { TimingsPanelComponent } from '../timings-panel/timings-panel.component';
import {
  UiItem,
  UiTotals,
  HealthScoreInput,
} from '../../models/analyzer.models';

@Component({
  selector: 'app-nutrition-analysis',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IngredientTableComponent,
    TimingsPanelComponent,
  ],
  templateUrl: './nutrition-analysis.component.html',
  styleUrls: ['./nutrition-analysis.component.css'],
})
export class NutritionAnalysisComponent {
  hint: string = '';
  isLoading: boolean = false;
  started: boolean = false;
  error: string | null = null;
  showMealLoggedNotification = false;
  showHealthScoreNotification = false;

  // Result structure matching the analyzer
  result: Partial<AnalyzeResponse> = {};
  uiItems: UiItem[] = [];
  totals: UiTotals | null = null;

  // Phase flags
  gotRecognize = false;
  gotIngr = false;
  gotCalories = false;
  gotHealthScore = false;

  constructor(
    private apiService: ApiService,
    private svc: FoodAnalyzerService,
    private mealLoggerService: MealLoggerService,
    private cdr: ChangeDetectorRef
  ) {}

  analyzeNutrition() {
    console.log('[DEBUG] analyzeNutrition called with hint:', this.hint);
    console.log('[DEBUG] hint.trim():', this.hint.trim());
    console.log('[DEBUG] hint.length:', this.hint.length);

    if (!this.hint.trim()) {
      this.error = 'Please enter a food description or dish name';
      console.log('[DEBUG] Hint is empty, returning early');
      return;
    }

    // Store the hint before resetting, since resetPage() clears it
    const hintToAnalyze = this.hint.trim();

    this.resetPageButKeepHint();
    this.started = true;
    this.isLoading = true;
    this.error = null;

    console.log('[DEBUG] Calling API with hint:', hintToAnalyze);
    this.apiService.analyzeNutrition(hintToAnalyze).subscribe({
      next: (response: AnalyzeResponse) => {
        // Simulate the streaming behavior by setting all phases at once
        this.handleNutritionResponse(response);
        this.isLoading = false;
      },
      error: (error: any) => {
        this.error = error.msg || 'Failed to analyze nutrition';
        this.isLoading = false;
      },
    });
  }

  private handleNutritionResponse(response: AnalyzeResponse) {
    // Set all phases to true since we get the complete response at once
    this.gotRecognize = true;
    this.gotIngr = true;
    this.gotCalories = true;

    // Set the result data
    this.result = response;

    // Build UI items for the ingredient table
    if (this.result.items_grams && this.result.items_nutrition) {
      this.uiItems = this.svc.buildUiItems(this.result as any);
      this.totals = this.svc.computeTotals(
        this.uiItems,
        this.uiItems.map((u) => u.baseGrams)
      );
    }

    // Log the meal automatically
    this.logMeal();

    // Get health score
    this.getHealthScore();

    this.showMealLoggedNotification = true;
    setTimeout(() => {
      this.showMealLoggedNotification = false;
    }, 3000);

    this.cdr.detectChanges();
  }

  clearResults() {
    this.resetPage();
  }

  onTotals(t: UiTotals) {
    this.totals = t;
  }

  private resetPage() {
    this.isLoading = false;
    this.started = false;
    this.error = null;
    this.showMealLoggedNotification = false;
    this.showHealthScoreNotification = false;
    this.result = {};
    this.uiItems = [];
    this.totals = null;
    this.gotRecognize =
      this.gotIngr =
      this.gotCalories =
      this.gotHealthScore =
        false;
    this.hint = '';
  }

  private resetPageButKeepHint() {
    this.isLoading = false;
    this.started = false;
    this.error = null;
    this.showMealLoggedNotification = false;
    this.showHealthScoreNotification = false;
    this.result = {};
    this.uiItems = [];
    this.totals = null;
    this.gotRecognize =
      this.gotIngr =
      this.gotCalories =
      this.gotHealthScore =
        false;
    // Don't clear this.hint here!
  }

  /**
   * Log the current meal to the meal logger service
   */
  private logMeal(): void {
    if (!this.result.dish) {
      console.log('Cannot log meal: missing dish information');
      return;
    }

    try {
      const loggedMeal = this.mealLoggerService.logMeal(
        this.result as any,
        'nutrition', // analysis mode
        'nutrition', // service
        undefined, // image_url
        undefined // overlay_url
      );

      console.log('Meal logged successfully:', loggedMeal);
    } catch (error) {
      console.error('Error logging meal:', error);
    }
  }

  /**
   * Get health score for the analyzed meal
   */
  private getHealthScore(): void {
    if (
      this.result.total_kcal &&
      this.result.total_grams &&
      this.result.total_fat_g &&
      this.result.total_protein_g &&
      this.result.items_grams
    ) {
      const healthScoreInput: HealthScoreInput = {
        total_kcal: this.result.total_kcal,
        total_grams: this.result.total_grams,
        total_fat_g: this.result.total_fat_g,
        total_protein_g: this.result.total_protein_g || 0,
        items_grams: this.result.items_grams.map((item) => ({
          name: item.name,
          grams: item.grams,
        })),
        kcal_confidence: this.result.kcal_confidence || 1.0,
        use_confidence_dampen: false,
      };

      this.apiService.getHealthScore(healthScoreInput).subscribe({
        next: (healthScore) => {
          this.result.health_score = healthScore;
          this.gotHealthScore = true;
          console.log('Health score received:', healthScore);
          this.cdr.detectChanges();

          // Show notification
          this.showHealthScoreNotification = true;
          setTimeout(() => {
            this.showHealthScoreNotification = false;
          }, 3000);
        },
        error: (error) => {
          console.error('Health score failed:', error);
          // Don't show error to user, health score is optional
        },
      });
    }
  }

  /**
   * Get component scores for display
   */
  getComponentScores(): Array<{ name: string; score: number }> {
    if (!this.result.health_score?.component_scores) {
      return [];
    }

    const scores = this.result.health_score.component_scores;
    return [
      { name: 'Energy Density', score: scores.energy_density },
      { name: 'Protein Density', score: scores.protein_density },
      { name: 'Fat Balance', score: scores.fat_balance },
      { name: 'Carb Quality', score: scores.carb_quality },
      { name: 'Sodium Proxy', score: scores.sodium_proxy },
      { name: 'Whole Foods', score: scores.whole_foods },
    ];
  }
}
