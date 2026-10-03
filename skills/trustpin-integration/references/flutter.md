# Flutter

Source: https://docs.trustpin.cloud/sdk/dart. API reference: https://trustpin-cloud.github.io/flutter.sdk

## Requirements

iOS 15+, Android API 25+, macOS 13+. iOS/macOS: Swift 6.1+, Xcode 16.3+. Android: Kotlin 2.3.0+, Java 11+. The package bundles the native SDKs, so there is nothing else to install.

## Install

```yaml
dependencies:
  trustpin_sdk: ^6.4.0
```

Then `flutter pub get`. Confirm `minSdk 25` or higher in `android/app/build.gradle`.

## Config files

The recommended setup reads a native config file on each platform, so the project values never enter Dart code. Create one per platform the app targets. These are native files, not Flutter assets: do not list them under `assets:` in `pubspec.yaml`.

**iOS**: `ios/Runner/TrustPin-Info.plist`. **macOS**: `macos/Runner/TrustPin-Info.plist`.

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

Creating the file on disk is not enough. The user must open the project in Xcode and confirm Target Membership is checked for the Runner target, otherwise the plist is not copied into the bundle and setup fails. Tell them this explicitly.

Sandboxed macOS apps also need the network client entitlement in both `macos/Runner/DebugProfile.entitlements` and `macos/Runner/Release.entitlements`:

```xml
<key>com.apple.security.network.client</key>
<true/>
```

**Android**: `android/app/src/main/assets/trustpin.json`. Gradle bundles it automatically.

```json
{
  "organization_id": "your-org-id",
  "project_id": "your-project-id",
  "public_key": "your-base64-public-key",
  "mode": "strict"
}
```

## Initialize

```dart
import 'package:flutter/material.dart';
import 'package:trustpin_sdk/trustpin_sdk.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await TrustPin.shared.setupWithNativeBundle();
    await TrustPin.shared.awaitConfiguration();   // fail-closed gate
  } on TrustPinException catch (e) {
    // Log e.code and e.message. Do not fall back to an unpinned client.
  }
  runApp(const MyApp());
}
```

Setup is one-shot: a second call on the same instance throws `ALREADY_INITIALIZED`. Watch for this with hot restart during development and in tests.

Per-flavor files:

```dart
await TrustPin.shared.setupWithNativeBundle(
  iosFileName: 'TrustPin-Staging.plist',
  macosFileName: 'TrustPin-Staging.plist',
  androidFileName: 'trustpin-staging.json',
);
```

## Wire the HTTP client

**Dio (recommended)**: add the interceptor to the existing `Dio` instance.

```dart
dio.interceptors.add(TrustPinDioInterceptor());
```

Pinning failures arrive as a `DioException` whose `error` is a `TrustPinException`.

**package:http**: replace the client with a pinned one and reuse it.

```dart
final client = TrustPinHttpClient.create();
```

**Other transports or a pre-flight check**:

```dart
await TrustPin.shared.validateConnection('api.example.com',
    timeout: const Duration(seconds: 5));
```

`fetchCertificate()` and `verify()` are deprecated. Use `validateConnection()`.

## Logging and monitoring

```dart
await TrustPin.shared.setLogLevel(TrustPinLogLevel.debug);   // before setup
```

`TrustPin.logs` streams SDK log events. `TrustPin.validationEvents` streams definitive verdicts (`PINS_MISMATCH`, `ALL_PINS_EXPIRED`, `DOMAIN_NOT_REGISTERED`) for reporting suspected interception. Both are observe-only.

## Errors

All errors are `TrustPinException` with `code` and `message`, plus getters: `isDomainNotRegistered`, `isPinsMismatch`, `isAllPinsExpired`, `isInvalidServerCert`, `isInvalidProjectConfig`, `isAlreadyInitialized`, `isErrorFetchingPinningInfo`, `isConfigurationValidationFailed`, `isConfigIntegrityFailed`, `isFetchCertificateTimeout`. Android only: `isSetupInProgress`, `isLockTimeout`, `isSslContextSetupFailed`, `isUnsupportedDevice`.

## Multiple projects

```dart
final pin = TrustPin.instance('payments');
await pin.setupWithNativeBundle(iosFileName: 'TrustPin-Payments.plist',
    androidFileName: 'trustpin-payments.json');
dio.interceptors.add(TrustPinDioInterceptor(instance: pin));
```
