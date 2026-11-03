# Flutter (trustpin_attest)

Source: https://docs.trustpin.cloud/sdk/flutter-attestation. Package: https://pub.dev/packages/trustpin_attest

## Requirements

Flutter 3.44.0+ (iOS and macOS through Swift Package Manager only). iOS 15+, macOS 13+, Android API 25+, Kotlin 2.3.0+. `trustpin_sdk` set up in the app at the same version as `trustpin_attest` (7.1.1 or later). The App Attest capability on the Runner targets for iOS and macOS. The package wraps the native modules, so their device requirements apply (`references/swift.md`, `references/kotlin.md`).

## Install

```yaml
dependencies:
  trustpin_sdk: ^7.1.1
  trustpin_attest: ^7.1.1
```

## Configure

The native config files pinning already reads get the attestation keys: `AttestVerifierURL` and `AttestedHosts` in `ios/Runner/TrustPin-Info.plist` and `macos/Runner/TrustPin-Info.plist`; `attest_verifier_url`, `attested_hosts` (and `google_cloud_project_number` only for Play Integrity) in `android/app/src/main/assets/trustpin.json`. Same formats as `references/swift.md` and `references/kotlin.md`.

## Set up

In `main()`, after pinning:

```dart
import 'package:trustpin_attest/trustpin_attest.dart';
import 'package:trustpin_sdk/trustpin_sdk.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await TrustPin.shared.setupWithNativeBundle();
    await TrustPin.shared.awaitConfiguration();
    await TrustPinAttest.shared.setupWithNativeBundle();
    await TrustPinAttest.shared.bindToHeader('Authorization');
    await TrustPinAttest.shared.prefetch();
  } on TrustPinException catch (e) {
    // Pinning setup failed. Log it; do not fall back to an unpinned client.
  } on TrustPinAttestException catch (e) {
    // Attestation setup failed. Log it; requests go out without the header.
  }
  runApp(const MyApp());
}
```

`prefetch()` never throws. A second setup throws `ALREADY_INITIALIZED` (watch for hot restart). Named instances: `TrustPinAttest.instance('id')` pairs with `TrustPin.instance('id')`.

## Send the header

| App uses | The header |
|---|---|
| Dio with `TrustPinDioInterceptor` | Added automatically. Construct it as `TrustPinDioInterceptor(dio: dio)` so it follows redirects of attested requests itself; without `dio`, an attested request's redirect reaches the app |
| `package:http` with `TrustPinHttpClient` | Added automatically, redirects followed with the right header per hop |
| Another client | `await TrustPin.shared.attestationHeaders(uri, headers: {...})`, and `redirectedRequestHeaders(...)` for each redirect hop the client follows |
| gRPC, WebSockets | `await TrustPinAttest.shared.getToken()`, sent in `TrustPinAttest.headerName` |

## Sensitive operations

```dart
import 'package:crypto/crypto.dart';

final body = utf8.encode(jsonEncode(payload));
final headers = {'Authorization': 'Bearer $session'};
// With header binding, ask for this request's token first, then the assertion.
headers.addAll(await TrustPinAttest.shared
    .attestationHeaders(url, method: 'POST', headers: headers));
headers.addAll(await TrustPinAttest.shared
    .assertionHeaders(Uint8List.fromList(sha256.convert(body).bytes)));
await client.post(url, headers: headers, body: body);
```

Add `crypto` to `pubspec.yaml` if the app has no SHA-256 already.

## Simulators, emulators and debug tokens

```dart
const debugToken = String.fromEnvironment('TRUSTPIN_DEBUG_TOKEN');
await TrustPinAttest.shared.setupWithNativeBundle(
  debugToken: debugToken.isEmpty ? null : debugToken,
);
```

Run with `flutter run --dart-define=TRUSTPIN_DEBUG_TOKEN=<token>`. Used on the iOS simulator and in debuggable Android builds, never sent in release builds. Never commit the token (not in `launch.json` or a committed `--dart-define-from-file`).

## Errors and state

`TrustPinAttestException` with `code`: `INVALID_CONFIGURATION`, `ALREADY_INITIALIZED`, `NOT_SET_UP`, `UNSUPPORTED_DEVICE`, `EVIDENCE_UNAVAILABLE`, `BINDING_REQUIRED`, `ATTESTATION_FAILED` (with `reasons`), `VERIFIER_UNAVAILABLE`, `VERIFIER_INCOMPATIBLE`, `INVALID_DIGEST`, plus `INVALID_ARGUMENTS`, `CANCELLED`, `ATTEST_ERROR`. Handle unknown codes.

`stateChanges` emits the current state first, then changes: `TrustPinAttestUnavailable`, `TrustPinAttestAttesting`, `TrustPinAttestReady(expiresAt)`, `TrustPinAttestFailed(error, retryAt)` (`retryAt == null`: no new attempt in this launch). `events` streams `TrustPinAttestEvent`s (sealed; keep a default case). Logging: `setLogLevel(TrustPinAttestLogLevel.debug)` and `TrustPinAttest.logs`.
