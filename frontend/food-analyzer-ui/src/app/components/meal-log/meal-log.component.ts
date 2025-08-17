import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { LoggedMeal, DailyMealLog } from '../../models/analyzer.models';
import { MealLoggerService } from '../../services/meal-logger.service';

@Component({
  selector: 'app-meal-log',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './meal-log.component.html',
  styleUrls: ['./meal-log.component.css'],
})
export class MealLogComponent implements OnInit, OnDestroy {
  todaysMealLog: DailyMealLog | null = null;
  searchQuery = '';
  searchResults: LoggedMeal[] = [];
  isSearching = false;
  selectedDate = new Date().toISOString().split('T')[0];
  allDates: string[] = [];
  expandedMeals: Set<string> = new Set();
  currentWeekStart: Date = new Date();

  private subscription: Subscription = new Subscription();

  constructor(private mealLoggerService: MealLoggerService) {}

  ngOnInit(): void {
    // Initialize current week start to the beginning of the current week (Sunday)
    const today = new Date();
    const dayOfWeek = today.getDay();
    this.currentWeekStart = new Date(today);
    this.currentWeekStart.setDate(today.getDate() - dayOfWeek);

    this.loadTodaysMeals();
    this.loadAllDates();

    // Subscribe to meal updates
    this.subscription.add(
      this.mealLoggerService.meals$.subscribe(() => {
        this.loadTodaysMeals();
        this.loadAllDates();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  loadTodaysMeals(): void {
    this.todaysMealLog = this.mealLoggerService.getTodaysMealLog();
  }

  loadAllDates(): void {
    this.allDates = this.mealLoggerService.getAllMealDates();
  }

  onDateChange(date: string): void {
    this.selectDate(date);
  }

  onSearch(): void {
    if (!this.searchQuery.trim()) {
      this.searchResults = [];
      this.isSearching = false;
      return;
    }

    this.isSearching = true;
    this.searchResults = this.mealLoggerService.searchMeals(this.searchQuery);
  }

  onClearSearch(): void {
    this.searchQuery = '';
    this.searchResults = [];
    this.isSearching = false;
  }

  onRemoveMeal(mealId: string): void {
    this.mealLoggerService.removeMeal(mealId);
  }

  toggleMealExpansion(mealId: string): void {
    if (this.expandedMeals.has(mealId)) {
      this.expandedMeals.delete(mealId);
    } else {
      this.expandedMeals.add(mealId);
    }
  }

  isMealExpanded(mealId: string): boolean {
    return this.expandedMeals.has(mealId);
  }

  getWeekDays(): {
    date: Date;
    dateString: string;
    dayName: string;
    isToday: boolean;
    isSelected: boolean;
  }[] {
    const days = [];
    const today = new Date();
    const todayString = today.toISOString().split('T')[0];

    for (let i = 0; i < 7; i++) {
      const date = new Date(this.currentWeekStart);
      date.setDate(this.currentWeekStart.getDate() + i);
      const dateString = date.toISOString().split('T')[0];
      const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
      const isToday = dateString === todayString;
      const isSelected = dateString === this.selectedDate;

      days.push({ date, dateString, dayName, isToday, isSelected });
    }

    return days;
  }

  getDayTotals(dateString: string): { kcal: number; protein: number } {
    const meals = this.mealLoggerService.getMealsForDate(dateString);
    const totals = meals.reduce(
      (acc, meal) => ({
        kcal: acc.kcal + (meal.total_kcal || 0),
        protein: acc.protein + (meal.total_protein_g || 0),
      }),
      { kcal: 0, protein: 0 }
    );

    return totals;
  }

  previousWeek(): void {
    this.currentWeekStart.setDate(this.currentWeekStart.getDate() - 7);
  }

  nextWeek(): void {
    this.currentWeekStart.setDate(this.currentWeekStart.getDate() + 7);
  }

  selectDate(dateString: string): void {
    this.selectedDate = dateString;
    this.todaysMealLog = this.mealLoggerService.getDailyMealLog(dateString);
  }

  onAddMealToToday(meal: LoggedMeal): void {
    // Create a new meal entry for today based on the selected meal
    const today = new Date().toISOString().split('T')[0];
    const newMeal: LoggedMeal = {
      ...meal,
      id: this.generateId(),
      date: today,
      timestamp: new Date().toISOString(),
    };

    // Add the meal using the service's public method
    this.mealLoggerService.logMeal(
      newMeal,
      newMeal.analysis_mode,
      newMeal.service_used,
      newMeal.image_url,
      newMeal.overlay_url
    );
  }

  private generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  formatTime(timestamp: string): string {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  formatDate(date: string): string {
    return new Date(date).toLocaleDateString([], {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  }

  getServiceIcon(service: string): string {
    return service === 'logmeal' ? '🍽️' : '🤖';
  }

  getAnalysisModeIcon(mode: string): string {
    switch (mode) {
      case 'logmeal':
        return '🍽️';
      case 'gemini':
        return '🤖';
      case 'ab_test':
        return '⚖️';
      case 'fallback':
        return '🔄';
      default:
        return '📊';
    }
  }
}
