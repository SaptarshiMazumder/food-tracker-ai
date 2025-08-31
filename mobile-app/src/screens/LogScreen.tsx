import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ScrollView } from 'react-native';
import { Colors } from '../theme/colors';
import { mealLogger, LoggedMeal, DailyMealLog } from '../services/mealLogger';
import { MaterialIcons } from '@expo/vector-icons';

function startOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay(); // 0..6, Sun..Sat
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - day);
  return d;
}

function formatDateNice(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
}

function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function LogScreen() {
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(() => startOfWeek(new Date()));
  const [log, setLog] = useState<DailyMealLog>(() => mealLogger.getDailyMealLog(selectedDate));
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<LoggedMeal[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLog(mealLogger.getDailyMealLog(selectedDate));
  }, [selectedDate]);

  useEffect(() => {
    const unsub = mealLogger.subscribe(() => {
      setLog(mealLogger.getDailyMealLog(selectedDate));
    });
    return unsub;
  }, [selectedDate]);

  const weekDays = useMemo(() => {
    const days: Array<{ date: Date; dateString: string; dayName: string; isToday: boolean; isSelected: boolean; }> = [];
    const todayStr = new Date().toISOString().split('T')[0];
    for (let i = 0; i < 7; i++) {
      const d = new Date(currentWeekStart);
      d.setDate(currentWeekStart.getDate() + i);
      const ds = d.toISOString().split('T')[0];
      const dayName = d.toLocaleDateString('en-US', { weekday: 'short' });
      const isToday = ds === todayStr;
      const isSelected = ds === selectedDate;
      days.push({ date: d, dateString: ds, dayName, isToday, isSelected });
    }
    return days;
  }, [currentWeekStart, selectedDate]);

  function getDayTotals(dateString: string): { kcal: number; protein: number } {
    const meals = mealLogger.getMealsForDate(dateString);
    return meals.reduce(
      (acc, m) => ({ kcal: acc.kcal + (m.total_kcal || 0), protein: acc.protein + (m.total_protein_g || 0) }),
      { kcal: 0, protein: 0 }
    );
  }

  function onSearch() {
    if (!searchQuery.trim()) {
      setIsSearching(false);
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    setSearchResults(mealLogger.searchMeals(searchQuery.trim()));
  }

  function clearSearch() {
    setSearchQuery('');
    setIsSearching(false);
    setSearchResults([]);
  }

  function toggle(mealId: string) {
    setExpanded((prev) => {
      const next = new Set(Array.from(prev));
      if (next.has(mealId)) next.delete(mealId); else next.add(mealId);
      return next;
    });
  }

  function previousWeek() { setCurrentWeekStart((w) => { const d = new Date(w); d.setDate(d.getDate() - 7); return startOfWeek(d); }); }
  function nextWeek() { setCurrentWeekStart((w) => { const d = new Date(w); d.setDate(d.getDate() + 7); return startOfWeek(d); }); }
  function goToday() {
    const today = new Date().toISOString().split('T')[0];
    setSelectedDate(today);
    setCurrentWeekStart(startOfWeek(new Date()));
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 24 }}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Meal Log</Text>
        <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={goToday}>
          <Text style={styles.btnTextPrimary}>Today</Text>
        </TouchableOpacity>
      </View>

      {/* Weekly Calendar */}
      <View style={styles.calendar}>
        <View style={styles.calendarHeader}>
          <TouchableOpacity style={styles.navBtn} onPress={previousWeek}>
            <MaterialIcons name="chevron-left" size={20} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.calendarMonth}>
            {currentWeekStart.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
          </Text>
          <TouchableOpacity style={styles.navBtn} onPress={nextWeek}>
            <MaterialIcons name="chevron-right" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
        <View style={styles.calendarGrid}>
          {weekDays.map((d) => {
            const totals = getDayTotals(d.dateString);
            return (
              <TouchableOpacity key={d.dateString} style={[styles.calendarDay, d.isToday && styles.today, d.isSelected && styles.selected]} onPress={() => setSelectedDate(d.dateString)}>
                <Text style={[styles.dayName, d.isSelected && styles.selectedText]}>{d.dayName}</Text>
                <Text style={[styles.dayDate, d.isSelected && styles.selectedText]}>{d.date.getDate()}</Text>
                {totals.kcal > 0 ? (
                  <View>
                    <Text style={[styles.totalKcal, d.isSelected && styles.selectedText]}>{totals.kcal.toFixed(0)} cal</Text>
                    <Text style={[styles.totalProtein, d.isSelected && styles.selectedText]}>{totals.protein.toFixed(0)}p</Text>
                  </View>
                ) : null}
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Search */}
      <View style={styles.searchSection}>
        <View style={styles.searchRow}>
          <TextInput
            placeholder="Search meals by dish or ingredients..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            onSubmitEditing={onSearch}
            style={styles.searchInput}
          />
          <TouchableOpacity style={[styles.btn, styles.btnSearch]} onPress={onSearch}>
            <Text style={styles.btnTextPrimary}>Search</Text>
          </TouchableOpacity>
          {searchQuery ? (
            <TouchableOpacity style={[styles.btn, styles.btnClear]} onPress={clearSearch}>
              <Text style={styles.btnTextPrimary}>Clear</Text>
            </TouchableOpacity>
          ) : null}
        </View>
      </View>

      {isSearching && searchResults.length > 0 ? (
        <View style={styles.searchResults}>
          <Text style={styles.sectionTitle}>Search Results</Text>
          {searchResults.map((meal) => (
            <View key={meal.id} style={[styles.card, styles.searchCard]}>
              <View style={styles.rowBetween}>
                <View>
                  <Text style={styles.mealTitle}>{meal.dish || 'Meal'}</Text>
                  <Text style={styles.mealMeta}>{formatDateNice(meal.date)}</Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <Text style={styles.kcal}>{(meal.total_kcal || 0).toFixed(0)} kcal</Text>
                  <Text style={styles.grams}>{(meal.total_grams || 0).toFixed(0)} g</Text>
                </View>
              </View>
              <View style={{ marginTop: 8, flexDirection: 'row', justifyContent: 'flex-end' }}>
                <TouchableOpacity style={[styles.btn, styles.btnAdd]} onPress={() => mealLogger.duplicateToToday(meal)}>
                  <Text style={styles.btnTextPrimary}>Add to Today</Text>
                </TouchableOpacity>
              </View>
            </View>
          ))}
        </View>
      ) : null}

      {/* Daily Log */}
      <View style={styles.daily}>
        <View style={styles.dailyHeader}>
          <Text style={styles.dailyTitle}>{formatDateNice(log.date)}</Text>
          {log.meals.length > 0 ? (
            <View style={styles.totalsRow}>
              <View style={styles.totalItem}><Text style={styles.totalLabel}>Total kcal</Text><Text style={styles.totalValue}>{log.dailyTotals.total_kcal.toFixed(0)}</Text></View>
              <View style={styles.totalItem}><Text style={styles.totalLabel}>Protein</Text><Text style={styles.totalValue}>{log.dailyTotals.total_protein_g.toFixed(1)} g</Text></View>
              <View style={styles.totalItem}><Text style={styles.totalLabel}>Carbs</Text><Text style={styles.totalValue}>{log.dailyTotals.total_carbs_g.toFixed(1)} g</Text></View>
              <View style={styles.totalItem}><Text style={styles.totalLabel}>Fat</Text><Text style={styles.totalValue}>{log.dailyTotals.total_fat_g.toFixed(1)} g</Text></View>
            </View>
          ) : null}
        </View>
        {log.meals.length > 0 ? (
          <View style={{ padding: 12 }}>
            {log.meals.map((m) => (
              <View key={m.id} style={styles.card}>
                <TouchableOpacity onPress={() => toggle(m.id)} style={styles.rowBetween}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.mealTitle}>{m.dish || 'Meal'}</Text>
                    <View style={styles.quickStats}>
                      <Text style={styles.kcal}>{(m.total_kcal || 0).toFixed(0)} cal</Text>
                      <Text style={styles.protein}>{(m.total_protein_g || 0).toFixed(0)}p</Text>
                      <Text style={styles.time}>{formatTime(m.timestamp)}</Text>
                    </View>
                  </View>
                  <MaterialIcons name={expanded.has(m.id) ? 'expand-more' : 'chevron-right'} size={20} color="#999" />
                </TouchableOpacity>
                {expanded.has(m.id) ? (
                  <View style={{ marginTop: 8 }}>
                    <View style={styles.nutritionGrid}>
                      <View style={styles.nutItem}><Text style={styles.nutLabel}>kcal</Text><Text style={styles.nutValue}>{(m.total_kcal || 0).toFixed(0)}</Text></View>
                      <View style={styles.nutItem}><Text style={styles.nutLabel}>protein</Text><Text style={styles.nutValue}>{(m.total_protein_g || 0).toFixed(1)} g</Text></View>
                      <View style={styles.nutItem}><Text style={styles.nutLabel}>carbs</Text><Text style={styles.nutValue}>{(m.total_carbs_g || 0).toFixed(1)} g</Text></View>
                      <View style={styles.nutItem}><Text style={styles.nutLabel}>fat</Text><Text style={styles.nutValue}>{(m.total_fat_g || 0).toFixed(1)} g</Text></View>
                      <View style={styles.nutItem}><Text style={styles.nutLabel}>total</Text><Text style={styles.nutValue}>{(m.total_grams || 0).toFixed(0)} g</Text></View>
                    </View>
                    {Array.isArray(m.ingredients_detected) && m.ingredients_detected.length > 0 ? (
                      <View style={{ marginTop: 8 }}>
                        <Text style={styles.ingredientsLabel}>Ingredients:</Text>
                        <View style={styles.ingredientsWrap}>
                          {m.ingredients_detected.map((ing, i) => (
                            <Text key={i} style={styles.ingredientChip}>{ing}</Text>
                          ))}
                        </View>
                      </View>
                    ) : null}
                    {m.notes ? (
                      <View style={{ marginTop: 6 }}>
                        <Text style={styles.notesLabel}>Notes:</Text>
                        <Text style={styles.notesText}>{m.notes}</Text>
                      </View>
                    ) : null}
                    <View style={{ marginTop: 8, flexDirection: 'row', justifyContent: 'flex-end' }}>
                      <TouchableOpacity style={[styles.btn, styles.btnRemove]} onPress={() => mealLogger.removeMeal(m.id)}>
                        <Text style={styles.btnTextPrimary}>Remove</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ) : null}
              </View>
            ))}
          </View>
        ) : (
          <View style={{ padding: 20, alignItems: 'center' }}>
            <Text style={{ color: '#666' }}>No meals logged for {formatDateNice(log.date)}</Text>
            <Text style={{ color: '#999' }}>Analyze some food to start logging your meals!</Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, borderBottomWidth: 1, borderBottomColor: '#eee' },
  headerTitle: { fontSize: 22, fontWeight: '600' },
  btn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, borderWidth: StyleSheet.hairlineWidth, borderColor: '#ddd' },
  btnPrimary: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  btnSearch: { backgroundColor: '#28a745', borderColor: '#28a745' },
  btnClear: { backgroundColor: '#6c757d', borderColor: '#6c757d' },
  btnAdd: { backgroundColor: '#28a745', borderColor: '#28a745' },
  btnRemove: { backgroundColor: '#dc3545', borderColor: '#dc3545' },
  btnTextPrimary: { color: '#fff', fontWeight: '600' },
  calendar: { margin: 16, borderWidth: 1, borderColor: '#e9ecef', borderRadius: 8, overflow: 'hidden' },
  calendarHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 12, paddingVertical: 10, backgroundColor: '#f8f9fa', borderBottomWidth: 1, borderBottomColor: '#e9ecef' },
  calendarMonth: { fontSize: 16, fontWeight: '600', color: '#333' },
  navBtn: { backgroundColor: Colors.primary, width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  calendarGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  calendarDay: { width: '14.2857%', minWidth: '14.2857%', paddingVertical: 10, alignItems: 'center', justifyContent: 'center', borderRightWidth: 1, borderTopWidth: 1, borderColor: '#e9ecef' },
  today: { backgroundColor: '#e3f2fd' },
  selected: { backgroundColor: Colors.primary },
  selectedText: { color: '#fff' },
  dayName: { fontSize: 11, color: '#666', textTransform: 'uppercase' },
  dayDate: { fontSize: 16, fontWeight: '600', color: '#333' },
  totalKcal: { fontSize: 10, color: '#e91e63', fontWeight: '600' },
  totalProtein: { fontSize: 10, color: '#4caf50', fontWeight: '600' },
  searchSection: { paddingHorizontal: 16, marginTop: 10 },
  searchRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  searchInput: { flex: 1, borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10 },
  searchResults: { marginTop: 16, paddingHorizontal: 16 },
  sectionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 8 },
  card: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#e9ecef', borderRadius: 8, padding: 12, marginBottom: 10 },
  searchCard: { backgroundColor: '#fff3cd', borderColor: '#ffeaa7' },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  mealTitle: { fontSize: 16, fontWeight: '600', color: '#333' },
  mealMeta: { fontSize: 12, color: '#666' },
  kcal: { color: '#e91e63', fontWeight: '600' },
  grams: { color: '#666' },
  daily: { margin: 16, borderWidth: 1, borderColor: '#e9ecef', borderRadius: 8, overflow: 'hidden' },
  dailyHeader: { backgroundColor: '#f8f9fa', padding: 12, borderBottomWidth: 1, borderBottomColor: '#e9ecef' },
  dailyTitle: { fontSize: 20, fontWeight: '600' },
  totalsRow: { marginTop: 6, flexDirection: 'row', flexWrap: 'wrap', gap: 16 },
  totalItem: { minWidth: 72, alignItems: 'center' },
  totalLabel: { fontSize: 12, color: '#666', textTransform: 'uppercase' },
  totalValue: { fontSize: 18, fontWeight: '600', color: '#333' },
  quickStats: { flexDirection: 'row', gap: 12, marginTop: 4 },
  protein: { color: '#4caf50', fontWeight: '600' },
  time: { color: Colors.primary },
  nutritionGrid: { marginTop: 6, flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  nutItem: { paddingHorizontal: 8, paddingVertical: 6, backgroundColor: '#f8f9fa', borderRadius: 6, borderWidth: 1, borderColor: '#eee' },
  nutLabel: { fontSize: 11, color: '#666', textTransform: 'uppercase' },
  nutValue: { fontSize: 12, fontWeight: '600', color: '#333' },
  ingredientsLabel: { fontSize: 12, color: '#666', textTransform: 'uppercase' },
  ingredientsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 },
  ingredientChip: { backgroundColor: '#e9ecef', color: '#495057', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12, fontSize: 11 },
  notesLabel: { fontSize: 12, color: '#666', textTransform: 'uppercase' },
  notesText: { fontSize: 14, color: '#666', fontStyle: 'italic' },
});


