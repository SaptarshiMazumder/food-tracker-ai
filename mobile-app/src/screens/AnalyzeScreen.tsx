import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Image, Alert, ActivityIndicator, ScrollView, Animated, TextInput, TouchableOpacity } from 'react-native';
import { Colors } from '../theme/colors';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Circle, Text as SvgText } from 'react-native-svg';
import PrimaryButton from '../components/PrimaryButton';
import * as DocumentPicker from 'expo-document-picker';
import { uploadAnalyzeImage, AnalysisResponse, analyzeStream } from '../services/api';
import { mealLogger } from '../services/mealLogger';
import { buildUiItems, computeTotals, UiItem, UiTotals } from '../services/uiBuilder';
import Slider from '@react-native-community/slider';

type CircularProgressProps = {
  size: number;
  trackWidth?: number;
  progressWidth?: number;
  progress: number; // 0..1
  trackColor?: string;
  progressColor?: string;
  trackOpacity?: number;
  progressOpacity?: number;
  labelColor?: string;
  labelFontSize?: number;
  labelDy?: number;
};

function CircularProgress({ size, trackWidth = 4, progressWidth = 7, progress, trackColor = Colors.sliderInactive, progressColor = Colors.primary, trackOpacity = 0.5, progressOpacity = 1, labelColor = Colors.neutralText, labelFontSize = 11, labelDy = 0 }: CircularProgressProps) {
  const clamped = Math.max(0, Math.min(1, progress || 0));
  const maxStroke = Math.max(trackWidth, progressWidth);
  const radius = (size - maxStroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - clamped);
  const center = size / 2;
  return (
    <Svg width={size} height={size}>
      <Circle
        cx={center}
        cy={center}
        r={radius}
        stroke={trackColor}
        strokeOpacity={trackOpacity}
        strokeWidth={trackWidth}
        fill="none"
      />
      <Circle
        cx={center}
        cy={center}
        r={radius}
        stroke={progressColor}
        strokeOpacity={progressOpacity}
        strokeWidth={progressWidth}
        strokeDasharray={`${circumference} ${circumference}`}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
        fill="none"
        transform={`rotate(-90 ${center} ${center})`}
      />
      <SvgText
        x={center}
        y={center}
        dy={labelDy}
        fill={labelColor}
        fontSize={labelFontSize}
        fontWeight="500"
        textAnchor="middle"
        alignmentBaseline="middle"
      >
        {`${Math.round(clamped * 100)}%`}
      </SvgText>
    </Svg>
  );
}

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
  const [hasAnalyzed, setHasAnalyzed] = useState(false);

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
      setHasAnalyzed(false);
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
            try {
              mealLogger.logFromAnalysis(res, 'gemini', 'gemini');
            } catch {}
            return res;
          });
          setHasAnalyzed(true);
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
      {/* Compute macro percentages for rings */}
      {(() => {
        return null;
      })()}
      <View style={styles.actions}>
        <PrimaryButton
          title="Upload Image(s)"
          onPress={onUpload}
          disabled={loading}
          style={{ backgroundColor: Colors.primary, borderWidth: 0 }}
          textStyle={{ color: '#ffffff' }}
          disabledStyle={{ backgroundColor: Colors.neutralSurface, borderWidth: 0 }}
          disabledTextStyle={{ color: Colors.neutralText }}
          leftIcon={<Ionicons name="images-outline" size={18} color="#ffffff" style={styles.iconAlignUp} />}
        />
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
          <PrimaryButton
            title={hasAnalyzed && !loading ? "Analyze again" : "Analyze"}
            onPress={onAnalyze}
            disabled={selectedUris.length === 0 || loading}
            style={{ backgroundColor: Colors.primary, borderWidth: 0 }}
            textStyle={{ color: '#ffffff' }}
            disabledStyle={{ backgroundColor: Colors.neutralSurface, borderWidth: 0 }}
            disabledTextStyle={{ color: Colors.neutralText }}
            leftIcon={hasAnalyzed && !loading ? (<Ionicons name="refresh-outline" size={18} color="#ffffff" style={styles.iconAlignUp} />) : undefined}
          />
        </View>
        <View style={styles.half}>
          <PrimaryButton title="Clear" onPress={() => {
            if (loading) return;
            setSelectedUris([]);
            setResult(null);
            setUiItems([]);
            setGrams([]);
            setTotals(null);
            setStarted(false);
            setGotRecognize(false);
            setGotIngr(false);
            setGotCalories(false);
            setLoading(false);
            setHasAnalyzed(false);
          }} disabled={selectedUris.length === 0 || loading}
            style={{ backgroundColor: '#f2f2f2', borderWidth: 0 }}
            textStyle={{ color: '#444444' }}
            disabledStyle={{ backgroundColor: '#e9e9e9', borderWidth: 0 }}
            disabledTextStyle={{ color: '#999999' }}
          />
        </View>
      </View>

      {loading ? (
        <View style={{ marginTop: 16 }}>
          <ActivityIndicator size="large" />
          <Text style={{ marginTop: 8 }}>Working… you'll see results step-by-step.</Text>
        </View>
      ) : null}

      {started ? (
        <View style={styles.result}>
          {/* 1. FOOD */}
          <View style={styles.card}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Text style={styles.sectionTitle}>1. FOOD</Text>
              <Ionicons name="fast-food-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
            </View>
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
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Text style={styles.sectionTitle}>2. MACROS</Text>
                <Ionicons name="stats-chart-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
              </View>
              {typeof result?.total_grams === 'number' ? (
                <View style={styles.accentBubble}><Text style={styles.accentBubbleText}>{result!.total_grams} g total</Text></View>
              ) : null}
            </View>
            {gotCalories && Array.isArray(result?.items_nutrition) && result!.items_nutrition!.length > 0 ? (
              <>
                {(() => {
                  const totalG = typeof result?.total_grams === 'number' && result!.total_grams > 0 ? result!.total_grams : 0;
                  const p = totalG > 0 && typeof result?.total_protein_g === 'number' ? result!.total_protein_g / totalG : 0;
                  const c = totalG > 0 && typeof result?.total_carbs_g === 'number' ? result!.total_carbs_g / totalG : 0;
                  const f = totalG > 0 && typeof result?.total_fat_g === 'number' ? result!.total_fat_g / totalG : 0;
                  return (
                    <View style={styles.grid4}>
                      <View style={styles.tile}>
                        {/* Center ring overlay if needed (not for calories) */}
                        <View style={styles.rowBetween}>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                            <Text style={styles.tileTitle}>Calories</Text>
                            <MaterialCommunityIcons name="fire" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
                          </View>
                        </View>
                        <Text style={styles.tileValue}>{result!.total_kcal}</Text>
                      </View>
                      <View style={styles.tile}>
                        <View style={styles.ringRightOverlay} pointerEvents="none">
                          <CircularProgress size={56} trackWidth={4} progressWidth={7} progress={p} trackOpacity={0.35} progressColor={Colors.macroProtein} labelColor={Colors.neutralText} labelFontSize={14} labelDy={2} />
                        </View>
                        <View style={styles.ringedContent}>
                          <View style={styles.rowBetween}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                              <Text style={styles.tileTitle}>Protein</Text>
                              <MaterialCommunityIcons name="dumbbell" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
                            </View>
                          </View>
                          <Text style={styles.tileValue}>{result!.total_protein_g} g</Text>
                        </View>
                      </View>
                      <View style={styles.tile}>
                        <View style={styles.ringRightOverlay} pointerEvents="none">
                          <CircularProgress size={56} trackWidth={4} progressWidth={7} progress={c} trackOpacity={0.35} progressColor={Colors.macroCarbs} labelColor={Colors.neutralText} labelFontSize={14} labelDy={2} />
                        </View>
                        <View style={styles.ringedContent}>
                          <View style={styles.rowBetween}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                              <Text style={styles.tileTitle}>Carbs</Text>
                              <MaterialCommunityIcons name="bread-slice-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
                            </View>
                          </View>
                          <Text style={styles.tileValue}>{result!.total_carbs_g} g</Text>
                        </View>
                      </View>
                      <View style={styles.tile}>
                        <View style={styles.ringRightOverlay} pointerEvents="none">
                          <CircularProgress size={56} trackWidth={4} progressWidth={7} progress={f} trackOpacity={0.35} progressColor={Colors.macroFat} labelColor={Colors.neutralText} labelFontSize={14} labelDy={2} />
                        </View>
                        <View style={styles.ringedContent}>
                          <View style={styles.rowBetween}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                              <Text style={styles.tileTitle}>Fat</Text>
                              <MaterialCommunityIcons name="water-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
                            </View>
                          </View>
                          <Text style={styles.tileValue}>{result!.total_fat_g} g</Text>
                        </View>
                      </View>
                    </View>
                  );
                })()}
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
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Text style={styles.sectionTitle}>3. INGREDIENTS PORTIONS</Text>
                <Ionicons name="scale-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
              </View>
            </View>
            {gotIngr ? (
              Array.isArray(result?.items_grams) && result!.items_grams!.length > 0 ? (
                <>
                  {result!.items_grams!.map((it: { name: string; grams: number; note?: string }, i: number) => (
                    <View key={i} style={styles.rowBetween}>
                      <Text>{it.name}</Text>
                      <View style={styles.neutralBubble}><Text style={styles.neutralBubbleText}>{it.grams} g</Text></View>
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
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Text style={styles.sectionTitle}>ADJUST PORTIONS</Text>
                <Ionicons name="create-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
              </View>
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
                      <TouchableOpacity
                        activeOpacity={0.7}
                        style={styles.resetBtn}
                        onPress={() => {
                          const next = [...grams];
                          next[i] = u.baseGrams;
                          setGrams(next);
                          setTotals(computeTotals(uiItems, next));
                        }}
                      >
                        <Text style={styles.resetBtnText}>Reset</Text>
                      </TouchableOpacity>
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
                    style={{ height: 36 }}
                    minimumTrackTintColor={Colors.sliderActive}
                    maximumTrackTintColor={Colors.sliderInactive}
                    thumbTintColor={Colors.sliderActive}
                    onValueChange={(val) => {
                      const next = [...grams];
                      next[i] = Math.round(val as number);
                      setGrams(next);
                      setTotals(computeTotals(uiItems, next));
                    }}
                  />
                  <View style={styles.macroRow}>
                    <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Cals </Text><Text style={styles.macroPillValue}>{(u.kcalPerG * (grams[i] ?? u.baseGrams)).toFixed(0)}</Text></View>
                    <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Protein </Text><Text style={styles.macroPillValue}>{(u.proteinPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g</Text></View>
                    <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Carbs </Text><Text style={styles.macroPillValue}>{(u.carbsPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g</Text></View>
                    <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Fats </Text><Text style={styles.macroPillValue}>{(u.fatPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g</Text></View>
                  </View>
                  <Text style={styles.perGText}>(
                    {u.kcalPerG.toFixed(2)} kcal/g
                  )</Text>
                </View>
              ))}
              {totals ? (
                <View style={styles.totalsContainer}>
                  <Text style={styles.totalsTitle}>Adjusted totals</Text>
                  <View style={styles.macroRow}>
                    <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Cals </Text><Text style={styles.macroPillValue}>{totals.kcal}</Text></View>
                    <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Protein </Text><Text style={styles.macroPillValue}>{totals.protein} g</Text></View>
                    <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Carbs </Text><Text style={styles.macroPillValue}>{totals.carbs} g</Text></View>
                    <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Fats </Text><Text style={styles.macroPillValue}>{totals.fat} g</Text></View>
                  </View>
                </View>
              ) : null}
            </View>
          ) : null}

          

          {/* processing time */}
          {result?.timings ? (
            <View style={styles.card}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Text style={styles.sectionTitle}>PROCESSING TIME</Text>
                <Ionicons name="time-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
              </View>
              {Object.entries(result!.timings!).map(([k, v]) => {
                let label = k.replace('_', ' ');
                if (k === 'recognize_ms') label = 'identify food';
                if (k === 'ing_quant_ms') label = 'identify ingredients quantity';
                if (k === 'calories_ms') label = 'calculate macros';
                return (
                  <View style={styles.rowBetween} key={k}>
                    <Text style={styles.timingLabel}>{label}</Text>
                    <View style={styles.neutralBubble}><Text style={styles.neutralBubbleText}>{(Number(v) / 1000).toFixed(2)} s</Text></View>
                  </View>
                );
              })}
              {typeof result!.total_ms === 'number' ? (
                <View style={[styles.rowBetween, { marginTop: 6 }]}> 
                  <Text style={styles.timingLabelBold}>Total</Text>
                  <View style={styles.neutralBubble}><Text style={styles.neutralBubbleText}>{(result!.total_ms / 1000).toFixed(2)} s</Text></View>
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
    // subtle, centered, blurred shadow
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 50,
    elevation: 2,
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
    backgroundColor: Colors.accentSurface,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    color: Colors.accentText,
  },
  accentBubble: {
    backgroundColor: Colors.accentSurface,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    transform: [{ translateY: -3 }],
  },
  accentBubbleText: {
    color: Colors.accentText,
    fontWeight: '400',
  },
  neutralBubble: {
    backgroundColor: Colors.neutralSurface,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    transform: [{ translateY: -1 }],
  },
  neutralBubbleText: {
    color: Colors.neutralText,
    fontWeight: '400',
  },
  iconAlignUp: {
    transform: [{ translateY: -2 }],
  },
  ringOverlay: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringRightOverlay: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    right: 6,
    width: 64,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringedContent: {
    paddingRight: 72,
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
    minWidth: 56,
    height: 28,
    paddingVertical: 0,
    paddingHorizontal: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#888',
    borderRadius: 8,
    backgroundColor: '#fff',
    color: '#333',
    fontSize: 13,
  },
  macroStrip: {
    color: '#666',
  },
  macroRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 6,
  },
  macroPill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: '#f1f1f1',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#d0d0d0',
  },
  macroPillLabel: {
    color: '#444',
    fontWeight: '400',
    fontSize: 11,
    textTransform: 'capitalize',
  },
  macroPillValue: {
    color: '#333',
    fontWeight: '600',
    fontSize: 11,
  },
  perGText: {
    color: '#666',
    fontSize: 12,
    marginTop: 4,
  },
  ingName: {
    color: '#111111',
    fontWeight: '400',
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
  resetBtn: {
    paddingHorizontal: 8,
    height: 28,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 10,
    backgroundColor: '#fff',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#777',
  },
  resetBtnText: {
    color: '#333',
    fontWeight: '500',
    fontSize: 12,
  },
});
