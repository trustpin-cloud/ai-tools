# Swift: iOS and macOS

Source: https://docs.trustpin.cloud/sdk/swift. API reference: https://trustpin-cloud.github.io/swift.sdk

## Requirements

iOS 15+, macOS 13+, Mac Catalyst 15+ (also watchOS 8+, tvOS 15+, visionOS 2+). Swift 6.1+, Xcode 16.3+. async/await is required.

## Install

Swift Package Manager (preferred): `https://github.com/trustpin-cloud/swift.sdk`, version 6.4.0, Up to Next Major.

```swift
dependencies: [
    .package(url: "https://github.com/trustpin-cloud/swift.sdk", from: "6.4.0")
],
targets: [
    .target(name: "YourApp", dependencies: [
        .product(name: "TrustPinKit", package: "swift.sdk"),
        // Only when the app uses Alamofire:
        .product(name: "TrustPinKitAlamofire", package: "swift.sdk")
    ])
]
```

CocoaPods: `pod 'TrustPinKit', '~> 6.4'`, then `pod install`. The Alamofire adapter is SPM only.

For an Xcode project without a `Package.swift`, you usually cannot add the package reliably by editing `project.pbxproj`. Ask the user to add it through File, Add Package Dependencies, and continue with the code.

## Config file

Create `TrustPin-Info.plist` and make sure it is a member of the app target (Copy Bundle Resources). If it is not in the bundle, setup throws `invalidProjectConfig`.

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

Optional keys: `Mode` (`strict` default, or `permissive`, lowercase), `ConfigurationURL` (HTTPS), `EmbeddedConfigurationFile` (RASP-protected apps only).

Per-environment files: `TrustPinConfiguration.fromPlist(fileName: "TrustPin-Info-Debug.plist")`.

## Initialize

Put this where the app starts (`@main` App `init`, or `AppDelegate`). Match the app's existing structure.

```swift
import TrustPinKit

Task {
    do {
        let config = try TrustPinConfiguration.fromPlist()
        try await TrustPin.setup(config)
        // Optional fail-closed gate (default timeout 30s):
        // try await TrustPin.awaitConfiguration()
    } catch {
        // Log it. Do not block launch and do not fall back to an unpinned session.
    }
}
```

## Wire the HTTP client

Pick the row that matches what the app already does.

| App uses | Do this |
|---|---|
| Its own `URLSession` | Delegate (recommended) |
| Alamofire | Adapter |
| Third-party libraries that own their sessions | System-wide `URLProtocol` |
| `URLSession.shared` | It cannot take a delegate. Either replace it with a session you create (preferred, pins only what you choose), or use the system-wide protocol, which also covers `URLSession.shared` |

**URLSession delegate**

```swift
let session = URLSession(
    configuration: .default,
    delegate: TrustPin.makeURLSessionDelegate(),
    delegateQueue: nil
)
```

If the session already has a delegate, keep it: `TrustPin.makeURLSessionDelegate(forwardingTo: existingDelegate)`. Pinning answers the server-trust challenge and every other callback reaches the existing delegate unchanged.

**Alamofire**

```swift
import Alamofire
import TrustPinKit
import TrustPinKitAlamofire

let session = Session(serverTrustManager: ServerTrustManager(evaluators: [
    "api.example.com": TrustPinServerTrustEvaluating()
]))
```

List every pinned host as an evaluator key. The evaluator blocks Alamofire's delegate queue while it verifies, so call `try await TrustPin.awaitConfiguration()` once at startup to keep the first handshake fast.

**System-wide**

```swift
try await TrustPin.setup(config, autoRegisterURLProtocol: true)
```

This covers every `URLSession` in the app, including `URLSession.shared` and sessions owned by third-party libraries. Include their hosts in the host inventory. Plain `http://` requests perform no TLS handshake and are never pin-validated, so keep App Transport Security on.

**One-off checks**: `try await TrustPin.verify(domain: "api.example.com", certificate: pem)`.

## Logging and monitoring

```swift
TrustPin.set(logLevel: .debug)   // before setup; .none, .error, .info, .debug
```

To report suspected interception, implement `TrustPinValidationListener` (`onValidationFailure(instanceId: String, domain: String, error: TrustPinErrors, presentedCertificate: Data)`) and install it with `TrustPin.setValidationListener(_:)`. It fires only for definitive verdicts and cannot change the outcome.

## Errors

Cases of `TrustPinErrors`: `invalidProjectConfig`, `errorFetchingPinningInfo`, `configurationValidationFailed`, `domainNotRegistered`, `pinsMismatch`, `allPinsExpired`, `invalidServerCert`, `alreadyInitialized`, `timeout`, `configIntegrityFailed`.

## Multiple projects

`let api = try TrustPin.instance(id: "payments")`, then `try await api.setup(config)` with its own plist. The id must be non-empty and not `"default"`.
