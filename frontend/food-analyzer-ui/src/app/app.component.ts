import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UploadAnalyzeComponent } from './components/upload-analyze/upload-analyze.component';
import { RagQueryComponent } from './components/rag-query/rag-query.component';
import { MealLogComponent } from './components/meal-log/meal-log.component';
import { NutritionAnalysisComponent } from './components/nutrition-analysis/nutrition-analysis.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    UploadAnalyzeComponent,
    RagQueryComponent,
    MealLogComponent,
    NutritionAnalysisComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {
  activeTab: 'analyzer' | 'recipes' | 'log' | 'nutrition' = 'analyzer';

  setActiveTab(tab: 'analyzer' | 'recipes' | 'log' | 'nutrition') {
    this.activeTab = tab;
  }
}
