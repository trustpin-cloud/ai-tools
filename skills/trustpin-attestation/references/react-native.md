# React Native, bare and Expo (@trustpin/react-native-attest)

Source: https://docs.trustpin.cloud/sdk/react-native-attestation. Package: https://www.npmjs.com/package/@trustpin/react-native-attest

## How this platform differs

Like pinning, attestation starts in **native code** before JavaScript runs, from the same config files. React Native's networking is native, so `fetch`, `XMLHttpRequest` and axios carry the `TrustPin-Attestation` header to the attested hosts with nothing to change. Do not wrap `fetch` or add interceptors for the header.

## Requirements

React Native 0.85+ (New Architecture), iOS 15+, Android API 25+, Kotlin 2.3.0+. `@trustpin/react-native` set up at the same version as `@trustpin/react-native-attest` (7.1.0 or later). Expo Go cannot run it: a development build is required. The native device requirements apply (`references/swift.md`, `references/kotlin.md`).

## Install

```bash
npm install @trustpin/react-native @trustpin/react-native-attest
```

Use the package manager the project already uses.

## Expo

List the plugin with the pinning one:

```json
["@trustpin/react-native-attest", {
  "verifierUrl": "https://attest.example.com",
  "attestedHosts": ["api.example.com"],
  "appAttestEnvironment": "development"
}]
```

Then `npx expo prebuild`. The plugin adds the attestation keys to the config files the pinning plugin writes, the App Attest entitlement, and the native start call right after pinning's. Other props: `googleCloudProjectNumber` (Android, Play Integrity only), `logLevel` (`none`, `error`, `warning`, `info`, `debug`). `appAttestEnvironment` defaults to `production`; use `development` for dev-client builds. Prefer `app.config.js` with environment variables in a public repository.

## Bare React Native

1. Add the attestation keys to the config files pinning reads: `AttestVerifierURL` and `AttestedHosts` in `ios/<App>/TrustPin-Info.plist`; `attest_verifier_url`, `attested_hosts` (and `google_cloud_project_number` only for Play Integrity) in `android/app/src/main/assets/trustpin.json`.
2. Start attestation right after pinning:

```swift
// AppDelegate.swift
import TrustPinReactNativeAttest

TrustPinReactNative.start()
TrustPinReactNativeAttest.start()        // or: .start(logLevel: .debug)
```

```kotlin
// MainApplication.kt
import cloud.trustpin.reactnative.attest.TrustPinReactNativeAttest

override fun onCreate() {
  TrustPinReactNative.start(this)
  TrustPinReactNativeAttest.start(this)   // or: .start(this, TrustPinAttestLogLevel.DEBUG, debugToken)
  super.onCreate()
  loadReactNative(this)
}
```

3. The App Attest capability on the iOS app target. Then `cd ios && pod install` and rebuild.

## JavaScript side

```ts
import TrustPinAttest from '@trustpin/react-native-attest';

await TrustPinAttest.bindToHeader('Authorization');
TrustPinAttest.prefetch();   // never rejects

const subscription = TrustPinAttest.onStateChange(state => {
  // current state first, then changes: unavailable | attesting | ready | failed
});
```

Other calls: `getToken()`, `attestationHeaders(url, { method, headers })` (for clients outside React Native's networking; never rejects), `setTokenBinding(value)`, `getState()`, `onEvent(listener)`, `onLogEvent(listener)`, `reset()`, `setLogLevel(level)`.

## Sensitive operations

```ts
const body = JSON.stringify(payload);
const headers: Record<string, string> = { Authorization: `Bearer ${session}`, 'Content-Type': 'application/json' };
Object.assign(headers, await TrustPinAttest.assertionHeaders(sha256Bytes(body)));
await fetch(url, { method: 'POST', headers, body });
```

`assertionHeaders` takes the digest as 32 bytes (`Uint8Array` or `ArrayBuffer`) or 64 hex characters. React Native has no built-in SHA-256: use the crypto library the app already has, and ask before adding one.

## Debug tokens

- iOS simulator: `TRUSTPIN_DEBUG_TOKEN` in the Xcode scheme's environment, or `TrustPinReactNativeAttest.start(debugToken:)` from a debug-only build setting.
- Android: `TrustPinReactNativeAttest.start(this, level, BuildConfig.TRUSTPIN_DEBUG_TOKEN)` from a debug-only build field (`references/kotlin.md`).

Never in a config file, `app.json`, or JavaScript source.

## Errors

Every rejection is a `TrustPinAttestError` with `code`: `INVALID_CONFIGURATION`, `ALREADY_INITIALIZED`, `NOT_SET_UP` (also when the native start call is missing), `UNSUPPORTED_DEVICE`, `EVIDENCE_UNAVAILABLE`, `BINDING_REQUIRED`, `ATTESTATION_FAILED` (with `reasons`), `VERIFIER_UNAVAILABLE`, `VERIFIER_INCOMPATIBLE`, `INVALID_DIGEST`, `INVALID_ARGUMENTS`, `CANCELLED`, `ATTEST_ERROR`. Handle unknown codes.
