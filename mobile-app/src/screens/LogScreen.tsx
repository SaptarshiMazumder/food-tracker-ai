import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ScrollView, Modal, Platform, Image } from 'react-native';
import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import { Colors } from '../theme/colors';
import Card from '../components/Card';
import { mealLogger, LoggedMeal, DailyMealLog } from '../services/mealLogger';
import { MaterialIcons } from '@expo/vector-icons';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Circle, Text as SvgText } from 'react-native-svg';
import { getHealthScore, HealthScoreInput, HealthScoreOutput } from '../services/api';

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
  const [selectedDate, setSelectedDate] = useState<string>(formatYMD(new Date()));
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(() => startOfWeek(new Date()));
  const [log, setLog] = useState<DailyMealLog>(() => mealLogger.getDailyMealLog(selectedDate));
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<LoggedMeal[]>([]);
  const [dateModalVisible, setDateModalVisible] = useState<boolean>(false);
  const [actionMeal, setActionMeal] = useState<LoggedMeal | null>(null);
  const [actionType, setActionType] = useState<'move' | 'copy' | null>(null);
  const [targetDateObj, setTargetDateObj] = useState<Date | null>(null);
  const [detailMeal, setDetailMeal] = useState<LoggedMeal | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState<boolean>(false);
  const [detailHealth, setDetailHealth] = useState<HealthScoreOutput | null>(null);
  const [detailHealthLoading, setDetailHealthLoading] = useState<boolean>(false);

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
    const todayStr = formatYMD(new Date());
    for (let i = 0; i < 7; i++) {
      const d = new Date(currentWeekStart);
      d.setDate(currentWeekStart.getDate() + i);
      const ds = formatYMD(d);
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

  // Removed dropdown/expand behavior

  function previousWeek() { setCurrentWeekStart((w) => { const d = new Date(w); d.setDate(d.getDate() - 7); return startOfWeek(d); }); }
  function nextWeek() { setCurrentWeekStart((w) => { const d = new Date(w); d.setDate(d.getDate() + 7); return startOfWeek(d); }); }
  function goToday() {
    const today = formatYMD(new Date());
    setSelectedDate(today);
    setCurrentWeekStart(startOfWeek(new Date()));
  }

  function formatYMD(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  function openDateModal(meal: LoggedMeal, type?: 'move' | 'copy') {
    setActionMeal(meal);
    setActionType(type || null);
    setTargetDateObj(new Date(meal.date + 'T00:00:00'));
    setDateModalVisible(true);
  }

  function openDetail(meal: LoggedMeal) {
    setDetailMeal(meal);
    setDetailModalVisible(true);
    // If health score was persisted from AnalyzeScreen, use it; else fetch once and store
    if (meal.health_score) {
      setDetailHealth(meal.health_score);
      return;
    }
    if (
      typeof meal.total_kcal === 'number' &&
      typeof meal.total_grams === 'number' &&
      typeof meal.total_fat_g === 'number' &&
      typeof meal.total_protein_g === 'number' &&
      Array.isArray(meal.items_grams) && meal.items_grams.length > 0
    ) {
      const input: HealthScoreInput = {
        total_kcal: meal.total_kcal || 0,
        total_grams: meal.total_grams || 0,
        total_fat_g: meal.total_fat_g || 0,
        total_protein_g: meal.total_protein_g || 0,
        items_grams: meal.items_grams.map((it) => ({ name: it.name, grams: it.grams })),
        kcal_confidence: meal.kcal_confidence || 1.0,
        use_confidence_dampen: false,
      };
      setDetailHealthLoading(true);
      getHealthScore(input)
        .then((hs) => {
          setDetailHealth(hs);
          mealLogger.updateMeal(meal.id, { health_score: hs });
        })
        .catch(() => {})
        .finally(() => setDetailHealthLoading(false));
    }
  }

  function closeDetail() {
    setDetailModalVisible(false);
    setDetailMeal(null);
    setDetailHealth(null);
    setDetailHealthLoading(false);
  }

  function CircularProgress({ size, trackWidth = 4, progressWidth = 7, progress, trackColor = Colors.sliderInactive, progressColor = Colors.primary, trackOpacity = 0.5, progressOpacity = 1, labelColor = Colors.neutralText, labelFontSize = 11, labelDy = 0 }: { size: number; trackWidth?: number; progressWidth?: number; progress: number; trackColor?: string; progressColor?: string; trackOpacity?: number; progressOpacity?: number; labelColor?: string; labelFontSize?: number; labelDy?: number; }) {
    const clamped = Math.max(0, Math.min(1, progress || 0));
    const maxStroke = Math.max(trackWidth, progressWidth);
    const radius = (size - maxStroke) / 2;
    const circumference = 2 * Math.PI * radius;
    const dashOffset = circumference * (1 - clamped);
    const center = size / 2;
    return (
      <Svg width={size} height={size}>
        <Circle cx={center} cy={center} r={radius} stroke={trackColor} strokeOpacity={trackOpacity} strokeWidth={trackWidth} fill="none" />
        <Circle cx={center} cy={center} r={radius} stroke={progressColor} strokeOpacity={progressOpacity} strokeWidth={progressWidth} strokeDasharray={`${circumference} ${circumference}`} strokeDashoffset={dashOffset} strokeLinecap="round" fill="none" transform={`rotate(-90 ${center} ${center})`} />
        <SvgText x={center} y={center} dy={labelDy} fill={labelColor} fontSize={labelFontSize} fontWeight="500" textAnchor="middle" alignmentBaseline="middle">{`${Math.round(clamped * 100)}%`}</SvgText>
      </Svg>
    );
  }

  function getHealthColor(score10: number): string {
    const s = Math.max(0, Math.min(10, score10));
    const red = { r: 239, g: 68, b: 68 };
    const yellow = { r: 245, g: 158, b: 11 };
    const green = { r: 34, g: 197, b: 94 };
    const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * t);
    const toHex = (n: number) => n.toString(16).padStart(2, '0');
    if (s <= 5) {
      const t = s / 5;
      const r = lerp(red.r, yellow.r, t);
      const g = lerp(red.g, yellow.g, t);
      const b = lerp(red.b, yellow.b, t);
      return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    } else {
      const t = (s - 5) / 5;
      const r = lerp(yellow.r, green.r, t);
      const g = lerp(yellow.g, green.g, t);
      const b = lerp(yellow.b, green.b, t);
      return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    }
  }

  function renderHealthStars(score10: number) {
    const roundedToHalf = Math.round((score10 / 2) * 2) / 2;
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
            <MaterialCommunityIcons key={idx} name={name as any} size={18} color={isFull || isHalf ? color : '#c7c7c7'} style={styles.iconAlignUp} />
          );
        })}
      </View>
    );
  }

  function closeDateModal() {
    setDateModalVisible(false);
    setActionMeal(null);
    setActionType(null);
    setTargetDateObj(null);
  }

  function confirmDateAction() {
    if (!actionMeal || !actionType) return;
    const target = targetDateObj ? formatYMD(targetDateObj) : null;
    if (!target) return;
    if (actionType === 'move') mealLogger.moveMealToDate(actionMeal.id, target); else mealLogger.duplicateToDate(actionMeal, target);
    closeDateModal();
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
            const metricTextColor = d.isSelected ? '#ffffff' : d.isToday ? Colors.primary : '#555555';
            const metricIconColor = d.isSelected ? '#ffffff' : Colors.primary;
            const metricWeight = d.isSelected || d.isToday ? '600' : '400';
            return (
              <TouchableOpacity key={d.dateString} style={[styles.calendarDay, d.isToday && styles.today, d.isSelected && styles.selected]} onPress={() => setSelectedDate(d.dateString)}>
                <Text style={[styles.dayName, d.isSelected && styles.selectedText]}>{d.dayName}</Text>
                <Text style={[styles.dayDate, d.isSelected && styles.selectedText]}>{d.date.getDate()}</Text>
                {totals.kcal > 0 ? (
                  <View style={{ alignItems: 'center' }}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                      <Text style={[styles.totalKcal, { color: metricTextColor, fontWeight: metricWeight as any }]}>{totals.kcal.toFixed(0)}</Text>
                      <MaterialCommunityIcons name="fire" size={12} color={metricIconColor} />
                    </View>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                      <Text style={[styles.totalProtein, { color: metricTextColor, fontWeight: metricWeight as any }]}>{totals.protein.toFixed(0)} g</Text>
                      <MaterialCommunityIcons name="dumbbell" size={12} color={metricIconColor} />
                    </View>
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
            <Card key={meal.id} style={styles.searchCard}>
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
            </Card>
          ))}
        </View>
      ) : null}

      {/* Daily Log */}
      <Card style={styles.daily}>
        <View style={styles.dailyHeader}>
          <Text style={styles.dailyTitle}>{formatDateNice(log.date)}</Text>
          {log.meals.length > 0 ? (
            <View style={styles.totalsRow}>
              <View style={styles.totalItem}><Text style={styles.totalLabel}>CALORIES</Text><View style={styles.accentBubble}><Text style={styles.accentBubbleText}>{log.dailyTotals.total_kcal.toFixed(0)}</Text></View></View>
              <View style={styles.totalItem}><Text style={styles.totalLabel}>Protein</Text><View style={styles.accentBubble}><Text style={styles.accentBubbleText}>{log.dailyTotals.total_protein_g.toFixed(1)} g</Text></View></View>
              <View style={styles.totalItem}><Text style={styles.totalLabel}>Carbs</Text><View style={styles.accentBubble}><Text style={styles.accentBubbleText}>{log.dailyTotals.total_carbs_g.toFixed(1)} g</Text></View></View>
              <View style={styles.totalItem}><Text style={styles.totalLabel}>Fat</Text><View style={styles.accentBubble}><Text style={styles.accentBubbleText}>{log.dailyTotals.total_fat_g.toFixed(1)} g</Text></View></View>
            </View>
          ) : null}
        </View>
        {log.meals.length > 0 ? (
          <View style={{ padding: 12 }}>
            {log.meals.map((m, idx) => (
              <View key={m.id} style={styles.itemContainer}>
                <TouchableOpacity onPress={() => openDetail(m)} style={styles.rowBetween}>
                  <View style={{ flex: 1 }}>
                    <View style={styles.rowBetween}>
                      <Text style={styles.mealTitle}>{m.dish || 'Meal'}</Text>
                      <Text style={styles.time}>{formatTime(m.timestamp)}</Text>
                    </View>
                    <View style={styles.rowBetween}>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                        <View style={styles.neutralBubble}>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                            <MaterialCommunityIcons name="fire" size={12} color={Colors.primary} />
                            <Text style={styles.neutralBubbleText}>{(m.total_kcal || 0).toFixed(0)}</Text>
                          </View>
                        </View>
                        <View style={styles.neutralBubble}>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                            <MaterialCommunityIcons name="dumbbell" size={12} color={Colors.primary} />
                            <Text style={styles.neutralBubbleText}>{(m.total_protein_g || 0).toFixed(1)} g</Text>
                          </View>
                        </View>
                      </View>
                    </View>
                  </View>
                  <MaterialIcons name={"chevron-right"} size={20} color="#999" />
                </TouchableOpacity>
                {/* Removed inline dropdown details to rely on detail modal */}
                {idx < log.meals.length - 1 ? <View style={styles.separator} /> : null}
              </View>
            ))}
          </View>
        ) : (
          <View style={{ padding: 20, alignItems: 'center' }}>
            <Text style={{ color: '#666' }}>No meals logged for {formatDateNice(log.date)}</Text>
            <Text style={{ color: '#999' }}>Analyze some food to start logging your meals!</Text>
          </View>
        )}
      </Card>
      {/* Date Modal */}
      <Modal visible={dateModalVisible} transparent animationType="fade" onRequestClose={closeDateModal}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={{ fontSize: 16, fontWeight: '600', marginBottom: 8 }}>
              {actionType ? (actionType === 'move' ? 'Move meal to date' : 'Copy meal to date') : 'Move or copy meal'}
            </Text>
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 10 }}>
              <TouchableOpacity
                style={[styles.choicePill, actionType === 'move' && styles.choicePillSelected]}
                onPress={() => setActionType('move')}
              >
                <Text style={[styles.choicePillText, actionType === 'move' && styles.choicePillTextSelected]}>Move</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.choicePill, actionType === 'copy' && styles.choicePillSelected]}
                onPress={() => setActionType('copy')}
              >
                <Text style={[styles.choicePillText, actionType === 'copy' && styles.choicePillTextSelected]}>Copy</Text>
              </TouchableOpacity>
            </View>
            {Platform.OS === 'ios' ? (
              <View>
                <DateTimePicker
                  value={targetDateObj || new Date()}
                  mode="date"
                  display="spinner"
                  onChange={(event, date) => {
                    if (date) setTargetDateObj(date);
                  }}
                />
                <Text style={{ marginTop: 6, color: '#666' }}>{targetDateObj ? targetDateObj.toLocaleDateString() : ''}</Text>
              </View>
            ) : (
              <View>
                <Text style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>Selected: {targetDateObj ? targetDateObj.toLocaleDateString() : ''}</Text>
                <TouchableOpacity
                  style={[styles.btn, styles.btnLight]}
                  onPress={() => {
                    DateTimePickerAndroid.open({
                      value: targetDateObj || new Date(),
                      mode: 'date',
                      onChange: (event, date) => {
                        if (event.type === 'set' && date) setTargetDateObj(date);
                      },
                    });
                  }}
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <MaterialIcons name="calendar-today" size={16} color={Colors.primary} />
                    <Text style={{ fontWeight: '600' }}>Select date</Text>
                  </View>
                </TouchableOpacity>
              </View>
            )}
            <View style={{ flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
              <TouchableOpacity style={[styles.btn]} onPress={closeDateModal}>
                <Text>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btn, styles.btnPrimary, (!targetDateObj || !actionType) && { opacity: 0.5 }] as any}
                onPress={confirmDateAction}
                disabled={!targetDateObj || !actionType}
              >
                <Text style={styles.btnTextPrimary}>Confirm</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Detail Modal */}
      <Modal visible={detailModalVisible} transparent animationType="slide" onRequestClose={closeDetail}>
        <View style={styles.modalBackdrop}>
          <View style={[styles.modalCard, { width: '92%' }]}>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
              <Text style={{ fontSize: 18, fontWeight: '600' }}>Meal Details</Text>
              <TouchableOpacity style={[styles.btn]} onPress={closeDetail}>
                <MaterialIcons name="close" size={18} color={Colors.neutralText} />
              </TouchableOpacity>
            </View>

            {detailMeal ? (
              <ScrollView style={{ marginTop: 8, maxHeight: 520 }}>
                {/* Image(s) */}
                {detailMeal.image_url ? (
                  <Image source={{ uri: detailMeal.image_url }} style={{ width: '100%', height: 220, borderRadius: 10, backgroundColor: '#f4f4f4' }} />
                ) : null}

                {/* 1. FOOD */}
                <Card style={{ marginTop: 12 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <Text style={styles.sectionTitle}>1. FOOD</Text>
                    <Ionicons name="fast-food-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
                  </View>
                  {detailMeal.dish ? <Text style={styles.mealTitle}>{detailMeal.dish}</Text> : null}
                  {Array.isArray(detailMeal.ingredients_detected) && detailMeal.ingredients_detected.length > 0 ? (
                    <View style={styles.ingredientsWrap}>
                      {detailMeal.ingredients_detected.map((ing, i) => (
                        <Text key={i} style={styles.ingredientChip}>{ing}</Text>
                      ))}
                    </View>
                  ) : null}
                </Card>

                {/* 2. MACROS */}
                <Card>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                      <Text style={styles.sectionTitle}>2. MACROS</Text>
                      <Ionicons name="stats-chart-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
                    </View>
                    {typeof detailMeal.total_grams === 'number' ? (
                      <View style={styles.accentBubble}><Text style={styles.accentBubbleText}>{detailMeal.total_grams} g total</Text></View>
                    ) : null}
                  </View>
                  {Array.isArray(detailMeal.items_nutrition) && detailMeal.items_nutrition.length > 0 ? (
                    (() => {
                      const totalG = typeof detailMeal.total_grams === 'number' && detailMeal.total_grams > 0 ? detailMeal.total_grams : 0;
                      const p = totalG > 0 && typeof detailMeal.total_protein_g === 'number' ? detailMeal.total_protein_g / totalG : 0;
                      const c = totalG > 0 && typeof detailMeal.total_carbs_g === 'number' ? detailMeal.total_carbs_g / totalG : 0;
                      const f = totalG > 0 && typeof detailMeal.total_fat_g === 'number' ? detailMeal.total_fat_g / totalG : 0;
                      return (
                        <View style={styles.grid4}>
                          <View style={styles.tile}>
                            <View style={styles.rowBetween}>
                              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                                <Text style={styles.tileTitle}>Calories</Text>
                                <MaterialCommunityIcons name="fire" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
                              </View>
                            </View>
                            <Text style={styles.tileValue}>{detailMeal.total_kcal}</Text>
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
                              <Text style={styles.tileValue}>{detailMeal.total_protein_g} g</Text>
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
                              <Text style={styles.tileValue}>{detailMeal.total_carbs_g} g</Text>
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
                              <Text style={styles.tileValue}>{detailMeal.total_fat_g} g</Text>
                            </View>
                          </View>
                        </View>
                      );
                    })()
                  ) : null}
                  {/* Health score */}
                  <View style={{ marginTop: 10 }}>
                    <View style={styles.rowBetween}>
                      <Text style={styles.tileTitle}>Health Score</Text>
                      {detailHealth ? (
                        renderHealthStars(detailHealth.health_score)
                      ) : null}
                    </View>
                  </View>
                </Card>

                {/* 3. INGREDIENTS PORTIONS */
                }
                <Card>
                  <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                      <Text style={styles.sectionTitle}>3. INGREDIENTS PORTIONS</Text>
                      <Ionicons name="scale-outline" size={18} color={Colors.neutralText} style={styles.iconAlignUp} />
                    </View>
                  </View>
                  {Array.isArray(detailMeal.items_grams) && detailMeal.items_grams.length > 0 ? (
                    <>
                      {detailMeal.items_grams.map((it, i) => (
                        <View key={i} style={styles.rowBetween}>
                          <Text>{it.name}</Text>
                          <View style={styles.neutralBubble}><Text style={styles.neutralBubbleText}>{it.grams} g</Text></View>
                        </View>
                      ))}
                    </>
                  ) : null}
                </Card>

                {/* Actions at bottom */}
                <View style={{ marginTop: 8, flexDirection: 'row', justifyContent: 'flex-end', gap: 8 }}>
                  <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={() => openDateModal(detailMeal)}>
                    <Text style={styles.btnTextPrimary}>Move/ Copy</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.btn, styles.btnRemove]}
                    onPress={() => {
                      mealLogger.removeMeal(detailMeal.id);
                      closeDetail();
                    }}
                  >
                    <Text style={styles.btnTextPrimary}>Remove</Text>
                  </TouchableOpacity>
                </View>

              </ScrollView>
            ) : null}
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, borderBottomWidth: 1, borderBottomColor: '#eee' },
  headerTitle: { fontSize: 22, fontWeight: '600' },
  btn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, borderWidth: StyleSheet.hairlineWidth, borderColor: '#ddd' },
  btnPrimary: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  btnSearch: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  btnClear: { backgroundColor: '#6c757d', borderColor: '#6c757d' },
  btnAdd: { backgroundColor: '#28a745', borderColor: '#28a745' },
  btnRemove: { backgroundColor: '#dc3545', borderColor: '#dc3545' },
  btnMove: { backgroundColor: '#007bff', borderColor: '#007bff' },
  btnCopy: { backgroundColor: '#17a2b8', borderColor: '#17a2b8' },
  btnLight: { backgroundColor: '#ffffff', borderColor: '#ddd' },
  btnTextPrimary: { color: '#fff', fontWeight: '600' },
  calendar: { margin: 16, borderWidth: 1, borderColor: '#e9ecef', borderRadius: 8, overflow: 'hidden' },
  calendarHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 12, paddingVertical: 10, backgroundColor: '#f8f9fa', borderBottomWidth: 1, borderBottomColor: '#e9ecef' },
  calendarMonth: { fontSize: 16, fontWeight: '600', color: '#333' },
  navBtn: { backgroundColor: Colors.primary, width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  calendarGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  calendarDay: { width: '14.2857%', minWidth: '14.2857%', paddingVertical: 10, alignItems: 'center', justifyContent: 'center', borderRightWidth: 1, borderTopWidth: 1, borderColor: '#e9ecef' },
  today: { backgroundColor: Colors.accentSurface },
  selected: { backgroundColor: Colors.primary },
  selectedText: { color: '#fff' },
  dayName: { fontSize: 11, color: '#666', textTransform: 'uppercase' },
  dayDate: { fontSize: 16, fontWeight: '600', color: '#333' },
  totalKcal: { fontSize: 10, color: '#000', fontWeight: '600' },
  totalProtein: { fontSize: 10, color: '#000', fontWeight: '600' },
  searchSection: { paddingHorizontal: 16, marginTop: 10 },
  searchRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  searchInput: { flex: 1, borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10 },
  searchResults: { marginTop: 16, paddingHorizontal: 16 },
  sectionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 8 },
  iconAlignUp: { transform: [{ translateY: -2 }] },
  grid4: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  tile: { width: '48%', backgroundColor: '#fafafa', borderRadius: 10, padding: 10, borderWidth: 1, borderColor: '#eee' },
  tileTitle: { color: '#666', marginBottom: 4 },
  tileValue: { fontSize: 16, fontWeight: '600' },
  ringRightOverlay: { position: 'absolute', top: 0, bottom: 0, right: 6, width: 64, alignItems: 'center', justifyContent: 'center' },
  ringedContent: { paddingRight: 72 },
  card: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#e9ecef', borderRadius: 8, padding: 12, marginBottom: 10 },
  searchCard: { backgroundColor: '#fff3cd', borderColor: '#ffeaa7' },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  mealTitle: { fontSize: 16, fontWeight: '600', color: '#333' },
  mealMeta: { fontSize: 12, color: '#666' },
  kcal: { color: '#e91e63', fontWeight: '600' },
  grams: { color: '#666' },
  daily: { margin: 16 },
  dailyHeader: { backgroundColor: 'transparent', padding: 12, borderBottomWidth: 1, borderBottomColor: '#e9ecef' },
  dailyTitle: { fontSize: 20, fontWeight: '600' },
  totalsRow: { marginTop: 6, flexDirection: 'row', flexWrap: 'nowrap', justifyContent: 'space-between', gap: 8 },
  totalItem: { alignItems: 'center' },
  totalLabel: { fontSize: 10, color: '#666', textTransform: 'uppercase' },
  totalValue: { fontSize: 16, fontWeight: '600', color: '#333' },
  accentBubble: { backgroundColor: Colors.accentSurface, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 999, marginTop: 2 },
  accentBubbleText: { color: Colors.accentText, fontWeight: '400', fontSize: 12 },
  quickStats: { flexDirection: 'row', gap: 12, marginTop: 4 },
  protein: { color: '#4caf50', fontWeight: '600' },
  time: { color: Colors.primary },
  neutralBubble: { backgroundColor: Colors.neutralSurface, paddingHorizontal: 6, paddingVertical: 3, borderRadius: 999 },
  neutralBubbleText: { color: Colors.neutralText, fontSize: 11 },
  nutritionGrid: { marginTop: 6, flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  nutItem: { paddingHorizontal: 8, paddingVertical: 6, backgroundColor: '#f8f9fa', borderRadius: 6, borderWidth: 1, borderColor: '#eee' },
  nutLabel: { fontSize: 11, color: '#666', textTransform: 'uppercase' },
  nutValue: { fontSize: 12, fontWeight: '600', color: '#333' },
  ingredientsLabel: { fontSize: 12, color: '#666', textTransform: 'uppercase' },
  ingredientsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 },
  ingredientChip: { backgroundColor: '#e9ecef', color: '#495057', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12, fontSize: 11 },
  notesLabel: { fontSize: 12, color: '#666', textTransform: 'uppercase' },
  notesText: { fontSize: 14, color: '#666', fontStyle: 'italic' },
  itemContainer: { paddingVertical: 10 },
  separator: { height: StyleSheet.hairlineWidth, backgroundColor: '#e9ecef', marginVertical: 10 },
  modalBackdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', alignItems: 'center', justifyContent: 'center' },
  modalCard: { width: '86%', backgroundColor: '#fff', borderRadius: 10, padding: 16, borderWidth: 1, borderColor: '#e9ecef' },
  dateInput: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10 },
  choicePill: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: '#ddd', backgroundColor: '#fff' },
  choicePillSelected: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  choicePillText: { color: '#333', fontWeight: '600' },
  choicePillTextSelected: { color: '#fff' },
});


