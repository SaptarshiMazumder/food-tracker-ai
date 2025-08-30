import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';

const SAMPLE_MEALS = [
  { id: '1', title: 'Oatmeal with Berries', calories: 320 },
  { id: '2', title: 'Grilled Chicken Salad', calories: 450 },
];

export default function MealsScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Meal Log</Text>
      <FlatList
        data={SAMPLE_MEALS}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.mealRow}>
            <Text style={styles.mealTitle}>{item.title}</Text>
            <Text style={styles.mealCals}>{item.calories} kcal</Text>
          </View>
        )}
        ItemSeparatorComponent={() => <View style={styles.sep} />}
        contentContainerStyle={{ paddingVertical: 8 }}
      />
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
  mealRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
  },
  mealTitle: {
    fontSize: 16,
  },
  mealCals: {
    fontSize: 14,
    color: '#666',
  },
  sep: {
    height: 1,
    backgroundColor: '#eee',
  },
});


