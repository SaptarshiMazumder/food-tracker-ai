import { Component, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { RAGQueryResponse, RAGQueryHit } from '../../models/rag.models';
import { RagQueryInputComponent } from './rag-query-input/rag-query-input.component';
import { RagQueryResultsComponent } from './rag-query-results/rag-query-results.component';

@Component({
  selector: 'app-rag-query',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RagQueryInputComponent,
    RagQueryResultsComponent,
  ],
  templateUrl: './rag-query.component.html',
  styleUrls: ['./rag-query.component.css'],
})
export class RagQueryComponent {
  @ViewChild('resultsComponent') resultsComponent: any;

  queryResults: RAGQueryResponse | null = null;
  isLoading = false;
  error: string | null = null;
  currentMode: 'flexible' | 'strict' = 'flexible';

  constructor(private apiService: ApiService, private cdr: ChangeDetectorRef) {}

  onQuerySubmit(data: { ingredients: string[]; mode: string }) {
    this.isLoading = true;
    this.error = null;
    this.queryResults = null;
    this.currentMode = data.mode as 'flexible' | 'strict';

    this.apiService
      .queryRAG({
        ingredients: data.ingredients,
        top: 5,
        mode: data.mode as 'flexible' | 'strict',
      })
      .subscribe({
        next: (response) => {
          this.queryResults = response;
          this.isLoading = false;
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.error = err.error || 'Failed to query RAG system';
          this.isLoading = false;
          this.cdr.detectChanges();
        },
      });
  }

  onLoadDetails(data: { dishName: string; ingredients: string[] }) {
    this.apiService
      .getRecipeDetails(data.dishName, data.ingredients)
      .subscribe({
        next: (details) => {
          // Update the sources in the query results
          if (this.queryResults) {
            this.queryResults.sources[data.dishName] = details.sources;
            this.cdr.detectChanges();
          }
          
          // Clear loading state for this specific recipe
          if (this.resultsComponent) {
            const index = this.queryResults?.hits.findIndex(hit => hit.dish_name === data.dishName);
            if (index !== undefined && index >= 0) {
              this.resultsComponent.clearLoadingState(index);
            }
          }
        },
        error: (err) => {
          console.error('Failed to load recipe details:', err);
          // Clear loading state on error too
          if (this.resultsComponent) {
            const index = this.queryResults?.hits.findIndex(hit => hit.dish_name === data.dishName);
            if (index !== undefined && index >= 0) {
              this.resultsComponent.clearLoadingState(index);
            }
          }
        },
      });
  }
}
