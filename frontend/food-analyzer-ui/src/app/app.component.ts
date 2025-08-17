import { Component } from '@angular/core';
import { UploadAnalyzeComponent } from './components/upload-analyze/upload-analyze.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [UploadAnalyzeComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {}
