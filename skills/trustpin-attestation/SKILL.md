---
name: trustpin-attestation
description: Add, review, or troubleshoot TrustPin app attestation, which proves to an API that requests come from the genuine app on a genuine device (Apple App Attest, Android Key Attestation, Google Play Integrity), in iOS, macOS, Android, Flutter, or React Native (bare or Expo) apps, and verify its tokens in the backend or at an API gateway. Use whenever the user mentions TrustPinAttestKit, kotlin-attest, trustpin_attest, @trustpin/react-native-attest, the TrustPin-Attestation or TrustPin-Assertion header, the TrustPin attestation verifier, an attestation policy, or asks for app attestation, App Attest, or Play Integrity with TrustPin. Covers adding the SDK module, token binding, assertions for sensitive operations, debug tokens, verifying tokens in an API, rolling out from monitor to enforce, and publishing the policy with trustpin-cli. For certificate pinning itself, use trustpin-integration.
license: TrustPin Binary License Agreement. See LICENSE
metadata:
  skill-version: "1.2.1"
  verified-against: "TrustPinAttestKit 7.1.0, kotlin-attest 7.1.1, trustpin_attest 7.1.1, @trustpin/react-native-attest 7.1.1, attest-verifier 1.0.0, trustpin-cli 7.0.0"
  docs: https://docs.trustpin.cloud/attestation/overview
---

# TrustPin app attestation

App attestation proves to the user's API that a request comes from their genuine app on a genuine device that meets their policy. The device attests once per device key to the attestation verifier **the user runs**, then renews a short-lived token cheaply. The token travels in the `TrustPin-Attestation` header, and the user's API or gateway verifies it.

This skill covers four jobs. Pick the one the user is asking for:

| The user wants | Do |
|---|---|
| Attestation added to an app | The workflow below |
| Tokens verified in the backend or at a gateway | `references/backend.md` |
| An existing attestation integration checked, or an error explained | `references/review-checklist.md`, then `references/troubleshooting.md` |
| The policy managed from the repository or CI | `references/project-side.md` |

The documentation at https://docs.trustpin.cloud/attestation/overview and the per-SDK pages (`/sdk/swift-attestation`, `/sdk/kotlin-attestation`, `/sdk/flutter-attestation`, `/sdk/react-native-attestation`) are the source of truth. If the installed SDK behaves differently from this skill, follow the SDK and tell the user what differed.

## What attestation is, and is not

- It tells the API that the request comes from the listed app, signed by the listed key, on a device whose platform vouches for it.
- It is **not** runtime protection: it does not detect hooking, debugging, tampering, root or jailbreak on a device that passed. Never describe it as RASP, anti-tamper or anti-fraud.
- The SDK **never blocks or fails a request**. A request without a valid token reaches the API, and the API decides what it may do.

## What you can do and what only the user can do

| You (in the codebase) | The user (TrustPin console, their infrastructure, or the CLI) |
|---|---|
| Add the attestation package next to the pinning one | Set attestation up for the project and publish the first policy in the console |
| Add the attestation keys to the existing config files | List the apps (Team ID and bundle ID, package name and signing-certificate digests) |
| Add setup, binding and prefetch | Deploy the verifier from the console's deployment bundle |
| Make sure the HTTP client in use carries the header | Register the verifier's host as a domain of the TrustPin project |
| Add assertions on sensitive operations, if asked | Run the verifier, its secrets and keys, and switch the policy from monitor to enforce |
| Write the token check in the API, if asked | Publish policy changes (`projects attestation sign`) |

Never invent the verifier URL, Team ID, bundle ID, package name or signing-certificate digests. Use the placeholders `https://attest.example.com` and `api.example.com` when the user has not given them, and say clearly that attestation will not work until they are replaced.

The verifier's signing keys, challenge secrets, monitor API key, Play Integrity service account, a debug token, the CLI API token, the master password and a bring-your-own-key private key are secrets. Never ask the user to paste them into the chat, never write them to a file in the repository, and never echo them in a command you show.

## Integration workflow

### 1. Check that pinning is in place

Attestation uses the pinning SDK of the same version: the verifier calls are pinned, and the HTTP integrations that add the header are the pinning ones. If TrustPin pinning is not integrated yet, do it first with the `trustpin-integration` skill. If it is on an older major version, plan the upgrade to 7.1 or later with the user before adding attestation: all TrustPin packages in the app must be on the same version.

### 2. Confirm the project side

Ask the user, and walk them through `references/project-side.md` for anything missing:

