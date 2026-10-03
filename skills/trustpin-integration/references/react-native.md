# React Native (bare and Expo)

Source: https://docs.trustpin.cloud/sdk/react-native. API reference: https://trustpin-cloud.github.io/react-native.sdk

## How this platform differs

Pinning is configured and activated in native code before any JavaScript runs. Ordinary `fetch` calls are then pinned inside the TLS handshake with no extra code, and the JavaScript API is observe-only: it cannot disable or reconfigure pinning. Two consequences:

- There is no HTTP client to wire. Do not wrap `fetch` or axios.
- In strict mode every host the app reaches is checked, including hosts used by third-party libraries. The host inventory matters most here.

## Requirements

React Native 0.85+ with the New Architecture, Node 22.11+, iOS 15+, Android API 25+ (React Native's default minSdk is 24), Kotlin 2.3.0+. No macOS. Expo Go cannot run pinning, since it is native code: a development build is required.

If the project is below React Native 0.85 or on the old architecture, stop and tell the user. Do not attempt an upgrade as a side effect.

## Install

```bash
npm install @trustpin/react-native
# or
yarn add @trustpin/react-native
```

Use the package manager the project already uses.

## Expo

Add the config plugin to `app.json` or `app.config.js`:

```json
{
  "expo": {
    "plugins": [
      ["@trustpin/react-native", {
        "organizationId": "your-org-id",
        "projectId": "your-project-id",
        "publicKey": "your-base64-public-key",
        "mode": "strict"
      }]
    ]
  }
}
```

Then:

```bash
npx expo prebuild
npx expo run:ios      # or: npx expo run:android
```

The plugin writes the native config files, wires the native init call, and applies Kotlin 2.3.0 and minSdk 25. Prefer `app.config.js` reading environment variables if the repository is public.

Other props: `configurationUrl`, `logLevel` (`none`, `error`, `info`, `debug`), `ios.configFile` and `android.configFile` (use existing files instead of generating them), `embeddedConfigurationFile` (RASP-protected apps only), `android.allowNonOemImages`. Inline credentials together with a `configFile` for the same platform are rejected, as are partial credentials.

## Bare React Native

**1. Config files**

iOS: `ios/<YourApp>/TrustPin-Info.plist`, added to the app target's Copy Bundle Resources phase in Xcode. The user must confirm this in Xcode.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>OrganizationId</key>
  <string>your-org-id</string>
  <key>ProjectId</key>
  <string>your-project-id</string>
  <key>PublicKey</key>
  <string>your-base64-public-key</string>
  <key>Mode</key>
  <string>strict</string>
</dict>
</plist>
```

Android: `android/app/src/main/assets/trustpin.json`.

```json
{
  "organization_id": "your-org-id",
  "project_id": "your-project-id",
  "public_key": "your-base64-public-key",
  "mode": "strict"
}
```

**2. Native init call**

iOS, `AppDelegate.swift`, first line of `didFinishLaunchingWithOptions`:

```swift
import TrustPinReactNative

TrustPinReactNative.start()          // or: .start(logLevel: .debug)
```

Android, `MainApplication.kt`, before `super.onCreate()`:

```kotlin
import cloud.trustpin.reactnative.TrustPinReactNative

override fun onCreate() {
  TrustPinReactNative.start(this)    // or: .start(this, TrustPinLogLevel.DEBUG)
  super.onCreate()
  loadReactNative(this)
}
```

If this call is missing, the JavaScript API reports `INVALID_PROJECT_CONFIG`.

**3. Android toolchain**, in `android/build.gradle`:

```groovy
buildscript {
    ext {
        kotlinVersion = "2.3.0"
        minSdkVersion = 25
    }
    dependencies {
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.3.0")
    }
}
```

Ask before changing these if the project pins different values. Then `cd ios && pod install` and rebuild.

## JavaScript side

```ts
import TrustPin, { TrustPinErrorCodes } from '@trustpin/react-native';

// Fail-closed readiness gate before the first request.
try {
  await TrustPin.awaitConfiguration(10_000);   // native side clamps to 10-120 s
} catch (error) {
  // Hard stop. Do not fall through to an unpinned client.
}

// Definitive verdicts, for reporting suspected interception.
const subscription = TrustPin.onValidationEvent(event => {
  if (event.code) {
    // event.domain, event.code, event.timestampMs
  }
});
```

Other methods: `isConfigurationLoaded()`, `validateConnection(host, port?, timeoutMs?)`, `setLogLevel(level)`, `onLogEvent(listener)`. Events raised before JavaScript is alive are replayed to the first subscriber.

## Errors

Every rejection carries a stable `code`: `PINS_MISMATCH`, `ALL_PINS_EXPIRED`, `DOMAIN_NOT_REGISTERED`, `INVALID_SERVER_CERT`, `FETCH_CERTIFICATE_TIMEOUT`, `INVALID_PROJECT_CONFIG`, `INVALID_ARGUMENTS`. Android also: `UNSUPPORTED_DEVICE`, `SETUP_IN_PROGRESS`, `LOCK_TIMEOUT`, `SSL_CONTEXT_SETUP_FAILED`.
