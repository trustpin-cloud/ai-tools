# Kotlin: Android

Source: https://docs.trustpin.cloud/sdk/kotlin. API reference (the most current source): https://trustpin-cloud.github.io/kotlin.sdk

## Requirements

Android API 25+, Kotlin 2.3.0+, Java 11+. The Maven Central artifact is an Android AAR. For server-side JVM, desktop, or Compose Multiplatform targets, the user must request the JVM JAR from contact@trustpin.cloud. Do not try to use the AAR there.

## Install

```kotlin
dependencies {
    implementation("cloud.trustpin:kotlin-sdk:6.4.0")
    // Optional adapters. Add the one matching the app's client:
    implementation("cloud.trustpin:trustpin-okhttp:6.4.0")  // OkHttp, Retrofit
    implementation("cloud.trustpin:trustpin-ktor:6.4.0")    // Ktor with the OkHttp engine
}
```

Follow the project's existing convention (version catalog, Groovy DSL). Adapters are versioned in lockstep with the SDK and do not pull in the SDK or the HTTP client transitively. Verified with OkHttp 4.12. The documentation states OkHttp 4.x.

## Config file

`app/src/main/assets/trustpin.json`:

```json
{
  "organization_id": "your-org-id",
  "project_id": "your-project-id",
  "public_key": "your-base64-public-key",
  "mode": "strict"
}
```

Optional keys: `mode` (`strict` default, or `permissive`), `configuration_url` (HTTPS), `embedded_configuration_asset` (RASP-protected apps only).

Per build variant: place another file at `src/debug/assets/trustpin.json` or `src/<flavor>/assets/trustpin.json`. Standard source-set merging applies.

## Initialize

In the `Application` class. If the app has none, create one and register it with `android:name` in `AndroidManifest.xml`. Confirm the manifest has `<uses-permission android:name="android.permission.INTERNET" />`.

```kotlin
import cloud.trustpin.kotlin.sdk.TrustPin
import cloud.trustpin.kotlin.sdk.TrustPinConfiguration
import cloud.trustpin.kotlin.sdk.fromAssets   // extension function: this import is required

class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val config = TrustPinConfiguration.fromAssets(this@MyApplication)
                TrustPin.setup(config)
                TrustPin.awaitConfiguration()   // fail-closed gate, has a default timeout
            } catch (e: Exception) {
                // Log it. Do not block launch and do not fall back to an unpinned client.
            }
        }
    }
}
```

Two Android-specific rules:

- Always build the configuration with `fromAssets(context)` (or `TrustPinConfiguration(orgId, projectId, publicKey).withAndroidStorage(context)` for a programmatic one). Using the plain constructor on Android still works, but the API reference says it degrades the security profile of the instance and the SDK logs an info message about it.
- A configuration built this way is single-use. Pass it to exactly one `setup` call. Reusing it for a second instance silently downgrades that instance. For a second named instance, call `fromAssets(context)` again.

Call `awaitConfiguration()` after setup and before constructing any HTTP client that depends on pinning. For synchronous call sites use `TrustPin.awaitConfigurationBlocking()`. `TrustPin.isConfigurationLoaded` (a property, not a function) is a non-throwing status read. If the app builds its client through dependency injection at startup, make sure the client is created after setup, for example lazily.

## Wire the HTTP client

**OkHttp (recommended), with the adapter**

```kotlin
import cloud.trustpin.kotlin.sdk.okhttp.trustPin

val client = OkHttpClient.Builder()
    .trustPin()                      // or .trustPin(TrustPin.instance("payments"))
    .build()
```

Java: `TrustPinOkHttp.trustPin(new OkHttpClient.Builder()).build();`

**OkHttp without the adapter**

```kotlin
val tls = TrustPin.makeTlsPair()
val client = OkHttpClient.Builder()
    .sslSocketFactory(tls.sslSocketFactory, tls.trustManager)
    .build()
```

Take both values from the same `makeTlsPair()` call so the factory and trust manager belong to the same TrustPin instance. `makeSSLSocketFactory()` and `makeTrustManager()` also exist, but calling them separately gives you two objects with no guarantee they are matched. If you meet `TrustPinSSLSocketFactory.create()` from a `cloud.trustpin.kotlin.sdk.ssl` package in older material, it is not part of the public API of the 6.3.0 or 6.4.0 Android artifact and does not compile. Use `makeTlsPair()` or the adapter.

**Retrofit**: pass the pinned `OkHttpClient` to `Retrofit.Builder().client(...)`. Find the existing client and add pinning to it. Do not create a second one.

**Ktor (OkHttp engine only)**

```kotlin
import cloud.trustpin.kotlin.sdk.ktor.trustPin

val ktorClient = HttpClient(OkHttp) {
    engine { trustPin() }
}
```

A Ktor `preconfigured` OkHttpClient bypasses engine configuration. In that case pin the OkHttpClient itself with the OkHttp adapter.

**Custom transports**: `TrustPin.verify("api.example.com", x509Certificate)` (suspending).

**HttpsURLConnection**

```kotlin
HttpsURLConnection.setDefaultSSLSocketFactory(TrustPin.makeSSLSocketFactory())
```

This sets the process-wide default, so it affects every `HttpsURLConnection` in the app, including ones opened by libraries. Include their hosts in the host inventory. Call it after `awaitConfiguration()`.

**Anything else** (Volley with a custom stack, Cronet, WebView): there is no documented path. Tell the user, and do not improvise a trust manager.

## Logging and monitoring

```kotlin
TrustPin.setLogLevel(TrustPinLogLevel.DEBUG)   // before setup; NONE, ERROR, INFO, DEBUG
```

To report suspected interception, install a `TrustPinValidationListener` with `TrustPin.setValidationListener(...)`. It observes outcomes across all TrustPin instances, fires only for definitive verdicts, and cannot change the outcome. `TrustPin.setLogSink(sink)` routes SDK log output to your own logger instead of logcat.

## Errors

`TrustPinError` is a sealed class: `DomainNotRegistered`, `PinsMismatch`, `AllPinsExpired`, `InvalidServerCert`, `InvalidProjectConfig`, `ErrorFetchingPinningInfo`, `ConfigurationValidationFailed`, `ConfigIntegrityError`, `NotInitialized`, `AlreadyInitialized`, `SetupInProgress`, `LockTimeout`, `Timeout`, `SSLContextSetupFailed`, `UnsupportedDevice`.

`NotInitialized` usually means a client was built before setup finished. Guard with `awaitConfiguration()`.

## Release builds

The AAR ships its own R8/ProGuard consumer rules, so no keep rules are needed. If a release build fails with a missing TrustPin class anyway, see `troubleshooting.md` for the keep rules from the documentation.