1. Attestation is set up for the project and a policy is published (in **monitor** mode to start).
2. The verifier is deployed and reachable over HTTPS, at contract version 2 or newer: verifier 1.0.0 or later.
3. The verifier's host is a registered domain of the TrustPin project. In strict mode an unregistered verifier host fails every call (`verifierUnavailable`) and no header is ever sent.

The code can be written before this is done, but it cannot be verified until all three hold.

### 3. Detect the platform and read its reference

| Signal in the repo | Platform | Read |
|---|---|---|
| `pubspec.yaml` with a `flutter:` section | Flutter | `references/flutter.md` |
| `package.json` depending on `react-native` or `expo` | React Native | `references/react-native.md` |
| `*.xcodeproj`, `Package.swift` or `Podfile` (and neither of the above) | Swift (iOS, macOS) | `references/swift.md` |
| `build.gradle(.kts)` with an Android plugin (and neither of the first two) | Android / Kotlin | `references/kotlin.md` |

Check the reference's requirements against the project before changing anything. Do not raise deployment targets, toolchains or framework versions without asking.

### 4. Install, configure, set up, bind, send

Follow the reference file. On every platform the shape is the same:

1. Add the attestation package at the same version as the pinning package.
2. Add the attestation keys (verifier URL and attested hosts, plus the Google Cloud project number on Android only when the policy uses Play Integrity) to the config file pinning already reads.
3. Set attestation up once per launch, after pinning.
4. Bind tokens to the user's session, usually `bindToHeader("Authorization")`, and prefetch.
5. Make sure the app's HTTP client carries the header. Use the path the reference gives for that client. Do not introduce a new networking library.
6. iOS and macOS: the App Attest capability on the app target.

### 5. Verify

Build the app. Then, with the user and the log level at debug, confirm that a request to an attested host carries the header and that the API (or the verifier's log) sees a valid token. On simulators and emulators that needs a debug token the user's verifier operator issues (see the reference); real evidence needs a real device. If you cannot build or run here, say so and give the user the exact check.

### 6. Report

End with a short summary: files changed, the attested hosts, the binding mode, placeholders still to replace, and the project steps still open (policy, verifier, domain registration, App Attest capability, and when to move from monitor to enforce).

## Rules that hold on every platform

- **Pinning first, same version.** Set up the pinning instance before the attestation instance with the same identifier, and keep all TrustPin packages on one version.
- **Only the attested hosts get the header.** List exactly the hosts of the user's own API that will verify the token. Never add third-party hosts.
- **Never block or retry on a missing token in the app.** The SDK sends the request without the header after a short, bounded wait. Do not wrap requests to wait for a token, do not fail them client-side, and do not loop on `getToken()`.
- **Bind tokens to the session** with `bindToHeader("Authorization")` when requests carry the session in that header, or `setTokenBinding(value)` otherwise. With **Require token binding** on, a failed state with `bindingRequired` before sign-in is expected.
- **Debug tokens come from the build, never from a file.** Not from `TrustPin-Info.plist`, `trustpin.json`, a committed `.env`, or source. Never in a release build.
- **Never log or display a token, an assertion, a bound value or a debug token**, and never send them anywhere but the user's API and verifier.
- **`sub` is the device key, not a device or user identifier.** It changes on reinstall, reset or key replacement. Do not use it to identify users or devices.
- **`reset()` is for support flows**, not routine sign-out or every launch. Calling it in a loop spends attestations and trips the verifier's per-key limit. The one routine case: on Apple platforms, when a **different user account** signs in on the same device (Apple asks for one key per user account).
- **Assertions are per operation.** Each `assertionHeaders(digest)` call produces a new one; compute the digest over the exact bytes sent, and never cache or reuse the headers.
- **Fixing an attestation failure never means weakening pinning.** A `verifierUnavailable` from strict pinning is fixed by registering the verifier's domain, not by switching to permissive.
- **Publishing a policy is the user's decision.** Never run `trustpin-cli projects attestation sign` without the user's explicit go-ahead in this conversation. Use `--dry-run` to rehearse.
- **Moving to enforce is the user's decision**, after they have measured in monitor mode (`references/backend.md`).

## What not to claim

Do not say the app is now protected against tampering, rooting, jailbreaking, bots or fraud, and do not claim compliance with any standard (OWASP, MASVS, PCI DSS, or similar). Say what was done: which client carries the header, for which hosts, bound how, and what the API still has to decide.

## Out of scope

Deploying and operating the verifier itself (point the user to https://docs.trustpin.cloud/attestation/verifier and /attestation/operations), the REST API, and FIDO-protected project keys (they do not support attestation). For questions the documentation does not answer: support@trustpin.cloud.
