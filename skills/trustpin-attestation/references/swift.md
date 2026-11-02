# Swift: iOS and macOS (TrustPinAttestKit)

Source: https://docs.trustpin.cloud/sdk/swift-attestation. API reference: https://trustpin-cloud.github.io/swift.sdk

## Requirements

iOS 15+, macOS 13+, Mac Catalyst 15+, tvOS 15+, watchOS 9+, visionOS 2+. `TrustPinKit` set up in the app at the same version (7.1.0 or later). The **App Attest** capability on the App ID and in the app target (entitlement `com.apple.developer.devicecheck.appattest-environment`: `development` for Xcode builds, `production` for TestFlight and the App Store). Some Macs and older hardware report App Attest unsupported.

Use TrustPinAttestKit from the app process only. App extensions are not supported (Apple supports App Attest in Action, extensible SSO and watchOS extensions only), and extensions sharing the app's Keychain are not supported.

## Install

Swift Package Manager: add the `TrustPinAttestKit` product from the same `swift.sdk` package as `TrustPinKit`.

```swift
.package(url: "https://github.com/trustpin-cloud/swift.sdk", from: "7.1.0"),
// target dependencies:
.product(name: "TrustPinKit", package: "swift.sdk"),
.product(name: "TrustPinAttestKit", package: "swift.sdk"),
```

CocoaPods: `pod 'TrustPinKit', '~> 7.1'` and `pod 'TrustPinAttestKit', '~> 7.1'`.

For an Xcode project without a `Package.swift`, ask the user to add the product through File, Add Package Dependencies (or the target's Frameworks section), and to add the App Attest capability under Signing & Capabilities. Do not edit `project.pbxproj` for either.

## Configure

Add two keys to the `TrustPin-Info.plist` that already holds the pinning configuration:

```xml
<key>AttestVerifierURL</key>
<string>https://attest.example.com</string>
<key>AttestedHosts</key>
<array>
  <string>api.example.com</string>
</array>
```

`AttestVerifierURL`: HTTPS base URL of the verifier, no version segment, no credentials, query, fragment or IP address (a deployment path is allowed). `AttestedHosts`: one to fifty hosts; `*.example.com` covers exactly one label. In code: `try TrustPinAttestConfiguration(verifierURL:attestedHosts:)`.

## Set up

After pinning, once per launch, where pinning is set up:

```swift
import TrustPinKit
import TrustPinAttestKit

Task {
    do {
        try await TrustPin.setup(.fromPlist())
        try await TrustPinAttest.setup(.fromPlist())
        TrustPinAttest.bindToHeader("Authorization")
        TrustPinAttest.prefetch()
    } catch {
        // Log it. Do not block launch; requests go out without the header.
    }
}
```

`setup` makes no network call. A second `setup` throws `alreadyInitialized`. `prefetch()` never throws. Named instances: `TrustPinAttest.instance(id:)` pairs with `TrustPin.instance(id:)` of the same id, set up first.

## Send the header

Pick the row matching what the app already does for pinning.

| App uses | The header |
|---|---|
| `TrustPinURLProtocol` (`setup(_:autoRegisterURLProtocol: true)`) | Added automatically, default instance only |
| Its own `URLSession` with `TrustPin.makeURLSessionDelegate()` | A delegate cannot change headers: `request = await TrustPinAttest.addingAttestation(to: request)` before each request |
| Alamofire with `TrustPinKitAlamofire` | Add `TrustPinAttestationAdapter()` to the session's interceptor and pass `TrustPinAttestationRedirectHandler()` as its `redirectHandler` |
| gRPC, WebSockets | `let token = try await TrustPinAttest.getToken()`, sent in `TrustPinAttest.headerName` |

Redirects: TrustPin's URL protocol, session delegates and the Alamofire redirect handler re-request the header for each redirect. A session that handles redirects itself without TrustPin's delegate calls `await TrustPin.redirectedRequest(newRequest)` in its redirect callback.

With `addingAttestation(to:)` and a request built in many places, add it in the one function that builds or sends requests (an API client's `send`), not at every call site.

## Sensitive operations

```swift
import CryptoKit

let digest = Data(SHA256.hash(data: body))
for (name, value) in try await TrustPinAttest.assertionHeaders(payloadDigest: digest) {
    request.setValue(value, forHTTPHeaderField: name)
}
```

## Simulators

Simulators cannot run App Attest. The user's verifier operator issues a debug token. In the Xcode scheme's environment, set `TRUSTPIN_DEBUG_TOKEN` (and `TRUSTPIN_DEBUG_APP_ID` to `TEAMID.bundle.id` if the simulator reports a different app id). Never put it in the bundle or a plist. It works only in simulator builds, when run from Xcode.

## Errors and state

`TrustPinAttestError`: `invalidConfiguration`, `alreadyInitialized`, `notSetUp`, `unsupportedDevice`, `evidenceUnavailable`, `bindingRequired`, `attestationFailed(reasons:)`, `verifierUnavailable`, `verifierIncompatible`, `invalidDigest`. Switch with `@unknown default`.

`TrustPinAttest.state`: `unavailable`, `attesting`, `ready(expiresAt:)`, `failed(error, retryAt:)`. `setStateListener` observes changes and does not replay the current state. `.distantFuture` means no new attempt in this launch.

Logging is off by default: `TrustPinAttest.set(logLevel: .debug)` during development. Events for metrics: `TrustPinAttest.setEventListener { event in ... }`.
