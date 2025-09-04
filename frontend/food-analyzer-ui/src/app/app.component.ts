import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UploadAnalyzeComponent } from './components/upload-analyze/upload-analyze.component';
import { RagQueryComponent } from './components/rag-query/rag-query.component';
import { MealLogComponent } from './components/meal-log/meal-log.component';
import { NutritionAnalysisComponent } from './components/nutrition-analysis/nutrition-analysis.component';
import { ApiService, AppConfig } from './services/api.service';

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
export class AppComponent implements OnInit {
  activeTab: 'analyzer' | 'recipes' | 'log' | 'nutrition' = 'analyzer';
  appConfig: AppConfig | null = null;
  configLoading = true;
  configError: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadConfig();
  }

  setActiveTab(tab: 'analyzer' | 'recipes' | 'log' | 'nutrition') {
    this.activeTab = tab;
  }

  private loadConfig() {
    this.configLoading = true;
    this.configError = null;

    this.apiService.getConfig().subscribe({
      next: (config) => {
        this.appConfig = config;
        this.configLoading = false;
      },
      error: (error) => {
        console.error('Failed to load app config:', error);
        this.configError = 'Failed to load configuration';
        this.configLoading = false;
      },
    });
  }
}
