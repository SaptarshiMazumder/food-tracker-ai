import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, ScrollView } from 'react-native';
import PrimaryButton from '../components/PrimaryButton';

export default function RagScreen() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<string | null>(null);

  const onAsk = () => {
    // TODO: call RAG backend endpoint
    setResult('Sample answer will appear here.');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>RAG Query</Text>
      <TextInput
        placeholder="Ask about recipes, ingredients, nutrition..."
        value={query}
        onChangeText={setQuery}
        style={styles.input}
      />
      <PrimaryButton title="Ask" onPress={onAsk} />
      <ScrollView style={styles.result} contentContainerStyle={{ paddingVertical: 8 }}>
        {result ? <Text>{result}</Text> : <Text style={{ color: '#888' }}>No results yet.</Text>}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: '600',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 12,
  },
  result: {
    marginTop: 12,
  },
});


