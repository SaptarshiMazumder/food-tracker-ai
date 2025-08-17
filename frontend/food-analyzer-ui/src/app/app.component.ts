import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UploadAnalyzeComponent } from './components/upload-analyze/upload-analyze.component';
import { RagQueryComponent } from './components/rag-query/rag-query.component';
import { MealLogComponent } from './components/meal-log/meal-log.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    UploadAnalyzeComponent,
    RagQueryComponent,
    MealLogComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {
  activeTab: 'analyzer' | 'recipes' | 'log' = 'analyzer';

  setActiveTab(tab: 'analyzer' | 'recipes' | 'log') {
    this.activeTab = tab;
  }
}
