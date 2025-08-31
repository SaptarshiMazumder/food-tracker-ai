import { AnalysisResponse } from './api';

export type AnalysisMode = 'logmeal' | 'gemini' | 'ab_test' | 'fallback' | string;

export interface LoggedMealItemGrams {
  name: string;
  grams: number;
  note?: string;
}

export interface LoggedMealItemNutrition {
  name: string;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  method?: string;
}

export interface LoggedMeal {
  id: string;
  date: string; // YYYY-MM-DD
  timestamp: string; // ISO
  dish?: string;
  dish_confidence?: number;
  ingredients_detected: string[];
  items_grams: LoggedMealItemGrams[];
  total_grams?: number;
  grams_confidence?: number;
  items_nutrition?: LoggedMealItemNutrition[];
  total_kcal?: number;
  total_protein_g?: number;
  total_carbs_g?: number;
  total_fat_g?: number;
  kcal_confidence?: number;
  notes?: string;
  analysis_mode: AnalysisMode;
  service_used: string;
  image_url?: string;
  overlay_url?: string;
}

export interface DailyMealTotals {
  total_kcal: number;
  total_protein_g: number;
  total_carbs_g: number;
  total_fat_g: number;
  total_grams: number;
}

export interface DailyMealLog {
  date: string;
  meals: LoggedMeal[];
  dailyTotals: DailyMealTotals;
}

type Subscriber = () => void;

class MealLogger {
  private static STORAGE_KEY = 'food_analyzer_meals_mobile';
  private subscribers: Set<Subscriber> = new Set();
  private meals: LoggedMeal[] = [];

  constructor() {
    this.load();
  }

  subscribe(fn: Subscriber): () => void {
    this.subscribers.add(fn);
    return () => this.subscribers.delete(fn);
  }

  private notify() {
    for (const fn of Array.from(this.subscribers)) {
      try {
        fn();
      } catch {}
    }
  }

  private persist() {
    try {
      // Minimal persistence without external deps
      (globalThis as any).__MEAL_LOGGER_DATA__ = JSON.stringify(this.meals);
    } catch {}
  }

