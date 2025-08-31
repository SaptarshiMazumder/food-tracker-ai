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

// NEW: Health Score Models
export interface HealthScoreInput {
  total_kcal: number;
  total_grams: number;
  total_fat_g: number;
  total_protein_g: number;
  items_grams: { name: string; grams: number }[];
  kcal_confidence: number;
  use_confidence_dampen: boolean;
}

export interface ComponentScores {
  energy_density: number;
  protein_density: number;
  fat_balance: number;
  carb_quality: number;
  sodium_proxy: number;
  whole_foods: number;
}

export interface HealthScoreOutput {
  health_score: number;
  component_scores: ComponentScores;
  weights: { [key: string]: number };
  drivers_positive: string[];
  drivers_negative: string[];
  debug: { [key: string]: number };
  classification: { name: string; category: string }[];
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

  // NEW: Health Score
  health_score?: HealthScoreOutput;
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

// NEW: Meal logging interfaces
export interface LoggedMeal {
  id: string;
  date: string; // ISO date string (YYYY-MM-DD)
  timestamp: string; // ISO datetime string
  dish: string;
  dish_confidence: number;
  ingredients_detected: string[];
  items_grams: AnalyzeItemGrams[];
  total_grams: number;
  grams_confidence: number;
  items_nutrition: AnalyzeNutritionItem[];
  total_kcal: number;
  total_protein_g?: number;
  total_carbs_g?: number;
  total_fat_g?: number;
  kcal_confidence: number;
  notes?: string;
  analysis_mode: 'logmeal' | 'gemini' | 'ab_test' | 'fallback';
  service_used: 'logmeal' | 'gemini';
  image_url?: string;
  overlay_url?: string;
}

export interface DailyMealLog {
  date: string; // ISO date string (YYYY-MM-DD)
  meals: LoggedMeal[];
  dailyTotals: {
    total_kcal: number;
    total_protein_g: number;
    total_carbs_g: number;
    total_fat_g: number;
    total_grams: number;
  };
}
