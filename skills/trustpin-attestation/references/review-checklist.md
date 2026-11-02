# Reviewing an attestation integration

Use this when the user asks to check or audit app attestation, or before a release. Read the platform reference first. Cite the file and line for each finding, and do not change code unless the user asks for fixes. Review pinning too, with the `trustpin-integration` skill's checklist: attestation depends on it.

## App

1. Every TrustPin package (pinning, attestation, adapters, wrappers) is on the same version, 7.1 or later.
2. Pinning is set up before attestation, for the same instance id.
3. The attestation keys are in the config file the app actually bundles, the verifier URL is HTTPS on a host name, and the attested hosts are exactly the user's own API hosts that verify the token.
4. Setup runs once per launch, its errors are logged, and they do not block or crash launch.
5. A binding is set (`bindToHeader("Authorization")` or `setTokenBinding`), and it matches what the API compares `bind` with.
6. Every HTTP client that calls an attested host carries the header through the path the reference gives (adapter, interceptor, `addingAttestation`, `attestationHeaders`). On Flutter, `TrustPinDioInterceptor` gets `dio:`. No client copies the header onto a redirect by hand.
7. No code waits for a token before sending, fails a request for a missing token, or loops on `getToken()`.
8. No debug token in the repository: not in config files, source, `app.json`, `launch.json`, committed `.env` or Gradle properties. It is passed only to debug builds.
9. No token, assertion, bound value or debug token is logged, shown, or sent to analytics.
10. `reset()` is called only from a support flow (and, on Apple, when a different user account signs in), never on every launch or sign-out.
11. Assertions, if used: one `assertionHeaders` call per operation, over the exact bytes sent, with the token header from the same call.
12. iOS and macOS: the App Attest capability is on the app target with the right environment for the build.
13. Android with Play Integrity: `google_cloud_project_number` is the project number, and the Data safety form declares the Play Integrity API. Without Play Integrity, the key is absent.
14. Production log level is error or none.

## Project and backend (ask the user, or read the backend code if it is in the repository)

15. The verifier's host is a registered domain of the TrustPin project, and the verifier is at contract version 2 or newer.
16. The policy lists every shipped app: Team ID and bundle ID; package name and every signing-certificate digest, including the Play app signing key.
17. The API verifies the token as `references/backend.md` describes: JWKS by `kid`, `ES256` and `typ` only, `iss`, `aud`, `exp`, `tp.prj`, binding, no debug tokens in production.
18. The API's handling of requests without a valid token is decided per endpoint, and matches the policy mode (log in monitor, refuse in enforce).
19. `sub` is not used as a device or user identifier.

## Reporting

Group findings by severity:

- **Leaks or weakens**: items 8, 9, and an API that skips any check of item 17.
- **Breaks attestation**: items 1, 2, 3, 6, 15, 16.
- **Will cause trouble later**: items 5, 7, 10, 11, 18.
- **Hygiene**: the rest.

State what you could not check from the code (the console, the verifier). A clean review does not make the app tamper-proof or compliant with any standard: say what is in place.
