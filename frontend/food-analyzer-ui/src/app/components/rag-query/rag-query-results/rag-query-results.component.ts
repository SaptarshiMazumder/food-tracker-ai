import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  RAGQueryResponse,
  RAGQueryHit,
  WebSource,
} from '../../../models/rag.models';

@Component({
  selector: 'app-rag-query-results',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './rag-query-results.component.html',
  styleUrls: ['./rag-query-results.component.css'],
})
export class RagQueryResultsComponent {
  @Input() results!: RAGQueryResponse;
  @Input() mode: 'flexible' | 'strict' = 'flexible';
  @Output() loadDetails = new EventEmitter<{
    dishName: string;
    ingredients: string[];
  }>();

  // Track collapsed state for each recipe card
  collapsedCards: { [key: number]: boolean } = {};
  // Track loading state for details in strict mode
  loadingDetails: { [key: number]: boolean } = {};
  // Track loaded details in strict mode
  loadedDetails: { [key: number]: any } = {};

  getScorePercentage(score: number): number {
    return Math.round(score * 100);
  }

  getScoreColor(score: number): string {
    if (score >= 0.8) return 'high';
    if (score >= 0.6) return 'medium';
    return 'low';
  }

  getSourcesForDish(dishName: string): WebSource[] {
    return this.results.sources[dishName] || [];
  }

  hasRecipeInfo(recipeInfo: any): boolean {
    return (
      recipeInfo &&
      typeof recipeInfo === 'object' &&
      Object.keys(recipeInfo).length > 0
    );
  }

  toggleCard(index: number): void {
    this.collapsedCards[index] = !this.collapsedCards[index];
  }

  isCardCollapsed(index: number): boolean {
    return this.collapsedCards[index] !== false; // Default to collapsed
  }

  onLoadDetails(index: number, dishName: string, ingredients: string[]): void {
    if (this.mode === 'strict' && !this.loadedDetails[index]) {
      this.loadingDetails[index] = true;
      this.loadDetails.emit({ dishName, ingredients });
    }
  }

  isDetailsLoaded(index: number): boolean {
    return !!this.loadedDetails[index];
  }

  isDetailsLoading(index: number): boolean {
    return this.loadingDetails[index] === true;
  }

  updateDetails(index: number, details: any): void {
    this.loadedDetails[index] = details;
    this.loadingDetails[index] = false;
  }

  onCardClick(index: number, dishName: string, ingredients: string[]): void {
    if (this.mode === 'strict') {
      // In strict mode, load details and then expand
      if (!this.loadedDetails[index]) {
        this.loadingDetails[index] = true;
        this.loadDetails.emit({ dishName, ingredients });
      }
    }
    // Always toggle the card
    this.toggleCard(index);
  }

  // Method to clear loading state when details are loaded
  clearLoadingState(index: number): void {
    this.loadingDetails[index] = false;
  }

  onImageError(event: any): void {
    // Set fallback image when the original image fails to load
    event.target.src =
      'https://d33wubrfki0l68.cloudfront.net/2b3f027405ee07fb69921b5de0710bb844882662/e937b/img/fallback.png';
  }
}