  private load() {
    try {
      const raw = (globalThis as any).__MEAL_LOGGER_DATA__;
      if (typeof raw === 'string') {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) this.meals = parsed as LoggedMeal[];
      }
    } catch {
      this.meals = [];
    }
  }

  private generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
  }

  getAll(): LoggedMeal[] {
    return this.meals.slice().sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
  }

  getMealsForDate(date: string): LoggedMeal[] {
    return this.meals.filter((m) => m.date === date).sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
  }

  private formatYMD(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  getTodaysMeals(): LoggedMeal[] {
    const today = this.formatYMD(new Date());
    return this.getMealsForDate(today);
  }

  getDailyMealLog(date: string): DailyMealLog {
    const meals = this.getMealsForDate(date);
    return {
      date,
      meals,
      dailyTotals: this.calculateTotals(meals),
    };
  }

  getTodaysMealLog(): DailyMealLog {
    const today = this.formatYMD(new Date());
    return this.getDailyMealLog(today);
  }

  getAllMealDates(): string[] {
    const set = new Set(this.meals.map((m) => m.date));
    return Array.from(set).sort().reverse();
  }

  searchMeals(query: string): LoggedMeal[] {
    const q = (query || '').toLowerCase();
    if (!q) return [];
    return this.meals.filter((m) => {
      const inDish = (m.dish || '').toLowerCase().includes(q);
      const inIngredients = (m.ingredients_detected || []).some((ing) => ing.toLowerCase().includes(q));
      return inDish || inIngredients;
    });
  }

  logFromAnalysis(
    api: AnalysisResponse,
    analysisMode: AnalysisMode,
    serviceUsed: string,
    imageUrl?: string,
    overlayUrl?: string
  ): LoggedMeal {
    const meal: LoggedMeal = {
      id: this.generateId(),
      date: this.formatYMD(new Date()),
      timestamp: new Date().toISOString(),
      dish: api?.dish,
      dish_confidence: api?.dish_confidence,
      ingredients_detected: api?.ingredients_detected || [],
      items_grams: api?.items_grams || [],
      total_grams: api?.total_grams || 0,
      grams_confidence: api?.grams_confidence || 0,
      items_nutrition: api?.items_nutrition || [],
      total_kcal: api?.total_kcal || 0,
      total_protein_g: api?.total_protein_g || 0,
      total_carbs_g: api?.total_carbs_g || 0,
      total_fat_g: api?.total_fat_g || 0,
      kcal_confidence: api?.kcal_confidence || 0,
      notes: api?.notes,
      analysis_mode: analysisMode,
      service_used: serviceUsed,
      image_url: imageUrl,
      overlay_url: overlayUrl,
    };
    this.meals = [...this.meals, meal];
    this.persist();
    this.notify();
    return meal;
  }

  duplicateToToday(existing: LoggedMeal): LoggedMeal {
    const today = this.formatYMD(new Date());
    const dup: LoggedMeal = {
      ...existing,
      id: this.generateId(),
      date: today,
      timestamp: new Date().toISOString(),
    };
    this.meals = [...this.meals, dup];
    this.persist();
    this.notify();
    return dup;
  }

  removeMeal(mealId: string): void {
    this.meals = this.meals.filter((m) => m.id !== mealId);
    this.persist();
    this.notify();
  }

  duplicateToDate(existing: LoggedMeal, targetDate: string): LoggedMeal {
    // Preserve time-of-day from existing timestamp, change just the date
    const timeSource = new Date(existing.timestamp);
    const [y, m, d] = targetDate.split('-').map((n) => parseInt(n, 10));
    const ts = new Date(timeSource);
    if (!isNaN(y) && !isNaN(m) && !isNaN(d)) {
      ts.setFullYear(y, m - 1, d);
    }
    const dup: LoggedMeal = {
      ...existing,
      id: this.generateId(),
      date: targetDate,
      timestamp: ts.toISOString(),
    };
    this.meals = [...this.meals, dup];
    this.persist();
    this.notify();
    return dup;
  }

  moveMealToDate(mealId: string, targetDate: string): void {
    const idx = this.meals.findIndex((m) => m.id === mealId);
    if (idx === -1) return;
    const meal = this.meals[idx];
    const timeSource = new Date(meal.timestamp);
    const [y, m, d] = targetDate.split('-').map((n) => parseInt(n, 10));
    const ts = new Date(timeSource);
    if (!isNaN(y) && !isNaN(m) && !isNaN(d)) {
      ts.setFullYear(y, m - 1, d);
    }
    const updated: LoggedMeal = { ...meal, date: targetDate, timestamp: ts.toISOString() };
    // Replace in-place to preserve ordering semantics; then resort isn't necessary for per-day views
    this.meals = [
      ...this.meals.slice(0, idx),
      updated,
      ...this.meals.slice(idx + 1),
    ];
    this.persist();
    this.notify();
  }

  clearAll(): void {
    this.meals = [];
    this.persist();
    this.notify();
  }

  getMealsInDateRange(startDate: string, endDate: string): LoggedMeal[] {
    return this.meals.filter((m) => m.date >= startDate && m.date <= endDate);
  }

  private calculateTotals(meals: LoggedMeal[]): DailyMealTotals {
    return meals.reduce(
      (acc, m) => ({
        total_kcal: acc.total_kcal + (m.total_kcal || 0),
        total_protein_g: acc.total_protein_g + (m.total_protein_g || 0),
        total_carbs_g: acc.total_carbs_g + (m.total_carbs_g || 0),
        total_fat_g: acc.total_fat_g + (m.total_fat_g || 0),
        total_grams: acc.total_grams + (m.total_grams || 0),
      }),
      { total_kcal: 0, total_protein_g: 0, total_carbs_g: 0, total_fat_g: 0, total_grams: 0 }
    );
  }
}

export const mealLogger = new MealLogger();


