import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Timings } from '../../models/analyzer.models';

@Component({
  selector: 'app-timings-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: 'timings-panel.component.html',
  styleUrls: ['timings-panel.component.css'],
})
export class TimingsPanelComponent {
  @Input() timings: Timings | null = null;
  @Input() totalMs: number | null = null;

  keysInOrder(t: Timings | null): string[] {
    if (!t) return [];
    const order = ['recognize_ms', 'ing_quant_ms', 'calories_ms'];
    const rest = Object.keys(t).filter((k) => !order.includes(k));
    return [...order.filter((k) => k in t), ...rest];
  }
}
