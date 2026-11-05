# Changelog

## 1.2.1

- `trustpin-attestation` targets the attestation verifier `trustpincloud/attest-verifier` 1.0.0 or later, and installs kotlin-attest, trustpin_attest and @trustpin/react-native-attest 7.1.1. The snippets for sensitive operations add the attestation header before asking for the assertion headers, so the assertion is bound to that request's session. On Android, a debug token identifies the app by the package name it runs under, so a debug build with an `applicationIdSuffix` needs its own entry in the policy.
- `trustpin-integration` installs kotlin-sdk, trustpin-okhttp, trustpin-ktor and trustpin_sdk 7.1.1. The pinning API is unchanged.

Verification for this release:

| Platform | Packages | What was checked |
|---|---|---|
| Swift | TrustPinKit, TrustPinAttestKit, TrustPinKitAlamofire 7.1.0 | Unchanged since 1.2.0 |
| Kotlin | kotlin-sdk, kotlin-attest, trustpin-okhttp, trustpin-ktor 7.1.1 | Changed snippets and API names checked against the 7.1.1 source; not recompiled |
| Flutter | trustpin_sdk, trustpin_attest 7.1.1 | Changed snippets and API names checked against the 7.1.1 source; not re-analyzed |
| React Native | @trustpin/react-native, @trustpin/react-native-attest 7.1.1 | Changed snippets and API names checked against the 7.1.1 source; not re-type-checked |
| CLI | trustpin-cli 7.0.0 | Unchanged since 1.2.0 |

## 1.2.0

- New skill `trustpin-attestation` (`/trustpin:trustpin-attestation`): adds, reviews, and troubleshoots TrustPin app attestation (Apple App Attest, Android Key Attestation, Google Play Integrity) on iOS, macOS, Android, Flutter, and React Native (bare and Expo), with token binding, assertions for sensitive operations, debug tokens for simulators and emulators, verifying tokens in the API or at a gateway, rolling out from monitor to enforce, and policy publishing with `trustpin-cli projects attestation`. It never handles the verifier's keys, secrets or debug tokens, and never publishes a policy without approval.
- `trustpin-integration` now targets the 7.1 SDKs: TrustPinKit, kotlin-sdk, trustpin_sdk and @trustpin/react-native 7.1.0. Swift: watchOS 9, Mac Catalyst 15, Alamofire 5.10 or later for the adapter. Flutter: Flutter 3.44 and Swift Package Manager only, and `TrustPinDioInterceptor(dio: dio)`. Each platform reference points to the attestation skill, and the review checklist expects every TrustPin package on one 7.x version.
- CLI reference updated to trustpin-cli 7.0.0 (digests for all four binaries), which adds the `projects attestation` commands. The pinning commands and flags are unchanged.
- The release now also publishes `trustpin-attestation.skill`, and `trustpin-skills.zip` holds all three skills.

Verification for this release:

| Platform | Packages | What was checked |
|---|---|---|
| Swift | TrustPinKit, TrustPinAttestKit, TrustPinKitAlamofire 7.1.0 | Pinning and attestation reference snippets built in a Swift package for macOS (`swift build`) and iOS (`xcodebuild`), Xcode 27, Alamofire 5.12 |
| Kotlin | kotlin-sdk, kotlin-attest, trustpin-okhttp, trustpin-ktor 7.1.0 | Reference snippets compiled (Kotlin 2.3.0, Android Gradle plugin 8.13) with OkHttp 4.12, Retrofit 2.11, Ktor 3.0, including exhaustive `when` over `TrustPinError` and `TrustPinAttestError` |
| Flutter | trustpin_sdk, trustpin_attest 7.1.0 | Reference snippets pass `flutter analyze` (Flutter 3.47) in a new project |
| React Native | @trustpin/react-native, @trustpin/react-native-attest 7.1.0 | JavaScript snippets type-checked against the npm packages (React Native 0.85); both Expo config plugins run through `expo prebuild` |
| CLI | trustpin-cli 7.0.0 | The Linux x64 binary checked against its published digest |

## 1.1.0

- New skill `trustpin-cicd` (`/trustpin:trustpin-cicd`): sets up or reviews CI/CD automation for pin rotation and release checks with trustpin-cli. Covers pinning automatically when an AWS ACM certificate renews (EventBridge and Lambda), scheduled refresh on CodeBuild and CodePipeline, a self-hosted configuration on S3 and CloudFront, and GitHub Actions, GitLab CI, Azure DevOps, Jenkins, CircleCI, and mobile CI services. It never handles secret values and never signs without approval.
- The AWS reference uses ACM's events as AWS documents them, and adds lessons from a working deployment: one function for several certificates and projects, a schedule next to the event for drift and regional certificates, writable `/tmp` and cleanup, strict exit-code handling, and signing only when something changed.
- CLI reference updated from TrustPin's CLI documentation: digests for all four v6.0.0 binaries, Brewfile install, the safety guarantees of `refresh-certs` and `cleanup`, `projects jws` behavior, and CLI troubleshooting entries.
- The release now also publishes `trustpin-cicd.skill` and `trustpin-skills.zip` (both skills) in place of `trustpin-integration.zip`.

Verification for this release: the plugin validates with `claude plugin validate --strict`.

## 1.0.0

First release.

- Integration workflow for Swift, Kotlin, Flutter, and React Native (bare and Expo).
- Review checklist, troubleshooting reference, CLI and CI reference.
- Host inventory script.

Verification performed for this release. On every platform a sample app was built and a pinned request tested at runtime, in addition to:

| Platform | SDK | What was checked |
|---|---|---|
| Kotlin | kotlin-sdk 6.4.0, trustpin-okhttp, trustpin-ktor | Reference snippets compiled with kotlinc 2.4.20 against the published artifacts, OkHttp 4.12, Retrofit 2.11, Ktor 3.6 |
| Flutter | trustpin_sdk 6.4.0 | Reference snippets pass `flutter analyze` (Flutter 3.47) |
| React Native | @trustpin/react-native 6.4.0 | Expo config plugin run through `expo prebuild` (React Native 0.86), JavaScript snippet type-checked |
| Swift | TrustPinKit 6.4.0 | Every symbol checked against the published `.swiftinterface`. Reference snippets built for iOS and macOS with Swift 6.4 (Xcode 27) and Alamofire 5.9 |
| CLI | trustpin-cli 6.0.0 | Commands run against a test project |
