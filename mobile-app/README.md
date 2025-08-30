## Mobile App (React Native + Expo)

Cross-platform UI for Food Tracker, built with Expo (React Native). This does not modify existing backend or Angular frontend.

### Prerequisites

- Node.js 18+
- Android Studio with Android SDK and an AVD emulator (Pixel recommended)
- Expo CLI (via `npx expo`)

### Install

```
cd mobile-app
npm install
```

### Run on Android Emulator (Windows)

1. Open Android Studio > Device Manager > start an emulator.
2. In another terminal:

```
npm run android
```

If your backend runs on localhost:5000, Android emulator reaches host via `10.0.2.2`. Configure API base:

```
setx EXPO_PUBLIC_API_BASE_URL "http://10.0.2.2:5000"
```

Restart the dev server after setting env vars.

### Scripts

- `npm start` – start Expo dev server
- `npm run android` – open on Android emulator
- `npm run web` – run web preview

### Structure

- `App.tsx` – bottom tab navigation (Home, Analyze, Meals, RAG)
- `src/screens/*` – screens
- `src/services/api.ts` – simple API client using `EXPO_PUBLIC_API_BASE_URL`
