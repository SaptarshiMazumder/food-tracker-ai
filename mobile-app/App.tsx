import { NavigationContainer, DefaultTheme, Theme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Text } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';

import HomeScreen from './src/screens/HomeScreen';
import AnalyzeScreen from './src/screens/AnalyzeScreen';
import MealsScreen from './src/screens/MealsScreen';
import RagScreen from './src/screens/RagScreen';
import { Colors } from './src/theme/colors';

const Tab = createBottomTabNavigator();

const appTheme: Theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: Colors.background,
    primary: Colors.primary,
    text: Colors.text,
    card: Colors.card,
    border: Colors.border,
  },
};

export default function App() {
  return (
    <NavigationContainer theme={appTheme}>
      <StatusBar style="dark" />
      <Tab.Navigator screenOptions={{ headerShown: true, tabBarActiveTintColor: appTheme.colors.primary, tabBarInactiveTintColor: '#999999' }}>
        <Tab.Screen
          name="Home"
          component={HomeScreen}
          options={{
            tabBarIcon: ({ color, size }) => (
              <MaterialIcons name="home" size={size} color={color} />
            ),
          }}
        />
        <Tab.Screen
          name="Analyze"
          component={AnalyzeScreen}
          options={{
            tabBarIcon: ({ color, size }) => (
              <MaterialIcons name="analytics" size={size} color={color} />
            ),
          }}
        />
        <Tab.Screen
          name="Meals"
          component={MealsScreen}
          options={{
            tabBarIcon: ({ color, size }) => (
              <MaterialIcons name="restaurant" size={size} color={color} />
            ),
          }}
        />
        <Tab.Screen
          name="RAG"
          component={RagScreen}
          options={{
            tabBarIcon: ({ color, size }) => (
              <MaterialIcons name="search" size={size} color={color} />
            ),
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
