# Troubleshooting

Source: https://docs.trustpin.cloud/troubleshooting, plus what the SDK artifacts show. Error names are written in the upper-case code form used by Flutter and React Native. Swift uses camelCase cases of `TrustPinErrors` and Kotlin uses PascalCase subclasses of `TrustPinError`.

Start every diagnosis the same way: set the log level to debug before setup, reproduce, and read the SDK log. Then find the error below.

## Setup and configuration

**`INVALID_PROJECT_CONFIG`** at setup.
- The config file is not in the app bundle. On Apple platforms check Target Membership / Copy Bundle Resources for `TrustPin-Info.plist`. On Android check the file is at `app/src/main/assets/trustpin.json`.
- A value is missing, wrong, or contains whitespace or a line break. Compare each against the dashboard.
- Wrong environment: the debug build is reading the production file or the reverse.
- React Native: the native init call (`TrustPinReactNative.start`) was never wired.
- An embedded configuration is declared but missing, modified, or signed for a different project.

**`ERROR_FETCHING_PINNING_INFO`**: the configuration could not be downloaded.
- No connectivity, or a firewall or proxy blocks HTTPS to `cdn.trustpin.cloud`.
- No configuration has been published yet. Confirm with `trustpin-cli projects jws <org> <project>` or in the dashboard under Publish config.
- Service status: https://status.trustpin.cloud
- Sandboxed macOS app without the `com.apple.security.network.client` entitlement.

**`CONFIGURATION_VALIDATION_FAILED`**: downloaded, but the signature did not verify.
- The Public Key in the config file is not this project's key. Copy it again from the dashboard.
- Something between the device and the CDN is altering the response.

**`ALREADY_INITIALIZED`**: setup ran twice on the same instance. Common causes are Flutter hot restart, a test harness, or setup called from both the app entry point and a dependency-injection module. Keep one call site.

**`NOT_INITIALIZED` (Kotlin)**: an HTTP client was built or used before setup finished. Await `awaitConfiguration()` before constructing the pinned client, or construct it lazily.

**Timeout from `awaitConfiguration()`**: same causes as a fetch failure. The gate is doing its job. Do not respond by removing it.

## Certificate validation

**`DOMAIN_NOT_REGISTERED`**: strict mode, and the host is not in the published configuration.
- Add the domain in the project and publish. Staged changes that were never published are the usual cause.
- The name must match exactly: `api.example.com` and `www.api.example.com` are different hosts.
- If the host belongs to a third-party library caught by system-wide pinning, either register it or narrow pinning to the app's own client.
- For local development against hosts that will never be registered, use `permissive` in a debug-only config. Never in a release build.

**`PINS_MISMATCH`**: the server certificate matches no active pin.
- The certificate was rotated and the new pin was not published first. Run `trustpin-cli domains certificates <host>` to see the live certificate's pins, compare with `trustpin-cli projects config`, then stage and publish.
- A pin was entered as a certificate fingerprint when the SPKI was intended, or the reverse.
- A corporate proxy or security appliance is intercepting TLS. This is pinning working as designed. The fix is to exclude the app's hosts from inspection, not to weaken pinning.
- It can be a real interception attempt. Do not dismiss it without checking the certificate that was presented (the validation listener receives it).

**`ALL_PINS_EXPIRED`**: every pin for the host has passed its expiry. Refresh the pins and publish. Prevent it with a scheduled `refresh-certs` job (see `cli.md`).

**`INVALID_SERVER_CERT`**: the server sent a certificate the SDK could not parse.

**A fix was published but the app still fails**: publishing propagates in a couple of minutes, and the SDK caches the configuration for 10 minutes. Wait, or restart the app.

## iOS and macOS

- **System-wide pinning has no effect**: confirm `autoRegisterURLProtocol: true` was passed to setup or `TrustPin.registerURLProtocol()` was called, and that nothing unregisters it. Plain `http://` URLs are never pin-validated.
- **Requests hang**: confirm the session was created with the TrustPin delegate and that the session is retained and reused.
- **CocoaPods errors**: `pod deintegrate`, then `pod install`.
- **Setup appears to do nothing**: the `Task` that calls setup is swallowing the error. Log the catch block.

## Android

- **Works in debug, fails in release with a missing class**: the AAR ships its own R8/ProGuard consumer rules, so this should not happen. If it does, the documentation gives these keep rules for `proguard-rules.pro`:

  ```
  -keep class cloud.trustpin.** { *; }
  -keepclassmembers class cloud.trustpin.** { *; }
  ```

- **TrustPin never initializes**: the `Application` subclass is not registered with `android:name` in `AndroidManifest.xml`.
- **A Network Security Config also declares pins**: two pinning mechanisms will disagree at rotation. Keep the trust anchors and cleartext settings, and remove the `<pin-set>` for hosts TrustPin manages. Ask the user before removing it.
- **`TrustPinSSLSocketFactory` does not resolve**: that class is not public in the Android artifact. Use `TrustPin.makeTlsPair()` or the `trustpin-okhttp` adapter (see `kotlin.md`).
- **`fromAssets` does not resolve**: add `import cloud.trustpin.kotlin.sdk.fromAssets`.
- **`UNSUPPORTED_DEVICE`**: the runtime lacks required security primitives. On React Native Expo, see the `android.allowNonOemImages` plugin prop.

## Flutter

- **Config changes are not picked up**: native config files are read by native code. Do a full rebuild, not a hot reload.
- **Setup fails on iOS or macOS only**: the plist is not a member of the Runner target.
- **Compilation errors**: the platform minimums are iOS 15 (`platform :ios, '15.0'` in `ios/Podfile`) and Android `minSdk 25`.
- **Binding error at startup**: `WidgetsFlutterBinding.ensureInitialized()` must run before setup.

## React Native

- **`INVALID_PROJECT_CONFIG` from JavaScript**: the native init helper is missing, or (Expo) `expo prebuild` was not re-run after adding the plugin.
- **Nothing is pinned in Expo Go**: expected. Use a development build.
- **Android build fails on Kotlin metadata**: align the Kotlin Gradle plugin to 2.3.0.

## When to send the user to support

After the steps above, collect: platform, SDK version, error code and full message, debug logs, steps to reproduce, and the network environment. Contact: support@trustpin.cloud
