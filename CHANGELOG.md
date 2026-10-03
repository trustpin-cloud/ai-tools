# Changelog

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
