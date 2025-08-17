// Typed API models and UI helpers

export interface AnalyzeItemGrams {
  name: string;
  grams: number;
  note?: string;
}

export interface AnalyzeNutritionItem {
  name: string;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  method?: string;
}

export interface AnalyzeDensity {
  name: string;
  kcal_per_g: number;
  protein_per_g: number;
  carbs_per_g: number;
  fat_per_g: number;
}

export interface Timings {
  recognize_ms?: number;
  ing_quant_ms?: number;
  calories_ms?: number;
  [k: string]: number | undefined;
}

export interface ApiResponse {
  dish: string;
  dish_confidence: number;
  ingredients_detected: string[];

  items_grams: AnalyzeItemGrams[];
  total_grams: number;
  grams_confidence: number;

  items_nutrition: AnalyzeNutritionItem[];
  items_kcal: { name: string; kcal: number; method?: string }[];

  items_density?: AnalyzeDensity[];

  total_kcal: number;
  total_protein_g?: number;
  total_carbs_g?: number;
  total_fat_g?: number;
  kcal_confidence: number;

  notes?: string;
  angles_used?: number;

  // NEW
  timings?: Timings;
  total_ms?: number;
}

/** Row model for the ingredients table */
export interface UiItem {
  name: string;
  baseGrams: number;
  min: number;
  max: number;
  step: number;
  kcalPerG: number;
  proteinPerG: number;
  carbsPerG: number;
  fatPerG: number;
  computedKcal: number;
  computedProtein: number;
  computedCarbs: number;
  computedFat: number;
  note?: string;
}

/** Aggregated totals computed client-side */
export interface UiTotals {
  grams: number;
  kcal: number;
  protein: number;
  carbs: number;
  fat: number;
}
