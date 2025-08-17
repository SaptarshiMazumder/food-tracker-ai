import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-upload-input',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: 'upload-input.component.html',
  styleUrls: ['upload-input.component.css'],
})
export class UploadInputComponent {
  @Output() analyze = new EventEmitter<{ files: File[]; model: string }>();
  @Output() clear = new EventEmitter<void>();

  form = new FormGroup({
    model: new FormControl<string>('gemini-2.5-pro'),
    files: new FormControl<File[] | null>(null),
  });

  fileNames: string[] = [];
  filePreviews: string[] = [];

  onFileChange(ev: Event) {
    const input = ev.target as HTMLInputElement;
    if (!input.files?.length) {
      this.fileNames = [];
      this.filePreviews = [];
      this.form.patchValue({ files: null });
      return;
    }
    const files = Array.from(input.files);
    this.fileNames = files.map((f) => f.name);
    this.filePreviews = [];
    files.forEach((f, idx) => {
      const fr = new FileReader();
      fr.onload = () => (this.filePreviews[idx] = String(fr.result || ''));
      fr.readAsDataURL(f);
    });
    this.form.patchValue({ files });
  }

  submit() {
    const files = this.form.value.files as File[] | null;
    const model = this.form.value.model || 'gemini-2.5-pro';
    if (!files?.length) return;
    this.analyze.emit({ files, model });
  }

  reset() {
    this.form.reset({ model: 'gemini-2.5-pro', files: null });
    this.fileNames = [];
    this.filePreviews = [];
    this.clear.emit();
  }
}
