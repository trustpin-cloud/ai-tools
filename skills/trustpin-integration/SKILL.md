---
name: trustpin-integration
description: Integrate, review, or automate TrustPin certificate pinning in an iOS, macOS, Android, Flutter, or React Native (bare or Expo) app. Use this skill whenever the user mentions TrustPin, TrustPinKit, trustpin_sdk, @trustpin/react-native, cloud.trustpin, trustpin-cli, TrustPin-Info.plist, or trustpin.json, and also when they ask to add certificate pinning, SSL pinning, public key pinning, or remotely updatable pins to a mobile app and TrustPin is in the project or is the chosen tool. Covers first-time SDK integration, wiring pinning into an existing HTTP client (URLSession, Alamofire, OkHttp, Retrofit, Ktor, HttpsURLConnection, Dio, package:http, fetch), auditing an existing TrustPin integration, diagnosing pinning errors, and pin rotation or CI automation with the TrustPin CLI.
license: TrustPin Binary License Agreement. See LICENSE
metadata:
  skill-version: "1.1.0"
  verified-against: "TrustPinKit 6.4.0, kotlin-sdk 6.4.0, trustpin_sdk 6.4.0, @trustpin/react-native 6.4.0, trustpin-cli 6.0.0"
  docs: https://docs.trustpin.cloud
---

# TrustPin integration

TrustPin delivers certificate pins to an app as a signed configuration fetched at runtime, so rotating a pin is a configuration change, not a code change. This skill covers three jobs. Pick the one the user is asking for:

| The user wants | Do |
|---|---|
| TrustPin added to an app | The integration workflow below |
| An existing integration checked, or a pinning error explained | `references/review-checklist.md`, then `references/troubleshooting.md` |
| Pins rotated by hand, or bring-your-own-key signing | `references/cli.md` |
| A CI/CD pipeline for pin rotation, automatic pinning when an AWS ACM certificate renews, or release checks in CI | The `trustpin-cicd` skill (it builds on `references/cli.md`) |

The SDK API references are the most current source: https://trustpin-cloud.github.io/swift.sdk, https://trustpin-cloud.github.io/kotlin.sdk, https://trustpin-cloud.github.io/flutter.sdk, https://trustpin-cloud.github.io/react-native.sdk. The documentation at https://docs.trustpin.cloud and the SDK repositories at https://github.com/trustpin-cloud are the wider source of truth. If the installed SDK behaves differently from this skill, follow the SDK and tell the user what differed.

## What you can do and what only the user can do

| You (in the codebase) | The user (dashboard at app.trustpin.cloud, or the CLI) |
|---|---|
| Detect the platform and HTTP client | Create the account and the project |
| Add the SDK dependency | Choose key management |
| Create the config file with the three project values | Add domains and their pins |
| Add setup code and the readiness gate | Publish (sign) the configuration |
| Wire pinning into the HTTP client | Copy Organization ID, Project ID, Public Key |
| Inventory the hosts the app calls | Hold the master password, private key, and API token |

Never invent the Organization ID, Project ID, or Public Key. If the user has not given them, write the placeholders `your-org-id`, `your-project-id`, `your-base64-public-key`, and say clearly that setup will fail until they are replaced. These three values are not secrets (the public key only verifies signatures), but they identify the project, so prefer the bundled config file over values hardcoded in source.

The master password, a bring-your-own-key private key, and the API token are secrets. Never ask the user to paste them into the chat, never write them to a file in the repository, and never echo them in a command you show.

## Integration workflow

Follow these steps in order. Do not skip the host inventory: it is the step that prevents a broken release.

### 1. Detect the platform

| Signal in the repo | Platform | Read |
|---|---|---|
| `pubspec.yaml` with a `flutter:` section | Flutter | `references/flutter.md` |
| `package.json` depending on `react-native` or `expo` | React Native | `references/react-native.md` |
| `*.xcodeproj`, `Package.swift`, or `Podfile` (and neither of the above) | Swift (iOS, macOS) | `references/swift.md` |
| `build.gradle(.kts)` with an Android plugin (and neither of the first two) | Android / Kotlin | `references/kotlin.md` |

Check Flutter and React Native first, since those projects also contain `ios/` and `android/` folders. If a repository holds separate native iOS and Android apps, integrate each one. Read only the reference file for the platform in front of you.

Check the minimum requirements in the reference file against the project before changing anything. If the project is below them (for example React Native older than 0.85, or Android minSdk under 25), stop and tell the user what would need to be raised. Do not raise deployment targets or toolchain versions without asking.

