# React Native / Expo Review Checklist

Apply this reference when the PR touches React Native or Expo code. Detect by:
- `package.json` contains `react-native` or `expo` in dependencies
- Files use `.tsx` / `.jsx` alongside RN-specific imports (`react-native`, `expo-*`, `@react-navigation/*`)

## Performance

- **Re-renders**: Unstable props (inline `{}`, `[]`, `() =>`) passed to memoized components or `FlatList`/`SectionList`. Flag when hot paths create new references on every render without `useMemo`/`useCallback`.
- **Lists**: `FlatList` / `SectionList` must have stable `keyExtractor`. Avoid `index` keys when items can reorder. For long lists, verify `getItemLayout`, `initialNumToRender`, `windowSize`, and `removeClippedSubviews` are considered.
- **Images**: Prefer `expo-image` over `Image` for caching/priority. Flag raw `Image` usage on screens with many thumbnails.
- **Heavy work on JS thread**: Large JSON parsing, sync crypto, or tight loops inside render/effects — recommend `InteractionManager.runAfterInteractions`, worklets, or native modules.
- **Reanimated / Gesture Handler**: Animation logic should live in worklets, not `setState` loops. Shared values should not be read inside render.

## Memory & Lifecycle

- Effects with subscriptions (listeners, timers, animation frames, WebSockets) must clean up in the return function.
- `useEffect` dependency arrays: flag missing deps or intentional omission without a comment explaining why.
- Navigation listeners (`navigation.addListener`) must be removed on unmount.
- Large in-memory caches (images, query results) should have eviction or be tied to screen lifecycle.

## Navigation

- Expo Router / React Navigation: deep links must be validated. Flag untrusted URL params passed directly to routes or `WebView`.
- Screen options should be stable (defined outside render or memoized) to avoid header flicker.
- Back button / Android hardware back behavior handled for modals, multi-step flows.

## Native Modules & Permissions

- Permission requests should be just-in-time, with a rationale, and degrade gracefully when denied.
- Native module calls that can fail (camera, location, biometrics, notifications) must have error handling, not uncaught promise rejections.
- `Info.plist` usage descriptions and `AndroidManifest.xml` permissions should match the feature set.

## Platform Differences

- `Platform.OS` / `Platform.select` used when behavior genuinely differs; avoid duplicated branches that should be unified.
- Safe area: screens that render to the edge must use `SafeAreaView` or `useSafeAreaInsets`.
- Keyboard handling: inputs near the bottom need `KeyboardAvoidingView` or an equivalent; test iOS `padding` vs. Android `height`.

## Expo-Specific

- `expo-constants` / `expo-device` reads should be cached — they're not free.
- `expo-secure-store` for credentials/tokens (never `AsyncStorage`).
- `expo-updates` / OTA: breaking native changes require a new binary; flag JS-only changes that assume native features not in the current runtime.
- Config plugins in `app.config.js` must be deterministic (no side effects, no network).

## Accessibility

- Touchables and custom pressables need `accessibilityRole`, `accessibilityLabel`, and a minimum 44x44 hit target.
- `accessible` grouping for composite components.
- Dynamic type / font scaling not broken by fixed heights.

## Testing

- Unit tests: pure functions and reducers.
- Component tests: `@testing-library/react-native` with user-centric queries, not `getByTestId` when a role/label would work.
- E2E (Detox / Maestro) for critical flows when present — verify new flows don't regress existing suites.

## Anti-Patterns to Flag

- `setState` inside render (outside of the initializer form).
- `useEffect` that fires on every render due to unstable deps.
- Storing derived state — recompute or use `useMemo`.
- Prop drilling > 3 levels — suggest context, zustand, or a query cache.
- `console.log` / `debugger` left in committed code.
- Inline styles in hot paths instead of `StyleSheet.create`.
- `any` escape hatches in TypeScript without justification.
