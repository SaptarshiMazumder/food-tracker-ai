import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiResponse, UiItem, UiTotals } from '../../models/analyzer.models';
import { FoodAnalyzerService } from '../../services/food-analyzer.service';
import { UploadInputComponent } from '../upload-input/upload-input.component';
import { IngredientTableComponent } from '../ingredient-table/ingredient-table.component';
import { TimingsPanelComponent } from '../timings-panel/timings-panel.component';

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

  // progressive state
  result: Partial<ApiResponse> = {};
  uiItems: UiItem[] = [];
  totals: UiTotals | null = null;

  // phase flags
  gotRecognize = false;
  gotIngr = false;
  gotCalories = false;

  constructor(private svc: FoodAnalyzerService) {}

  onAnalyze(req: { files: File[]; model: string }) {
    this.resetPage(); // clears previous run
    this.started = true; // mark that a run has started
    this.loading = true;

    this.svc.analyzeStream(req.files, req.model).subscribe({
      next: (evt) => {
        if (evt.phase === 'recognize') {
          this.gotRecognize = true;
          const d = evt.data || {};
          this.result.dish = d.dish;
          this.result.dish_confidence = d.dish_confidence;
          this.result.ingredients_detected = d.ingredients_detected || [];
          this.result.timings = {
            ...(this.result.timings || {}),
            ...(d.timings || {}),
          };
        } else if (evt.phase === 'ing_quant') {
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
        } else if (evt.phase === 'calories') {
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
        } else if (evt.phase === 'done') {
          const d = evt.data as ApiResponse;
          this.result = { ...this.result, ...d };
          if (!this.uiItems.length && d.items_grams && d.items_nutrition) {
            this.uiItems = this.svc.buildUiItems(d);
            this.totals = this.svc.computeTotals(
              this.uiItems,
              this.uiItems.map((u) => u.baseGrams)
            );
          }
          this.loading = false;
        } else if (evt.phase === 'error') {
          this.errorMsg =
            (evt.data && (evt.data.msg || evt.data.error)) || 'Streaming error';
          this.loading = false;
        }
      },
      error: (err) => {
        this.errorMsg =
          (err?.error && (err.error.msg || err.error.error)) ||
          err.message ||
          'Analyze failed';
        this.loading = false;
      },
    });
  }

  onClear() {
    this.resetPage();
  }

  onTotals(t: UiTotals) {
    this.totals = t;
  }

  private resetPage() {
    this.loading = false;
    this.started = false; // NEW: hide result panel on first load/after clear
    this.errorMsg = '';
    this.result = {};
    this.uiItems = [];
    this.totals = null;
    this.gotRecognize = this.gotIngr = this.gotCalories = false;
  }
}
