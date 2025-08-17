import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormArray,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
} from '@angular/forms';
import { UiItem, UiTotals } from '../../models/analyzer.models';
import { FoodAnalyzerService } from '../../services/food-analyzer.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-ingredient-table',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: 'ingredient-table.component.html',
  styleUrls: ['ingredient-table.component.css'],
})
export class IngredientTableComponent implements OnChanges {
  @Input() items: UiItem[] = [];
  @Output() totals = new EventEmitter<UiTotals>();

  form = new FormGroup({
    rows: new FormArray<FormControl<number>>([]),
  });

  private subs: Subscription[] = [];

  constructor(private svc: FoodAnalyzerService) {}

  get rowsFA(): FormArray<FormControl<number>> {
    return this.form.get('rows') as FormArray<FormControl<number>>;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['items']) {
      this.rebuildForm();
    }
  }

  private rebuildForm() {
    this.subs.forEach((s) => s.unsubscribe());
    this.subs = [];
    this.rowsFA.clear();
    this.items.forEach((u) =>
      this.rowsFA.push(
        new FormControl<number>(u.baseGrams, { nonNullable: true })
      )
    );
    this.emitTotals();
    this.subs.push(this.rowsFA.valueChanges.subscribe(() => this.emitTotals()));
  }

  onNumInput(i: number, ev: Event) {
    const val = Number((ev.target as HTMLInputElement).value || 0);
    this.rowsFA.at(i).setValue(val, { emitEvent: true });
  }

  resetRow(i: number) {
    const base = this.items[i]?.baseGrams ?? 0;
    this.rowsFA.at(i).setValue(base, { emitEvent: true });
  }

  private emitTotals() {
    const grams = this.rowsFA.value as number[];
    const totals = this.svc.computeTotals(this.items, grams);
    // update computed columns for display
    this.items.forEach((row, idx) => {
      const g = grams[idx] ?? row.baseGrams;
      row.computedKcal = Math.round(g * row.kcalPerG);
      row.computedProtein = +(g * row.proteinPerG).toFixed(1);
      row.computedCarbs = +(g * row.carbsPerG).toFixed(1);
      row.computedFat = +(g * row.fatPerG).toFixed(1);
    });
    this.totals.emit(totals);
  }
}
