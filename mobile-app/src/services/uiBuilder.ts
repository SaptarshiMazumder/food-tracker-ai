import { AnalysisResponse } from './api';

export type UiItem = {
  name: string;
  baseGrams: number;
  min: number;
  max: number;
  step: number;
  kcalPerG: number;
  proteinPerG: number;
  carbsPerG: number;
  fatPerG: number;
  note?: string;
};

export type UiTotals = {
  grams: number;
  kcal: number;
  protein: number;
  carbs: number;
  fat: number;
};

export function buildUiItems(resp: AnalysisResponse): UiItem[] {
  const gramsList = resp.items_grams || [];
  const nutrList = resp.items_nutrition || [];
  const densityMap = new Map(
    (resp.items_density || []).map((d) => [d.name.toLowerCase(), d])
  );
  const safePerG = (num: number, den: number) => (den > 0 ? num / den : 0);

  return gramsList.map((g) => {
    const nameL = g.name.toLowerCase();
    const n = nutrList.find((x) => x.name.toLowerCase() === nameL);
    const kcalPerG = densityMap.get(nameL)?.kcal_per_g ?? safePerG(n?.kcal ?? 0, g.grams);
    const proteinPerG = densityMap.get(nameL)?.protein_per_g ?? safePerG(n?.protein_g ?? 0, g.grams);
    const carbsPerG = densityMap.get(nameL)?.carbs_per_g ?? safePerG(n?.carbs_g ?? 0, g.grams);
    const fatPerG = densityMap.get(nameL)?.fat_per_g ?? safePerG(n?.fat_g ?? 0, g.grams);

    const base = g.grams || 0;
    const min = Math.max(0, Math.floor(base * 0.2));
    const max = Math.max(20, Math.ceil(base * 2.2));
    const step = 1;

    return {
      name: g.name,
      baseGrams: base,
      min,
      max,
      step,
      kcalPerG,
      proteinPerG,
      carbsPerG,
      fatPerG,
      note: g.note,
    };
  });
}

export function computeTotals(ui: UiItem[], currentGrams: number[]): UiTotals {
  let grams = 0, kcal = 0, protein = 0, carbs = 0, fat = 0;
  ui.forEach((row, i) => {
    const g = currentGrams[i] ?? row.baseGrams;
    grams += g;
    kcal += g * row.kcalPerG;
    protein += g * row.proteinPerG;
    carbs += g * row.carbsPerG;
    fat += g * row.fatPerG;
  });
  return {
    grams: Math.round(grams),
    kcal: Math.round(kcal),
    protein: +protein.toFixed(1),
    carbs: +carbs.toFixed(1),
    fat: +fat.toFixed(1),
  };
}


