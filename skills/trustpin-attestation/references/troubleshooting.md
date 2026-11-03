# Troubleshooting attestation

Source: the SDK attestation pages at https://docs.trustpin.cloud. Codes are written in the upper-case form of Flutter and React Native; Swift uses camelCase cases of `TrustPinAttestError`, Kotlin PascalCase subclasses.

Start every diagnosis the same way: set the attestation log level to debug, reproduce, and read the state (it carries the error and, for `ATTESTATION_FAILED`, the verifier's reasons). The verifier's log has the matching line for each request.

## The request has no header

- The host is not in the attested hosts, or the URL is `http://`.
- The client is not one the SDK serves automatically (see the platform reference), so nothing adds the header.
- No token yet: the first attestation is still running, a wait after a failure is in progress, or the state is failed. Check the state.
- React Native: the native start call (`TrustPinReactNativeAttest.start`) or the Expo plugin is missing, so every call rejects with `NOT_SET_UP`.

## Setup

**`INVALID_CONFIGURATION`**: a key is missing or invalid (`AttestVerifierURL` / `attest_verifier_url`, `AttestedHosts` / `attested_hosts`), the verifier URL is not HTTPS on a host name, or a host is an IP address. Also when a second setup starts while the first is running.

**`ALREADY_INITIALIZED`**: setup ran twice for one instance (hot restart, tests, two call sites).

## Failed states

**`VERIFIER_UNAVAILABLE`** every time: the verifier's host is not a registered domain of the TrustPin project (strict pinning refuses it), the verifier is down, or the URL is wrong. Register the domain and publish the pin configuration; never switch pinning to permissive.

**`VERIFIER_INCOMPATIBLE`**: the verifier is older than contract version 2. Upgrade it to 1.0.0 or later. The app needs no change.

**`ATTESTATION_FAILED`** with `reasons`:

| Reason | Cause | Fix |
|---|---|---|
| `app_not_allowed` | The app, its Team ID, or its signing certificate is not in the policy | Add it. Android installs from Play use the Play app signing key |
| `dev_environment` | An Xcode-run iOS build, with **Accept development builds** off | Turn it on for development |
| `too_many_attestations` | The verifier's per-key limit | The SDK keeps the key and waits as asked. Look for a loop calling `reset()` or `assertionHeaders` |
| `http_<status>`, `invalid_key`, `invalid_input` | Supplied by the SDK, not the verifier | Read the SDK debug log |

After a refusal the SDK waits before trying again, as long as the verifier asks, also across launches. Once the cause is fixed, `reset()` retries at once.

**`BINDING_REQUIRED`**: the policy requires a binding and none is set yet. Expected before sign-in. With header binding the first request carrying the header gets a token; with a fixed binding, call `setTokenBinding` before `prefetch()`.

**`UNSUPPORTED_DEVICE`**: App Attest unavailable (simulators without a debug token, some Macs, older hardware), or new keys keep failing. Requests go out without the header; the API decides.

**`EVIDENCE_UNAVAILABLE`**: the policy's evidence option needs something the device cannot provide (Play Integrity without Google Play or without a project number, Key Attestation on an emulator).

## Simulators and emulators

They need a debug token, allowed by both the policy (**Allow debug tokens**) and the verifier. iOS: `TRUSTPIN_DEBUG_TOKEN` in the Xcode scheme (Flutter: `--dart-define`), only when run from Xcode or the Flutter tool. Android: passed in debuggable builds only. Its tokens carry `tp.env` `debug`, which production APIs refuse.

## The API refuses a valid-looking token

- Wrong issuer, audience or project in the API's check: compare with the verifier's `TRUSTPIN_TOKEN_ISSUER` and `TRUSTPIN_TOKEN_AUDIENCE`.
- The binding was computed over a different value than the app bound (another header, or the value after the API modified it).
- Clock skew over 60 seconds.
- A debug token in production, correctly refused.

## Assertions refused

A header is missing, the API's digest is not over the same bytes the app digested, the nonce expired or was reused (`invalid_challenge`), or the verifier is older than contract version 2.