### 2. Confirm the project side

Ask the user whether a TrustPin project exists and its configuration has been published. If not, walk them through `references/project-setup.md`. The integration can be written before this is done, but it cannot be verified until a configuration is published.

### 3. Inventory the hosts

Run the bundled script from the repository root, then review its output yourself (it finds URL literals, so also check hosts assembled at runtime or loaded from remote config):

```bash
python3 <skill-dir>/scripts/find_hosts.py .
```

Give the user the list and ask them to confirm each host that the pinned client will reach is registered in the TrustPin project.

Why this matters: the default mode is `strict`, and in strict mode a pinned client refuses any host that is not in the published configuration (`domainNotRegistered`). On React Native, and on iOS when the system-wide `TrustPinURLProtocol` is used, pinning covers requests made by third-party libraries too, so their hosts count.

### 4. Install, configure, initialize, wire

Follow the reference file. On every platform the shape is the same:

1. Add the SDK dependency. Use the newest 6.x release on the platform's registry. The versions in the reference files are the ones this skill was verified against.
2. Add the bundled config file (`TrustPin-Info.plist` on Apple platforms, `trustpin.json` on Android) holding the three project values.
3. Call setup once at app start.
4. Wire pinning into the existing HTTP client. Find the client the app already uses and modify it. Do not introduce a new networking library, and do not leave a second, unpinned client talking to the same hosts.

### 5. Verify

Build the app. Then, with the user, confirm a request to a registered host succeeds with the log level at debug. On Flutter and React Native, `validateConnection(host)` is a direct check. Return the log level to error or none for production. If you cannot build or run in this environment, say so and give the user the exact check to run.

### 6. Report

End with a short summary: files changed, the host list, any placeholders still to be replaced, and the project steps still open.

## Rules that hold on every platform

These come from how the SDK behaves. Each one exists because the obvious shortcut produces an app that either stops connecting or silently stops pinning.

- **Keep `strict` as the mode for anything that ships.** `permissive` lets unregistered hosts through and is for development only. If you set it, set it in a debug-only config file or build variant and say so.
- **`setup()` is non-blocking, so follow the documented gate per platform.** It returns before the configuration is downloaded and verified. `awaitConfiguration()` is the fail-closed gate that waits for a validated configuration. On Android, Flutter, and React Native, add it by default: after setup and before the first pinned request or before constructing the pinned client. On Swift it is optional: add it when the user wants to fail closed at startup, and always when the app uses the Alamofire adapter (it keeps the first handshake fast). Where the gate is skipped, the first pinned request waits for the configuration by itself.
- **Call setup once per instance.** A second call is an error (`alreadyInitialized`). Do not call it from several tasks at once.
- **Never fall back to an unpinned client.** If setup or `awaitConfiguration()` fails, surface the error. Catching it and retrying over a plain client removes the protection exactly when it matters.
- **Never fix a pinning error by weakening pinning.** `pinsMismatch`, `allPinsExpired`, and `domainNotRegistered` are answered in the project (add the host, rotate the pin, publish), not by switching a release build to permissive, removing the delegate, or adding a trust-all manager.
- **Do not add an embedded configuration unless the user states the app is protected by RASP.** It is a last-resort fallback for first launch with no reachable source, and an unprotected app must not ship one. If they do use it, it must be regenerated in CI on every release (see `references/cli.md`).
- **Setup failure should not crash app launch.** Handle the error and let the app start. Pinned requests will fail closed on their own.
- **Reuse the pinned client.** Create one session or client and share it. Do not build one per request.
- **Validation listeners and log sinks are observe-only and run on TLS handshake paths.** Keep them fast, do no I/O inline, and never call back into TrustPin from inside one.
- **Publishing is the user's decision.** `trustpin-cli projects sign` makes a configuration live for every installed app. Never run it without the user's explicit go-ahead in this conversation. Use `--dry-run` to rehearse.

## What not to claim

When you describe the result to the user, in code comments, commit messages, or documentation you write for them, do not say the app is now compliant with any security standard (OWASP, MASVS, PCI DSS, or similar) and do not quote uptime figures. Whether an app meets a pinning requirement depends on the whole implementation across all its endpoints. Say what was done: which client is pinned, for which hosts, in which mode.

## Out of scope

The REST API, self-hosted configuration URLs, FIDO-protected keys, and server-side JVM use (the Maven Central artifact is an Android AAR). Point the user to https://docs.trustpin.cloud or support@trustpin.cloud.
