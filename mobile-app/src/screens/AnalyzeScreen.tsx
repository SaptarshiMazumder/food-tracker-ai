import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Image, Alert, ActivityIndicator, ScrollView, Animated, TextInput, TouchableOpacity } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '../theme/colors';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Circle, Text as SvgText } from 'react-native-svg';
import PrimaryButton from '../components/PrimaryButton';
import Card from '../components/Card';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { uploadAnalyzeImage, AnalysisResponse, analyzeStream, getHealthScore, HealthScoreInput, HealthScoreOutput } from '../services/api';
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
  const insets = useSafeAreaInsets();
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
  const [healthScore, setHealthScore] = useState<HealthScoreOutput | null>(null);
  const [healthScoreLoading, setHealthScoreLoading] = useState(false);
  const [loggedMealId, setLoggedMealId] = useState<string | null>(null);
  const [showSavedNotification, setShowSavedNotification] = useState(false);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [previewUri, setPreviewUri] = useState<string | null>(null);
  const [editsDirty, setEditsDirty] = useState(false);

  const onDownloadPreview = async () => {
    try {
      if (!previewUri) return;
      const MediaLibrary: any = await import('expo-media-library');
      const FileSystem: any = await import('expo-file-system');
      const perm = await MediaLibrary.requestPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Permission needed', 'Allow Photos access to save the image.');
        return;
      }
      let localUri = previewUri;
      if (!previewUri.startsWith('file://')) {
        const fname = `food-preview-${Date.now()}.jpg`;
        const target = FileSystem.cacheDirectory + fname;
        const dl = await FileSystem.downloadAsync(previewUri, target);
        localUri = dl.uri;
      }
      const asset = await MediaLibrary.createAssetAsync(localUri);
      try { await MediaLibrary.createAlbumAsync('Food Analyzer', asset, false); } catch {}
      Alert.alert('Saved', 'Image saved to Photos.');
    } catch (e: any) {
      Alert.alert('Save failed', e?.message || 'Install expo-file-system and expo-media-library');
    }
  };

  const onSaveEditsToLog = () => {
    try {
      if (!loggedMealId || !result) return;
      // Build patch from current UI state
      const patch: any = {
        dish: result.dish,
        ingredients_detected: Array.isArray(result.ingredients_detected) ? result.ingredients_detected : [],
        items_grams: Array.isArray(result.items_grams) ? result.items_grams : [],
        items_nutrition: Array.isArray(result.items_nutrition) ? result.items_nutrition : [],
        total_kcal: totals ? totals.kcal : result.total_kcal,
        total_protein_g: totals ? totals.protein : result.total_protein_g,
        total_carbs_g: totals ? totals.carbs : result.total_carbs_g,
        total_fat_g: totals ? totals.fat : result.total_fat_g,
        total_grams: totals ? totals.grams : result.total_grams,
      };
      mealLogger.updateMeal(loggedMealId, patch);
      setShowSavedNotification(true);
      setEditsDirty(false);
      setTimeout(() => setShowSavedNotification(false), 2000);
      Alert.alert('Saved', 'Edits saved to Logs.');
    } catch (e: any) {
      Alert.alert('Save failed', e?.message || 'Could not save edits');
    }
  };

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

  const onTakePhoto = async () => {
    try {
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

      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Permission needed', 'Camera access is required to take a photo.');
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 0.9,
        exif: false,
      });
      if (result.canceled) return;
      const uri = result.assets && result.assets[0] ? result.assets[0].uri : undefined;
      if (uri) {
        setSelectedUris([uri]);
        setHasAnalyzed(false);
      }
    } catch (e: any) {
      Alert.alert('Camera error', e?.message || 'Could not open camera');
    }
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
      setEditsDirty(false);
      setGotRecognize(false);
      setGotIngr(false);
      setGotCalories(false);
      setHealthScore(null);
      setHealthScoreLoading(false);
      setLoggedMealId(null);
      setShowSavedNotification(false);
      // Streaming flow exactly like web UI with Gemini only (no LogMeal)
      const stream = await analyzeStream(selectedUris, { model: 'gemini-2.5-pro', useLogmeal: false });
      const acc: any = {};
      for await (const ev of stream) {
        if (ev.phase === 'recognize') {
          Object.assign(acc, ev.data);
          setGotRecognize(true);
          // Update result so FOOD section renders immediately
          setResult((prev) => ({ ...(prev || {}), ...acc }));
        } else if (ev.phase === 'ing_quant') {
          Object.assign(acc, ev.data);
          setGotIngr(true);
          // Update result so INGREDIENTS section renders immediately
          setResult((prev) => ({ ...(prev || {}), ...acc }));
        } else if (ev.phase === 'calories') {
          Object.assign(acc, ev.data);
          setGotCalories(true);
          setResult((prev) => {
            const next = { ...(prev || {}), ...acc } as AnalysisResponse;
            // Build UI items as soon as calories arrive (if grams + nutrition available)
            if (Array.isArray(next.items_grams) && Array.isArray(next.items_nutrition)) {
              const ui = buildUiItems(next);
              setUiItems(ui);
              const baseGrams = ui.map((u) => u.baseGrams);
              setGrams(baseGrams);
              setTotals(computeTotals(ui, baseGrams));
            }
            return next;
          });
        } else if (ev.phase === 'done') {
          Object.assign(acc, ev.data);
          // Compose final result snapshot
          const finalRes = { ...(acc) } as AnalysisResponse;
          // Ensure UI items/totals are computed if not already
          if (uiItems.length === 0 && Array.isArray(finalRes.items_grams) && Array.isArray(finalRes.items_nutrition)) {
            const ui = buildUiItems(finalRes);
            setUiItems(ui);
            const baseGrams = ui.map((u) => u.baseGrams);
            setGrams(baseGrams);
            setTotals(computeTotals(ui, baseGrams));
          }
          setResult(finalRes);
          // Log meal and capture id
          try {
            const logged = mealLogger.logFromAnalysis(finalRes, 'gemini', 'gemini');
            setLoggedMealId(logged.id);
            setEditsDirty(false);
            setShowSavedNotification(true);
            setTimeout(() => setShowSavedNotification(false), 3000);
          } catch {}
          // Trigger health score fetch and persist
          try {
            const hsInput = buildHealthScoreInput(finalRes);
            if (hsInput) {
              setHealthScoreLoading(true);
              getHealthScore(hsInput)
                .then((hs) => {
                  setHealthScore(hs);
                  try {
                    if (loggedMealId) {
                      mealLogger.updateMeal(loggedMealId, { health_score: hs });
                    }
                  } catch {}
                })
                .catch(() => {})
                .finally(() => setHealthScoreLoading(false));
            }
          } catch {}
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

  function buildHealthScoreInput(res: AnalysisResponse): HealthScoreInput | null {
    if (
      typeof res?.total_kcal === 'number' &&
      typeof res?.total_grams === 'number' &&
      typeof res?.total_fat_g === 'number' &&
      typeof res?.total_protein_g === 'number' &&
      Array.isArray(res?.items_grams) &&
      res.items_grams.length > 0
    ) {
      return {
        total_kcal: res.total_kcal,
        total_grams: res.total_grams,
        total_fat_g: res.total_fat_g,
        total_protein_g: res.total_protein_g,
        items_grams: res.items_grams.map((it) => ({ name: it.name, grams: it.grams })),
        kcal_confidence: typeof res.kcal_confidence === 'number' ? res.kcal_confidence : 1.0,
        use_confidence_dampen: false,
      };
    }
    return null;
  }

  function renderHealthStars(score10: number) {
    const roundedToHalf = Math.round((score10 / 2) * 2) / 2; // 0..5 in 0.5 steps
    const color = getHealthColor(score10);
    const fullStars = Math.floor(roundedToHalf);
    return (
      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        {Array.from({ length: 5 }, (_, idx) => {
          const i = idx + 1;
          const isFull = i <= fullStars;
          const isHalf = !isFull && Math.abs(i - roundedToHalf - 0.5) < 1e-6;
          const name = isFull ? 'star' : isHalf ? 'star-half-full' : 'star-outline';
          return (
            <MaterialCommunityIcons
              key={idx}
              name={name as any}
              size={18}
              color={isFull || isHalf ? color : '#c7c7c7'}
              style={styles.iconAlignUp}
            />
          );
        })}
      </View>
    );
  }

  function getHealthColor(score10: number): string {
    // Clamp score
    const s = Math.max(0, Math.min(10, score10));
    // Define stops: 0=red, 5=yellow, 10=green
    const red = { r: 239, g: 68, b: 68 };    // #ef4444
    const yellow = { r: 245, g: 158, b: 11 }; // #f59e0b
    const green = { r: 34, g: 197, b: 94 };   // #22c55e
    const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * t);
    const toHex = (n: number) => n.toString(16).padStart(2, '0');

    if (s <= 5) {
      const t = s / 5; // 0..1 from red to yellow
      const r = lerp(red.r, yellow.r, t);
      const g = lerp(red.g, yellow.g, t);
      const b = lerp(red.b, yellow.b, t);
      return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    } else {
      const t = (s - 5) / 5; // 0..1 from yellow to green
      const r = lerp(yellow.r, green.r, t);
      const g = lerp(yellow.g, green.g, t);
      const b = lerp(yellow.b, green.b, t);
      return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    }
  }

  // No auto-analysis; user must press Analyze

  return (
    <View style={{ flex: 1 }}>
      {/* Portal-like absolute overlay based on window, not ScrollView */}
      {previewUri ? (
        <TouchableOpacity
          activeOpacity={1}
          onPress={() => setPreviewUri(null)}
          style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0, backgroundColor: '#000c', alignItems: 'center', justifyContent: 'center', zIndex: 9999, elevation: 10 }}
        >
          <View style={{ position: 'absolute', top: 50, right: 24, gap: 10 }}>
            <TouchableOpacity onPress={onDownloadPreview} style={{ backgroundColor: '#0009', width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name="download-outline" size={18} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setPreviewUri(null)} style={{ backgroundColor: '#0009', width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name="close" size={18} color="#fff" />
            </TouchableOpacity>
          </View>
          <Image source={{ uri: previewUri }} style={{ width: '92%', height: '80%', borderRadius: 12, resizeMode: 'contain' }} />
        </TouchableOpacity>
      ) : null}

      {/* Bottom Save bar will be rendered within content below sections */}

      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Removed explicit screen title per request */}
      <Text style={styles.subtitle}>Upload or take a photo to extract ingredients and calories.</Text>
      {/* toast rendered outside ScrollView for visibility */}
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
        <View style={{ height: 8 }} />
        <PrimaryButton
          title="Take Photo"
          onPress={onTakePhoto}
          disabled={loading}
          style={{ backgroundColor: Colors.primary, borderWidth: 0 }}
          textStyle={{ color: '#ffffff' }}
          disabledStyle={{ backgroundColor: Colors.neutralSurface, borderWidth: 0 }}
          disabledTextStyle={{ color: Colors.neutralText }}
          leftIcon={<Ionicons name="camera-outline" size={18} color="#ffffff" style={styles.iconAlignUp} />}
        />
        <Text style={{ marginTop: 6, color: '#777' }}>
          In the picker, long-press then tap multiple items to multi-select.
        </Text>
      </View>
      {selectedUris.length > 0 ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.gallery} contentContainerStyle={{ gap: 8 }}>
          {selectedUris.map((u, i) => (
            <View key={i}>
              <TouchableOpacity activeOpacity={0.9} onPress={() => setPreviewUri(u)}>
                <Image source={{ uri: u }} style={styles.thumb} />
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => {
                  if (loading) return; // Avoid removing during active upload stream
                  const next = selectedUris.filter((_, idx) => idx !== i);
                  setSelectedUris(next);
                }}
                style={{ position: 'absolute', top: 2, right: 2, backgroundColor: '#0009', width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' }}
              >
                <Ionicons name="close" size={12} color="#fff" />
              </TouchableOpacity>
            </View>
          ))}
        </ScrollView>
      ) : null}

      {/* image preview overlay moved outside ScrollView */}

      {selectedUris.length > 0 ? (
      <View style={styles.buttonRow}>
        <View style={styles.half}>
          <PrimaryButton
            title={hasAnalyzed && !loading ? "Analyze again" : "Analyze"}
            onPress={onAnalyze}
            disabled={loading}
            style={{ backgroundColor: Colors.primary, borderWidth: 0 }}
            textStyle={{ color: '#ffffff' }}
            disabledStyle={{ backgroundColor: Colors.neutralSurface, borderWidth: 0 }}
            disabledTextStyle={{ color: Colors.neutralText }}
            leftIcon={<Ionicons name={hasAnalyzed && !loading ? "refresh-outline" : "play"} size={18} color={loading ? Colors.neutralText : '#ffffff'} style={styles.iconAlignUp} />}
          />
        </View>
        <View style={styles.half}>
          <PrimaryButton title={loading ? "Stop" : "Clear"} onPress={() => {
            if (loading) {
              // Stop current analysis immediately by resetting streaming state
              setLoading(false);
              setStarted(false);
              setGotRecognize(false);
              setGotIngr(false);
              setGotCalories(false);
              setHealthScoreLoading(false);
              return;
            }
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
          }} disabled={!loading && selectedUris.length === 0}
            style={{ backgroundColor: loading ? '#fde68a' : '#f2f2f2', borderWidth: 0 }}
            textStyle={{ color: '#444444' }}
            disabledStyle={{ backgroundColor: '#e9e9e9', borderWidth: 0 }}
            disabledTextStyle={{ color: '#999999' }}
            leftIcon={loading ? (
              <Ionicons name="close" size={18} color="#444" style={styles.iconAlignUp} />
            ) : (
              <Ionicons name="trash-outline" size={18} color={selectedUris.length === 0 ? '#999999' : '#444'} style={styles.iconAlignUp} />
            )}
          />
        </View>
      </View>
      ) : null}

      {loading ? (
        <View style={{ marginTop: 16 }}>
          <ActivityIndicator size="large" />
          <Text style={{ marginTop: 8 }}>Working… you'll see results step-by-step.</Text>
        </View>
      ) : null}

      {started ? (
        <View style={styles.result}>
          {/* 1. FOOD */}
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Text style={styles.sectionTitle}>1. FOOD</Text>
              <Ionicons name="fast-food-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
            </View>
            {gotRecognize ? (
              <>
                {typeof result?.dish === 'string' ? (
                  <TextInput
                    style={[styles.dishName, { paddingVertical: 0, paddingHorizontal: 0, borderWidth: 0 }]}
                    value={result!.dish as string}
                    onChangeText={(txt) => {
                      setEditsDirty(true);
                      setResult((prev) => ({ ...(prev || {}), dish: txt }));
                    }}
                    placeholder="Dish name"
                    placeholderTextColor="#aaa"
                  />
                ) : null}
                {Array.isArray(result?.ingredients_detected) && result!.ingredients_detected!.length > 0 ? (
                  <View style={styles.tagsWrap}>
                    {result!.ingredients_detected!.map((tag: string, i: number) => (
                      <TextInput
                        key={i}
                        style={[styles.tag, { paddingVertical: 2, paddingHorizontal: 8 }]}
                        value={tag}
                        onChangeText={(txt) => setResult((prev) => {
                          setEditsDirty(true);
                          const next = { ...(prev || {}) } as any;
                          const arr = Array.isArray(next.ingredients_detected) ? [...next.ingredients_detected] : [];
                          arr[i] = txt;
                          next.ingredients_detected = arr;
                          return next;
                        })}
                      />
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
          </Card>
          <View style={{ height: 1, backgroundColor: '#eee', marginVertical: 8 }} />

          {/* 2. MACROS */}
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Text style={styles.sectionTitle}>2. MACROS</Text>
                <Ionicons name="stats-chart-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
              </View>
              {/* Save button moved to bottom sticky bar */}
              {typeof result?.total_grams === 'number' ? (
                <View style={styles.accentBubble}><Text style={styles.accentBubbleText}>{result!.total_grams} g total</Text></View>
              ) : null}
            </View>
            {gotCalories && Array.isArray(result?.items_nutrition) && result!.items_nutrition!.length > 0 ? (
              <>
                {(() => {
                  const useAdjusted = !!totals;
                  const macroG = useAdjusted ? (totals!.grams || 0) : (typeof result?.total_grams === 'number' ? (result!.total_grams || 0) : 0);
                  const macroProtein = useAdjusted ? (totals!.protein || 0) : (typeof result?.total_protein_g === 'number' ? (result!.total_protein_g || 0) : 0);
                  const macroCarbs = useAdjusted ? (totals!.carbs || 0) : (typeof result?.total_carbs_g === 'number' ? (result!.total_carbs_g || 0) : 0);
                  const macroFat = useAdjusted ? (totals!.fat || 0) : (typeof result?.total_fat_g === 'number' ? (result!.total_fat_g || 0) : 0);
                  const macroKcal = useAdjusted ? (totals!.kcal || 0) : (typeof result?.total_kcal === 'number' ? (result!.total_kcal || 0) : 0);
                  const totalG = macroG > 0 ? macroG : 0;
                  const p = totalG > 0 ? macroProtein / totalG : 0;
                  const c = totalG > 0 ? macroCarbs / totalG : 0;
                  const f = totalG > 0 ? macroFat / totalG : 0;
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
                        <Text style={styles.tileValue}>{macroKcal}</Text>
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
                          <Text style={styles.tileValue}>{macroProtein} g</Text>
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
                          <Text style={styles.tileValue}>{macroCarbs} g</Text>
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
                          <Text style={styles.tileValue}>{macroFat} g</Text>
                        </View>
                      </View>
                    </View>
                  );
                })()}
                {/* Removed description under macros per request */}
                {/* Health Score below macros */}
                <View style={{ marginTop: 10 }}>
                  <View style={styles.rowBetween}>
                    <Text style={styles.tileTitle}>Health Score</Text>
                    {healthScoreLoading ? (
                      <View style={styles.neutralBubble}><Text style={styles.neutralBubbleText}>analyzing…</Text></View>
                    ) : healthScore ? (
                      renderHealthStars(healthScore.health_score)
                    ) : null}
                  </View>
                </View>
              </>
            ) : (
              <View style={[styles.grid4, { width: '100%' }]}>
                <SkeletonTile />
                <SkeletonTile />
                <SkeletonTile />
                <SkeletonTile />
              </View>
            )}
          </Card>
          <View style={{ height: 1, backgroundColor: '#eee', marginVertical: 8 }} />

          {/* 3. INGREDIENTS (combined with adjust portions) */}
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Text style={styles.sectionTitle}>3. INGREDIENTS</Text>
                <Ionicons name="scale-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
              </View>
            </View>
            {gotIngr ? (
              Array.isArray(result?.items_grams) && result!.items_grams!.length > 0 ? (
                <>
                  {uiItems.length > 0 ? (
                    uiItems.map((u, i) => (
                      <View key={i} style={{ marginBottom: 12 }}>
                        <View style={styles.rowBetween}>
                          <TouchableOpacity
                            onPress={() => setExpanded((e) => ({ ...e, [i]: !e[i] }))}
                            activeOpacity={0.7}
                            style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 }}
                          >
                            <TextInput
                              style={[styles.ingName, { paddingVertical: 0, paddingHorizontal: 0, borderWidth: 0 }]}
                              value={u.name}
                              onChangeText={(txt) => {
                                // update uiItems and underlying result.items_grams name
                                setEditsDirty(true);
                                const nextUi = [...uiItems];
                                nextUi[i] = { ...nextUi[i], name: txt } as any;
                                setUiItems(nextUi);
                                setResult((prev) => {
                                  const r: any = { ...(prev || {}) };
                                  if (Array.isArray(r.items_grams)) {
                                    const g = [...r.items_grams];
                                    if (g[i]) g[i] = { ...g[i], name: txt };
                                    r.items_grams = g;
                                  }
                                  if (Array.isArray(r.items_nutrition)) {
                                    const n = [...r.items_nutrition];
                                    const idx = n.findIndex((x: any) => (x.name || '').toLowerCase() === (u.name || '').toLowerCase());
                                    if (idx >= 0) n[idx] = { ...n[idx], name: txt };
                                    r.items_nutrition = n;
                                  }
                                  return r;
                                });
                              }}
                            />
                            <Ionicons name={expanded[i] ? 'chevron-down' : 'chevron-forward'} size={18} color="#d0d0d0" style={{ transform: [{ translateY: 1 }] }} />
                          </TouchableOpacity>
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
                          </View>
                        </View>
                        {/* Always visible per-ingredient macros */}
                        <View style={styles.macroRow}>
                          <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Cals </Text><Text style={styles.macroPillValue}>{(u.kcalPerG * (grams[i] ?? u.baseGrams)).toFixed(0)}</Text></View>
                          <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Protein </Text><Text style={styles.macroPillValue}>{(u.proteinPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g</Text></View>
                          <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Carbs </Text><Text style={styles.macroPillValue}>{(u.carbsPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g</Text></View>
                          <View style={styles.macroPill}><Text style={styles.macroPillLabel}>Fats </Text><Text style={styles.macroPillValue}>{(u.fatPerG * (grams[i] ?? u.baseGrams)).toFixed(1)} g</Text></View>
                        </View>
                        {expanded[i] ? (
                          <>
                            {u.note ? (
                              <Text style={[styles.noteText, { marginTop: 2 }]}>{u.note}</Text>
                            ) : null}
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 }}>
                              <Slider
                                minimumValue={u.min}
                                maximumValue={u.max}
                                step={u.step}
                                value={grams[i] ?? u.baseGrams}
                                style={{ height: 36, flex: 1 }}
                                minimumTrackTintColor={Colors.sliderActive}
                                maximumTrackTintColor={Colors.sliderInactive}
                                thumbTintColor={Colors.sliderActive}
                                onValueChange={(val) => {
                                  const next = [...grams];
                                  next[i] = Math.round(val as number);
                                  setGrams(next);
                                  setTotals(computeTotals(uiItems, next));
                                  setEditsDirty(true);
                                }}
                              />
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
                            <Text style={[styles.perGText, { marginTop: 2 }]}>{u.kcalPerG.toFixed(2)} kcal/g</Text>
                          </>
                        ) : null}
                      </View>
                    ))
                  ) : (
                    // Before calories event: basic editable rows with default slider bounds
                    <>
                      {result!.items_grams!.map((it: { name: string; grams: number; note?: string }, i: number) => {
                        const base = typeof it.grams === 'number' ? it.grams : 0;
                        const min = Math.max(0, Math.floor(base * 0.2));
                        const max = Math.max(20, Math.ceil(base * 2.2));
                        return (
                          <View key={i} style={{ marginBottom: 12 }}>
                            <View style={styles.rowBetween}>
                              <TouchableOpacity
                                onPress={() => setExpanded((e) => ({ ...e, [i]: !e[i] }))}
                                activeOpacity={0.7}
                                style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 }}
                              >
                                <TextInput
                                  style={{ color: '#111111', paddingVertical: 0, paddingHorizontal: 0, borderWidth: 0 }}
                                  value={it.name}
                                  onChangeText={(txt) => {
                                    setEditsDirty(true);
                                    setResult((prev) => {
                                      const r: any = { ...(prev || {}) };
                                      if (Array.isArray(r.items_grams)) {
                                        const g = [...r.items_grams];
                                        if (g[i]) g[i] = { ...g[i], name: txt };
                                        r.items_grams = g;
                                      }
                                      return r;
                                    });
                                  }}
                                />
                                <Ionicons name={expanded[i] ? 'chevron-down' : 'chevron-forward'} size={18} color="#d0d0d0" style={{ transform: [{ translateY: 1 }] }} />
                              </TouchableOpacity>
                              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                                <TextInput
                                  style={styles.gramsInput}
                                  keyboardType="numeric"
                                  value={String(grams[i] ?? base)}
                                  onChangeText={(txt) => {
                                    const n = parseInt(txt || '0', 10);
                                    const clamped = isNaN(n) ? 0 : Math.max(min, Math.min(max, n));
                                    const next = [...grams];
                                    next[i] = clamped;
                                    setGrams(next);
                                  }}
                                />
                                <Text>g</Text>
                              </View>
                            </View>
                            {expanded[i] ? (
                              <>
                                {it.note ? (
                                  <Text style={[styles.noteText, { marginTop: 2 }]}>{it.note}</Text>
                                ) : null}
                                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 }}>
                                  <Slider
                                    minimumValue={min}
                                    maximumValue={max}
                                    step={1}
                                    value={grams[i] ?? base}
                                    style={{ height: 36, flex: 1 }}
                                    minimumTrackTintColor={Colors.sliderActive}
                                    maximumTrackTintColor={Colors.sliderInactive}
                                    thumbTintColor={Colors.sliderActive}
                                    onValueChange={(val) => {
                                      const next = [...grams];
                                      next[i] = Math.round(val as number);
                                      setGrams(next);
                                      setEditsDirty(true);
                                    }}
                                  />
                                  <TouchableOpacity
                                    activeOpacity={0.7}
                                    style={styles.resetBtn}
                                    onPress={() => {
                                      const next = [...grams];
                                      next[i] = base;
                                      setGrams(next);
                                    }}
                                  >
                                    <Text style={styles.resetBtnText}>Reset</Text>
                                  </TouchableOpacity>
                                </View>
                              </>
                            ) : null}
                          </View>
                        );
                      })}
                    </>
                  )}
                  {/* Removed Adjusted totals section to avoid duplication with MACROS */}
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
          </Card>
          <View style={{ height: 1, backgroundColor: '#eee', marginVertical: 8 }} />

          

          {/* processing time */}
          {result?.timings ? (
            <Card>
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
            </Card>
          ) : null}

          {/* Bottom in-flow Save button; visible only after analysis began */}
          {started ? (
            <View style={{ marginTop: 16, paddingBottom: 16 }}>
              <TouchableOpacity
                onPress={() => { if (editsDirty && loggedMealId) onSaveEditsToLog(); }}
                disabled={!(editsDirty && !!loggedMealId)}
                activeOpacity={0.8}
                style={{
                  backgroundColor: editsDirty && loggedMealId ? '#86efac' : '#e5e7eb',
                  paddingVertical: 12,
                  borderRadius: 12,
                  alignItems: 'center',
                  flexDirection: 'row',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                <Ionicons
                  name="document-text-outline"
                  size={18}
                  color={editsDirty && loggedMealId ? '#064e3b' : '#9ca3af'}
                  style={styles.iconAlignUp}
                />
                <Text style={{ color: editsDirty && loggedMealId ? '#064e3b' : '#9ca3af', fontWeight: '700' }}>Save changes</Text>
              </TouchableOpacity>
            </View>
          ) : null}
        </View>
      ) : null}
      </ScrollView>
      {showSavedNotification ? (
        <View style={styles.toast} pointerEvents="none">
          <Text style={styles.toastText}>Meal details saved to logs</Text>
          <Ionicons name="checkmark-circle" size={18} color="#ffffff" style={styles.iconAlignUp} />
        </View>
      ) : null}
    </View>
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
  toast: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 0,
    backgroundColor: '#22c55e',
    borderWidth: 0,
    paddingHorizontal: 16,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 2,
  },
  toastText: {
    color: '#ffffff',
    fontWeight: '700',
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
