import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Button, Image, Alert, ActivityIndicator, ScrollView, Animated, TextInput } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { uploadAnalyzeImage, AnalysisResponse, analyzeStream } from '../services/api';
import { buildUiItems, computeTotals, UiItem, UiTotals } from '../services/uiBuilder';
import Slider from '@react-native-community/slider';

export default function AnalyzeScreen() {
  const [selectedUris, setSelectedUris] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [uiItems, setUiItems] = useState<UiItem[]>([]);
  const [grams, setGrams] = useState<number[]>([]);
  const [totals, setTotals] = useState<UiTotals | null>(null);
  // Progressive flags similar to web UI
  const [started, setStarted] = useState(false);
  const [gotRecognize, setGotRecognize] = useState(false);
  const [gotIngr, setGotIngr] = useState(false);
  const [gotCalories, setGotCalories] = useState(false);

  // Skeleton components for loading states
  type SkeletonProps = { width?: number | string; height?: number; borderRadius?: number; style?: any };
  const Skeleton = ({ width = '100%', height = 12, borderRadius = 6, style }: SkeletonProps) => {
    const opacity = useRef(new Animated.Value(0.6)).current;
    useEffect(() => {
      const loop = Animated.loop(
        Animated.sequence([
          Animated.timing(opacity, { toValue: 1, duration: 800, useNativeDriver: true }),
          Animated.timing(opacity, { toValue: 0.6, duration: 800, useNativeDriver: true }),
        ])
      );
      loop.start();
      return () => loop.stop();
    }, [opacity]);
    return (
      <Animated.View
        style={[
          { opacity, backgroundColor: '#eee', width, height, borderRadius },
          style,
        ]}
      />
    );
  };

  const SkeletonLine = (props: SkeletonProps) => <Skeleton {...props} />;
  const SkeletonChip = ({ width = 60 }: { width?: number }) => (
    <Skeleton width={width} height={20} borderRadius={999} style={{ marginRight: 6, marginBottom: 6 }} />
  );
  const SkeletonTile = () => (
    <View style={styles.tile}>
      <SkeletonLine width={'50%'} height={14} />
      <View style={{ height: 6 }} />
      <SkeletonLine width={'30%'} height={18} />
    </View>
  );

  const pickWithDocumentPicker = async (): Promise<string[]> => {
    try {
      const doc = await DocumentPicker.getDocumentAsync({
        type: ['image/*'],
        multiple: true,
        copyToCacheDirectory: true,
      });
      if (doc.canceled) return [];
      const assets: any[] = (doc as any).assets || [];
      const uris = assets.length > 0 ? assets.map((a) => a.uri) : ((doc as any).uri ? [ (doc as any).uri ] : []);
      return uris;
    } catch (e: any) { // Added type annotation for e
      Alert.alert('Picker error', `Could not open any picker. Error: ${e.message}`); // Display error message
      return [];
    }
  };

  const onUpload = async () => {
    // Clear previous selections and results
    setSelectedUris([]);
    setResult(null);
    setUiItems([]);
    setGrams([]);
    setTotals(null);
    setLoading(false);
    setStarted(false);
    setGotRecognize(false);
    setGotIngr(false);
    setGotCalories(false);

    // Prefer Document Picker first (multi-select friendly)
    const docUris = await pickWithDocumentPicker();
    if (docUris.length > 0) {
      setSelectedUris(Array.from(new Set(docUris)));
      return;
    }

    // If user cancelled or provider doesn't support multi-select, do nothing.
  };

  const onAnalyze = async () => {
    if (selectedUris.length === 0) return;
    try {
      setLoading(true);
      setStarted(true);
      setResult(null);
      setUiItems([]);
      setGrams([]);
      setTotals(null);
      setGotRecognize(false);
      setGotIngr(false);
      setGotCalories(false);
      // Streaming flow exactly like web UI with Gemini only (no LogMeal)
      const stream = await analyzeStream(selectedUris, { model: 'gemini-2.5-pro', useLogmeal: false });
      const acc: any = {};
      for await (const ev of stream) {
        if (ev.phase === 'recognize') {
          Object.assign(acc, ev.data);
          setGotRecognize(true);
          setResult((prev) => ({ ...(prev || {}), ...acc }));
        } else if (ev.phase === 'ing_quant') {
          Object.assign(acc, ev.data);
          setGotIngr(true);
          setResult((prev) => ({ ...(prev || {}), ...acc }));
        } else if (ev.phase === 'calories') {
          Object.assign(acc, ev.data);
          setGotCalories(true);
          setResult((prev) => ({ ...(prev || {}), ...acc }));
          // Build UI items as soon as calories arrive (if grams available)
          const snapshot = { ...(result || {}), ...acc } as AnalysisResponse;
          if (Array.isArray(snapshot.items_grams) && Array.isArray(snapshot.items_nutrition)) {
            const ui = buildUiItems(snapshot);
            setUiItems(ui);
            const baseGrams = ui.map((u) => u.baseGrams);
            setGrams(baseGrams);
            setTotals(computeTotals(ui, baseGrams));
          }
        } else if (ev.phase === 'done') {
          Object.assign(acc, ev.data);
          setResult((prev) => {
            const res = { ...(prev || {}), ...acc } as AnalysisResponse;
            // Ensure UI items/totals are computed if not already
            if (uiItems.length === 0 && Array.isArray(res.items_grams) && Array.isArray(res.items_nutrition)) {
              const ui = buildUiItems(res);
              setUiItems(ui);
              const baseGrams = ui.map((u) => u.baseGrams);
              setGrams(baseGrams);
              setTotals(computeTotals(ui, baseGrams));
            }
            return res;
          });
          break;
        }
      }
    } catch (e: any) {
      Alert.alert('Analyze failed', e?.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // No auto-analysis; user must press Analyze

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Removed explicit screen title per request */}
      <Text style={styles.subtitle}>Upload a photo to extract ingredients and calories.</Text>
      <View style={styles.actions}>
        <Button title="Upload Images" onPress={onUpload} disabled={loading} />
        <Text style={{ marginTop: 6, color: '#777' }}>
          In the picker, long-press then tap multiple items to multi-select.
        </Text>
      </View>
      {selectedUris.length > 0 ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.gallery} contentContainerStyle={{ gap: 8 }}>
          {selectedUris.map((u, i) => (
            <Image key={i} source={{ uri: u }} style={styles.thumb} />
          ))}
        </ScrollView>
      ) : null}

      <View style={styles.buttonRow}>
        <View style={styles.half}>
          <Button title="Analyze" onPress={onAnalyze} disabled={selectedUris.length === 0 || loading} />
        </View>
        <View style={styles.half}>
          <Button title="Clear" onPress={() => {
            if (loading) return;
            setSelectedUris([]);
            setResult(null);
            setUiItems([]);
            setGrams([]);
            setTotals(null);
          }} disabled={selectedUris.length === 0 || loading} />
        </View>
      </View>

      {loading ? (
        <View style={{ marginTop: 16 }}>
          <ActivityIndicator size="large" />
          <Text style={{ marginTop: 8 }}>Working… you'll see results step-by-step.</Text>
        </View>
      ) : null}

      {started && (gotRecognize || gotIngr || gotCalories || (result && typeof result.total_ms === 'number')) ? (
        <View style={styles.result}>
          {/* 1. FOOD */}
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>1. FOOD</Text>
            {gotRecognize ? (
              <>
                {result?.dish ? <Text style={styles.dishName}>{result.dish}</Text> : null}
                {Array.isArray(result?.ingredients_detected) && result!.ingredients_detected!.length > 0 ? (
                  <View style={styles.tagsWrap}>
                    {result!.ingredients_detected!.map((tag: string, i: number) => (
                      <Text key={i} style={styles.tag}>{tag}</Text>
                    ))}
                  </View>
                ) : null}
              </>
            ) : (
              <>
                <SkeletonLine width={'60%'} height={16} />
                <View style={styles.tagsWrap}>
                  <SkeletonChip width={70} />
                  <SkeletonChip width={64} />
                  <SkeletonChip width={88} />
                </View>
              </>
            )}
          </View>

          {/* 2. MACROS */}
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>2. MACROS</Text>
            {gotCalories && Array.isArray(result?.items_nutrition) && result!.items_nutrition!.length > 0 ? (
              <>
                <View style={styles.grid4}>
                  <View style={styles.tile}><Text style={styles.tileTitle}>Calories</Text><Text style={styles.tileValue}>{result!.total_kcal}</Text></View>
                  <View style={styles.tile}><Text style={styles.tileTitle}>Protein</Text><Text style={styles.tileValue}>{result!.total_protein_g} g</Text></View>
                  <View style={styles.tile}><Text style={styles.tileTitle}>Carbs</Text><Text style={styles.tileValue}>{result!.total_carbs_g} g</Text></View>
                  <View style={styles.tile}><Text style={styles.tileTitle}>Fat</Text><Text style={styles.tileValue}>{result!.total_fat_g} g</Text></View>
                </View>
                {/* Removed description under macros per request */}
              </>
            ) : (
              <View style={[styles.grid4, { width: '100%' }]}>
                <SkeletonTile />
                <SkeletonTile />
                <SkeletonTile />
                <SkeletonTile />
              </View>
            )}
          </View>

          {/* 3. INGREDIENTS */}
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>3. INGREDIENTS {gotIngr && typeof result?.total_grams === 'number' ? `(${result!.total_grams} g total)` : ''}</Text>
            {gotIngr ? (
              Array.isArray(result?.items_grams) && result!.items_grams!.length > 0 ? (
                <>
                  {result!.items_grams!.map((it: { name: string; grams: number; note?: string }, i: number) => (
                    <View key={i} style={styles.rowBetween}>
                      <Text>{it.name}</Text>
                      <Text>{it.grams} g</Text>
                    </View>
                  ))}
                </>
              ) : null
            ) : (
              <>
                <SkeletonLine width={'40%'} height={14} />
                <View>
                  <View style={styles.rowBetween}>
                    <SkeletonLine width={'30%'} height={12} />
                    <SkeletonLine width={'15%'} height={12} />
                  </View>
                  <View style={styles.rowBetween}>
                    <SkeletonLine width={'28%'} height={12} />
                    <SkeletonLine width={'12%'} height={12} />
                  </View>
                  <View style={styles.rowBetween}>
                    <SkeletonLine width={'34%'} height={12} />
                    <SkeletonLine width={'10%'} height={12} />
                  </View>
                </View>
              </>
            )}
          </View>

          {/* Adjust portions */}
          {uiItems.length > 0 ? (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>ADJUST PORTIONS</Text>
              {uiItems.map((u, i) => (
                <View key={i} style={{ marginBottom: 12 }}>
                  <View style={styles.rowBetween}>
                    <Text style={styles.ingName}>{u.name}</Text>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                      <TextInput
                        style={styles.gramsInput}
                        keyboardType="numeric"
                        value={String(grams[i] ?? u.baseGrams)}
                        onChangeText={(txt) => {
                          const n = parseInt(txt || '0', 10);
                          const clamped = isNaN(n) ? 0 : Math.max(u.min, Math.min(u.max, n));
                          const next = [...grams];
                          next[i] = clamped;
                          setGrams(next);
                          setTotals(computeTotals(uiItems, next));
                        }}
                      />
                      <Text>g</Text>
                      <Button
                        title="Reset"
                        onPress={() => {
                          const next = [...grams];
                          next[i] = u.baseGrams;
                          setGrams(next);
                          setTotals(computeTotals(uiItems, next));
                        }}
                      />
                    </View>
                  </View>
                  {u.note ? (
                    <Text style={styles.noteText}>{u.note}</Text>
                  ) : null}
                  <Slider
                    minimumValue={u.min}
                    maximumValue={u.max}
                    step={u.step}
                    value={grams[i] ?? u.baseGrams}
                    onValueChange={(val) => {
                      const next = [...grams];
                      next[i] = Math.round(val as number);
                      setGrams(next);
                      setTotals(computeTotals(uiItems, next));
                    }}
                  />
                  <Text style={styles.macroStrip}>
                    Cals {(u.kcalPerG * (grams[i] ?? u.baseGrams)).toFixed(0)} • P {(u.proteinPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g • C {(u.carbsPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g • F {(u.fatPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g
                  </Text>
                </View>
              ))}
              {totals ? (
                <View style={styles.totalsContainer}>
                  <Text style={styles.totalsTitle}>Adjusted totals</Text>
                  <Text style={styles.totalsLine}>
                    {totals.grams} g • {totals.kcal} Cals • {totals.protein} g protein • {totals.carbs} g carbs • {totals.fat} g fat
                  </Text>
                </View>
              ) : null}
            </View>
          ) : null}

          

          {/* TIMINGS */}
          {result?.timings ? (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>TIMINGS</Text>
              {Object.entries(result!.timings!).map(([k, v]) => (
                <View style={styles.rowBetween} key={k}>
                  <Text style={styles.timingLabel}>{k.replace('_', ' ')}</Text>
                  <Text style={styles.timingValue}>{(Number(v) / 1000).toFixed(2)} s</Text>
                </View>
              ))}
              {typeof result!.total_ms === 'number' ? (
                <View style={[styles.rowBetween, { marginTop: 6 }]}> 
                  <Text style={styles.timingLabelBold}>Total</Text>
                  <Text style={styles.timingValueBold}>{(result!.total_ms / 1000).toFixed(2)} s</Text>
                </View>
              ) : null}
            </View>
          ) : null}
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  title: {
    fontSize: 22,
    fontWeight: '600',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 15,
    color: '#666',
  },
  actions: {
    marginTop: 16,
  },
  previewWrap: {
    marginTop: 16,
    alignItems: 'center',
  },
  preview: {
    width: '100%',
    height: 280,
    borderRadius: 12,
    backgroundColor: '#f4f4f4',
  },
  gallery: {
    marginTop: 16,
  },
  thumb: {
    width: 120,
    height: 120,
    borderRadius: 12,
    backgroundColor: '#f4f4f4',
  },
  result: {
    marginTop: 16,
  },
  resultTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#eee',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
    color: '#666',
    letterSpacing: 1,
  },
  dishName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  badge: {
    marginTop: 4,
    alignSelf: 'flex-start',
    backgroundColor: '#eef',
    color: '#334',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
  },
  tagsWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 8,
  },
  tag: {
    backgroundColor: '#f5f5f5',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
  },
  rowBetween: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  grid4: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
  buttonRow: {
    marginTop: 16,
    flexDirection: 'row',
    gap: 12,
  },
  half: {
    flex: 1,
  },
  tile: {
    width: '48%',
    backgroundColor: '#fafafa',
    borderRadius: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: '#eee',
  },
  tileTitle: {
    color: '#666',
    marginBottom: 4,
  },
  tileValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  totalsContainer: {
    marginTop: 8,
  },
  totalsTitle: {
    fontWeight: '600',
    marginBottom: 4,
  },
  totalsLine: {
    fontWeight: '600',
    flexWrap: 'wrap',
  },
  noteText: {
    color: '#666',
    fontSize: 12,
    marginBottom: 4,
  },
  gramsInput: {
    minWidth: 64,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 6,
    color: '#333',
  },
  macroStrip: {
    color: '#666',
  },
  ingName: {
    color: '#444',
    fontWeight: '500',
  },
  timingLabel: {
    color: '#666',
  },
  timingValue: {
    color: '#333',
    fontWeight: '500',
  },
  timingLabelBold: {
    color: '#444',
    fontWeight: '600',
  },
  timingValueBold: {
    color: '#111',
    fontWeight: '700',
  },
});
