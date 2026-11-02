# Kotlin: Android (kotlin-attest)

Source: https://docs.trustpin.cloud/sdk/kotlin-attestation. API reference: https://trustpin-cloud.github.io/kotlin.sdk

## Requirements

Android API 25+, Kotlin 2.3.0+. `kotlin-sdk` set up in the app at the same version as `kotlin-attest` (7.1.0 or later). Key Attestation needs hardware-backed key attestation (emulators offer only software attestation, never accepted). Play Integrity needs Google Play on the device, and only when the policy asks for it.

## Install

```kotlin
dependencies {
    implementation("cloud.trustpin:kotlin-sdk:7.1.0")
    implementation("cloud.trustpin:kotlin-attest:7.1.0")
    // The adapter for the app's client, if not already there:
    implementation("cloud.trustpin:trustpin-okhttp:7.1.0")   // OkHttp, Retrofit
    implementation("cloud.trustpin:trustpin-ktor:7.1.0")     // Ktor with the OkHttp engine
}
```

Follow the project's convention (version catalog, Groovy DSL). The AARs ship their consumer R8 rules; `kotlin-attest` declares no permissions and always brings the Play Integrity library.

## Configure

Add to `app/src/main/assets/trustpin.json`, next to the pinning keys:

```json
"attest_verifier_url": "https://attest.example.com",
"attested_hosts": ["api.example.com"]
```

Add `"google_cloud_project_number": "<number>"` only when the policy uses Play Integrity: with a number, the app contacts Google Play services from setup on (declare it in Play Console's Data safety form). The number is the Cloud project **number**, not its id.

## Set up

In the `Application`, after pinning, in the same coroutine:

```kotlin
import cloud.trustpin.kotlin.attest.TrustPinAttest
import cloud.trustpin.kotlin.attest.TrustPinAttestConfiguration
import cloud.trustpin.kotlin.attest.TrustPinAttestError
import cloud.trustpin.kotlin.attest.fromAssets   // extension function: this import is required

appScope.launch {
    try {
        TrustPin.setup(TrustPinConfiguration.fromAssets(this@MyApp))
        TrustPinAttest.setup(this@MyApp, TrustPinAttestConfiguration.fromAssets(this@MyApp))
        TrustPinAttest.bindToHeader("Authorization")
        TrustPinAttest.prefetch()
    } catch (e: TrustPinAttestError) {
        // Log it. Do not block launch; requests go out without the header.
    }
}
```

`setup` makes no verifier call. A second `setup` throws `AlreadyInitialized`. Set attestation up in the process that does the networking. Named instances: `TrustPinAttest.instance("id")` pairs with `TrustPin.instance("id")`. Java: `setupBlocking` and the other `...Blocking` forms, off the main thread.

## Send the header

| App uses | The header |
|---|---|
| OkHttp or Retrofit pinned with `.trustPin()` | Added automatically, including the right header on each redirect. Build the client after `TrustPin.setup` |
| Ktor with `engine { trustPin() }` | Added automatically |
| OkHttp pinned with `makeTlsPair()` by hand | Switch to the adapter's `.trustPin()`, which also installs the attestation interceptor |
| Any other client | `TrustPinAttest.attestationHeaders(url, requestHeaders)`, add them yourself, and turn automatic redirects off (or rebuild each hop's headers with `TrustPin.redirectedRequestHeaders`) |
| gRPC, WebSockets | `TrustPinAttest.getToken()`, sent in `TrustPinAttest.HEADER_NAME` |

## Sensitive operations

```kotlin
val digest = MessageDigest.getInstance("SHA-256").digest(bodyBytes)
val headers = TrustPinAttest.assertionHeaders(digest)   // assertionHeadersBlocking for Java
```

Add both headers to that request. With header binding, call `attestationHeaders(url, headers)` for this request first, then `assertionHeaders`.

## Emulators and debug tokens

The debug token comes from a debug-only build field, never from `trustpin.json` or the repository:

```kotlin
// build.gradle.kts
android {
    buildFeatures { buildConfig = true }
    buildTypes {
        debug {
            buildConfigField("String", "TRUSTPIN_DEBUG_TOKEN",
                "\"${providers.gradleProperty("trustpinDebugToken").getOrElse("")}\"")
        }
        release { buildConfigField("String", "TRUSTPIN_DEBUG_TOKEN", "\"\"") }
    }
}
```

```kotlin
val fromAssets = TrustPinAttestConfiguration.fromAssets(context)
val config = TrustPinAttestConfiguration(
    verifierUrl = fromAssets.verifierUrl,
    attestedHosts = fromAssets.attestedHosts,
    googleCloudProjectNumber = fromAssets.googleCloudProjectNumber,
    debugToken = BuildConfig.TRUSTPIN_DEBUG_TOKEN.ifEmpty { null },
)
```

The user keeps the token in `~/.gradle/gradle.properties` (`trustpinDebugToken=...`). It is used only in debuggable builds, on emulators and on real devices.

## Errors and state

`TrustPinAttestError` (sealed): `InvalidConfiguration`, `AlreadyInitialized`, `NotSetUp`, `UnsupportedDevice`, `EvidenceUnavailable`, `BindingRequired`, `AttestationFailed(reasons)`, `VerifierUnavailable`, `VerifierIncompatible`, `InvalidDigest`. Give `when` over it an `else` branch.

`TrustPinAttest.state`: `Unavailable`, `Attesting`, `Ready(expiresAtMillis)`, `Failed(error, retryAtMillis)` (`Long.MAX_VALUE`: no new attempt in this process). `setStateListener` does not replay. Logging: `TrustPinAttest.setLogLevel(TrustPinAttestLogLevel.DEBUG)` in development (logcat tag `TrustPinAttest`). Events: `TrustPinAttest.setEventListener { ... }`.
