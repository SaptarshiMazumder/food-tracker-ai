import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-rag-query-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './rag-query-input.component.html',
  styleUrls: ['./rag-query-input.component.css'],
})
export class RagQueryInputComponent {
  @Output() querySubmit = new EventEmitter<{
    ingredients: string[];
    mode: string;
  }>();

  ingredientInput = '';
  ingredients: string[] = [];
  searchMode: 'flexible' | 'strict' = 'flexible';

  addIngredient() {
    const ingredient = this.ingredientInput.trim().toLowerCase();
    if (ingredient && !this.ingredients.includes(ingredient)) {
      this.ingredients.push(ingredient);
      this.ingredientInput = '';
    }
  }

  removeIngredient(index: number) {
    this.ingredients.splice(index, 1);
  }

  submitQuery() {
    if (this.ingredients.length > 0) {
      this.querySubmit.emit({
        ingredients: [...this.ingredients],
        mode: this.searchMode,
      });
    }
  }

  onKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      this.addIngredient();
    }
  }
}
