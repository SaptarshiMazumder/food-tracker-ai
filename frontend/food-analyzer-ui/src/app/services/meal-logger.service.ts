import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { LoggedMeal, DailyMealLog } from '../models/analyzer.models';

@Injectable({
  providedIn: 'root',
})
export class MealLoggerService {
  private readonly STORAGE_KEY = 'food_analyzer_meals';
  private mealsSubject = new BehaviorSubject<LoggedMeal[]>([]);
  public meals$ = this.mealsSubject.asObservable();

  constructor() {
    this.loadMealsFromStorage();
  }

  /**
   * Log a new meal
   */
  logMeal(
    apiResponse: any,
    analysisMode: string,
    serviceUsed: string,
    imageUrl?: string,
    overlayUrl?: string
  ): LoggedMeal {
    const meal: LoggedMeal = {
      id: this.generateId(),
      date: new Date().toISOString().split('T')[0], // YYYY-MM-DD
      timestamp: new Date().toISOString(),
      dish: apiResponse.dish,
      dish_confidence: apiResponse.dish_confidence,
      ingredients_detected: apiResponse.ingredients_detected || [],
      items_grams: apiResponse.items_grams || [],
      total_grams: apiResponse.total_grams || 0,
      grams_confidence: apiResponse.grams_confidence || 0,
      items_nutrition: apiResponse.items_nutrition || [],
      total_kcal: apiResponse.total_kcal || 0,
      total_protein_g: apiResponse.total_protein_g,
      total_carbs_g: apiResponse.total_carbs_g,
      total_fat_g: apiResponse.total_fat_g,
      kcal_confidence: apiResponse.kcal_confidence || 0,
      notes: apiResponse.notes,
      analysis_mode: analysisMode as any,
      service_used: serviceUsed as any,
      image_url: imageUrl,
      overlay_url: overlayUrl,
    };

    const currentMeals = this.mealsSubject.value;
    const updatedMeals = [...currentMeals, meal];
    this.mealsSubject.next(updatedMeals);
    this.saveMealsToStorage(updatedMeals);

    return meal;
  }

  /**
   * Remove a meal by ID
   */
  removeMeal(mealId: string): void {
    const currentMeals = this.mealsSubject.value;
    const updatedMeals = currentMeals.filter((meal) => meal.id !== mealId);
    this.mealsSubject.next(updatedMeals);
    this.saveMealsToStorage(updatedMeals);
  }

  /**
   * Get meals for a specific date
   */
  getMealsForDate(date: string): LoggedMeal[] {
    return this.mealsSubject.value.filter((meal) => meal.date === date);
  }

  /**
   * Get meals for today
   */
  getTodaysMeals(): LoggedMeal[] {
    const today = new Date().toISOString().split('T')[0];
    return this.getMealsForDate(today);
  }

  /**
   * Get daily meal log for a specific date
   */
  getDailyMealLog(date: string): DailyMealLog {
    const meals = this.getMealsForDate(date);
    const dailyTotals = this.calculateDailyTotals(meals);

    return {
      date,
      meals,
      dailyTotals,
    };
  }

  /**
   * Get daily meal log for today
   */
  getTodaysMealLog(): DailyMealLog {
    const today = new Date().toISOString().split('T')[0];
    return this.getDailyMealLog(today);
  }

  /**
   * Search meals by dish name or ingredients
   */
  searchMeals(query: string): LoggedMeal[] {
    const meals = this.mealsSubject.value;
    const lowerQuery = query.toLowerCase();

    return meals.filter(
      (meal) =>
        meal.dish.toLowerCase().includes(lowerQuery) ||
        meal.ingredients_detected.some((ingredient) =>
          ingredient.toLowerCase().includes(lowerQuery)
        )
    );
  }

  /**
   * Get all unique dates that have meals
   */
  getAllMealDates(): string[] {
    const meals = this.mealsSubject.value;
    const dates = meals.map((meal) => meal.date);
    return [...new Set(dates)].sort().reverse(); // Most recent first
  }

  /**
   * Get meals from a specific date range
   */
  getMealsInDateRange(startDate: string, endDate: string): LoggedMeal[] {
    return this.mealsSubject.value.filter(
      (meal) => meal.date >= startDate && meal.date <= endDate
    );
  }

  /**
   * Clear all meals
   */
  clearAllMeals(): void {
    this.mealsSubject.next([]);
    this.saveMealsToStorage([]);
  }

  /**
   * Calculate daily totals from meals
   */
  private calculateDailyTotals(meals: LoggedMeal[]) {
    return meals.reduce(
      (totals, meal) => ({
        total_kcal: totals.total_kcal + (meal.total_kcal || 0),
        total_protein_g: totals.total_protein_g + (meal.total_protein_g || 0),
        total_carbs_g: totals.total_carbs_g + (meal.total_carbs_g || 0),
        total_fat_g: totals.total_fat_g + (meal.total_fat_g || 0),
        total_grams: totals.total_grams + (meal.total_grams || 0),
      }),
      {
        total_kcal: 0,
        total_protein_g: 0,
        total_carbs_g: 0,
        total_fat_g: 0,
        total_grams: 0,
      }
    );
  }

  /**
   * Generate unique ID for meals
   */
  private generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  /**
   * Load meals from browser storage
   */
  private loadMealsFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const meals = JSON.parse(stored);
        this.mealsSubject.next(meals);
      }
    } catch (error) {
      console.error('Error loading meals from storage:', error);
      this.mealsSubject.next([]);
    }
  }

  /**
   * Save meals to browser storage
   */
  private saveMealsToStorage(meals: LoggedMeal[]): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(meals));
    } catch (error) {
      console.error('Error saving meals to storage:', error);
    }
  }
}
