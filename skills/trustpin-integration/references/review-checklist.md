# Reviewing an existing integration

Use this when the user asks you to check, audit, or review a TrustPin integration, or before a release. Read the platform reference file first so you know what correct looks like. Work through every item, cite the file and line for each finding, and do not change code unless the user asks for fixes.

## Checklist

**Configuration**

1. The config file exists at the right path and is in the app bundle (`TrustPin-Info.plist` in the target's resources, `trustpin.json` under `assets/`).
2. The three project values are real, not placeholders, and contain no whitespace.
3. Release builds use `strict` mode. `permissive` appears only in debug-only files or build variants.
4. Debug and release point at different TrustPin projects, or the user has confirmed a single project is intended.
5. No secret is in the repository: no API token (`tp_`), master password, or private key file. The three project values are not secrets.

**Initialization**

6. Setup is called exactly once per instance, at app start.
7. The readiness gate matches the platform rule in `SKILL.md`.
8. Setup errors are handled and logged, and do not crash launch.
9. Android: the configuration comes from `fromAssets(context)` or `.withAndroidStorage(context)`, and each configuration object is passed to only one `setup` call.
10. React Native: the native init call is present on both platforms and runs before React Native starts.

**Coverage**

11. Every HTTP client that talks to the app's own backends is pinned. Search for other client constructors: a second `URLSession`, `OkHttpClient.Builder()`, `Dio()`, `http.Client()`, WebSocket clients, image loaders, analytics or auth SDKs with their own networking.
12. Run `scripts/find_hosts.py` and compare its output with the registered domains (`trustpin-cli projects config`, or ask the user to read them from the dashboard). Report hosts in the code that are not registered, and registered hosts the code no longer uses.
13. No code path retries over an unpinned client after a pinning failure.
14. No other mechanism disables or duplicates validation: trust-all trust managers, `hostnameVerifier` overrides, `NSAllowsArbitraryLoads`, an Android Network Security Config `<pin-set>` for the same hosts, or another pinning library.

**Operations**

15. Production log level is error or none.
16. Pin-validation failures are observable (validation listener or event stream feeding the app's monitoring). Recommended, not required.
17. If an embedded configuration is shipped: the user confirms RASP protection, and a build step regenerates the file on every release.
18. The SDK is on a current 6.x release.
19. Rotation is owned: there is a scheduled refresh job or a named person, and pins for each host include more than the single live certificate where the provider rotates keys.

## Reporting

Group findings by severity:

- **Breaks pinning or breaks the app**: items 3, 11, 13, 14, and unregistered hosts under item 12.
- **Will break later**: items 6, 7, 9, 17, 19.
- **Hygiene**: the rest.

For each finding give the location, what is wrong, and the fix. State what you could not check from the code alone (anything that lives in the dashboard). Follow the "What not to claim" section of `SKILL.md`: a clean review is not a statement of standards compliance.
