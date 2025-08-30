import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Button, Image, Alert, ActivityIndicator, ScrollView } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { uploadAnalyzeImage, AnalysisResponse, analyzeStream } from '../services/api';

export default function AnalyzeScreen() {
  const [selectedUri, setSelectedUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  const pickWithDocumentPicker = async () => {
    try {
      const doc = await DocumentPicker.getDocumentAsync({
        type: ['image/*'],
        multiple: false,
        copyToCacheDirectory: true,
      });
      if (doc.canceled) return;
      const asset = (doc as any).assets?.[0] || (doc as any);
      if (asset?.uri) {
        setSelectedUri(asset.uri);
      }
    } catch (e: any) { // Added type annotation for e
      Alert.alert('Picker error', `Could not open any picker. Error: ${e.message}`); // Display error message
    }
  };

  const onUpload = async () => {
    // Prefer Document Picker first (works without Google Play on emulators)
    try {
      await pickWithDocumentPicker();
      if (selectedUri) return;
    } catch {}

    // If user canceled or failed, try the system image library
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission required', 'Please allow photo library access to pick an image.');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        quality: 0.8,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        setSelectedUri(result.assets[0].uri);
      }
    } catch (e: any) {
      Alert.alert('Picker error', `Could not open any picker. Error: ${e.message}`);
    }
  };

  useEffect(() => {
    const runAnalysis = async () => {
      if (!selectedUri) return;
      try {
        setLoading(true);
        setResult(null);
        // Streaming flow to match web behavior
        const stream = await analyzeStream(selectedUri, { model: 'gemini-2.5-pro', useLogmeal: true });
        const acc: any = {};
        for await (const ev of stream) {
          if (ev.phase === 'recognize') {
            Object.assign(acc, ev.data);
          } else if (ev.phase === 'ing_quant') {
            Object.assign(acc, ev.data);
          } else if (ev.phase === 'calories') {
            Object.assign(acc, ev.data);
          } else if (ev.phase === 'done') {
            Object.assign(acc, ev.data);
            break;
          }
        }
        // Fallback to non-logmeal if portions look collapsed
        if (!acc.items_grams || acc.items_grams.length <= 1) {
          try {
            const res2 = await uploadAnalyzeImage(selectedUri, { model: 'gemini-2.5-pro', useLogmeal: false });
            Object.assign(acc, res2);
          } catch {}
        }
        setResult(acc);
      } catch (e: any) {
        Alert.alert('Analyze failed', e?.message || 'Unknown error');
      } finally {
        setLoading(false);
      }
    };
    runAnalysis();
  }, [selectedUri]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Analyze Meal</Text>
      <Text style={styles.subtitle}>Upload a photo to extract ingredients and calories.</Text>
      <View style={styles.actions}>
        <Button title="Upload Image" onPress={onUpload} />
      </View>
      {selectedUri ? (
        <View style={styles.previewWrap}>
          <Image source={{ uri: selectedUri }} style={styles.preview} />
        </View>
      ) : null}

      {loading ? (
        <View style={{ marginTop: 16 }}>
          <ActivityIndicator size="large" />
          <Text style={{ marginTop: 8 }}>Analyzing...</Text>
        </View>
      ) : null}

      {!loading && result ? (
        <View style={styles.result}>
          {/* 1. Recognize */}
          {result.dish ? (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>1. Recognize</Text>
              <Text style={styles.dishName}>{result.dish}</Text>
              {typeof result.dish_confidence === 'number' ? (
                <Text style={styles.badge}>Conf {result.dish_confidence.toFixed(2)}</Text>
              ) : null}
              {Array.isArray(result.ingredients_detected) && result.ingredients_detected.length > 0 ? (
                <View style={styles.tagsWrap}>
                  {result.ingredients_detected.map((tag: string, i: number) => (
                    <Text key={i} style={styles.tag}>{tag}</Text>
                  ))}
                </View>
              ) : null}
            </View>
          ) : null}

          {/* 2. Portion (grams) */}
          {Array.isArray(result.items_grams) && result.items_grams.length > 0 ? (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>2. Portion (grams) {typeof result.total_grams === 'number' ? `(${result.total_grams} g total)` : ''}</Text>
              {result.items_grams.map((it: { name: string; grams: number; note?: string }, i: number) => (
                <View key={i} style={styles.rowBetween}>
                  <Text>{it.name}</Text>
                  <Text>{it.grams} g</Text>
                </View>
              ))}
            </View>
          ) : null}

          {/* 3. Calories & Macros */}
          {Array.isArray(result.items_nutrition) && result.items_nutrition.length > 0 ? (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>3. Calories & Macros</Text>
              <View style={styles.grid4}>
                <View style={styles.tile}><Text style={styles.tileTitle}>Total kcal</Text><Text style={styles.tileValue}>{result.total_kcal}</Text></View>
                <View style={styles.tile}><Text style={styles.tileTitle}>Protein</Text><Text style={styles.tileValue}>{result.total_protein_g} g</Text></View>
                <View style={styles.tile}><Text style={styles.tileTitle}>Carbs</Text><Text style={styles.tileValue}>{result.total_carbs_g} g</Text></View>
                <View style={styles.tile}><Text style={styles.tileTitle}>Fat</Text><Text style={styles.tileValue}>{result.total_fat_g} g</Text></View>
              </View>
              {result.notes ? <Text style={{ marginTop: 8 }}>{result.notes}</Text> : null}
            </View>
          ) : null}

          {/* Timings */}
          {result.timings ? (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Processing time</Text>
              {Object.entries(result.timings).map(([k, v]) => (
                <View style={styles.rowBetween} key={k}>
                  <Text>{k.replace('_', ' ')}</Text>
                  <Text>{v} ms</Text>
                </View>
              ))}
              {typeof result.total_ms === 'number' ? (
                <View style={[styles.rowBetween, { marginTop: 6 }]}> 
                  <Text style={{ fontWeight: '600' }}>Total</Text>
                  <Text style={{ fontWeight: '600' }}>{result.total_ms} ms</Text>
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
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  dishName: {
    fontSize: 18,
    fontWeight: '700',
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
});
