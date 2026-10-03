# Project setup (dashboard steps for the user)

You cannot do the dashboard steps. Relay them to the user and wait for the three project values. Once a project exists, domains and pins can also be managed with the CLI (see `cli.md`), which you can run with the user's go-ahead. Full guide: https://docs.trustpin.cloud/getting-started/setup

## Steps

1. **Sign in** at https://app.trustpin.cloud (Google, GitHub, or an account).
2. **Create a project.** One project per app and per environment is the documented practice, for example "MyApp (Testing)" and "MyApp (Production)".
3. **Choose key management.** This decides how configurations are signed:
   - *Cloud Managed Key*: key created in the browser, encrypted with a master password. Simplest. Suited to development and testing.
   - *Bring Your Own Key*: the user creates and keeps an ECDSA P-256 key that is never uploaded, and signs with the CLI. The documented recommendation for production. Publishing from the web dashboard may be disabled with this option.
   - *FIDO Protected Keys*: signing protected by a FIDO security key.
4. **Add domains.** Enter each host the app connects to (use the host inventory from the skill workflow). For each domain add one or more pins. At least one of these must be set: SHA-256 fingerprint, SHA-512 fingerprint, SPKI SHA-256, SPKI SHA-512.
   - SPKI SHA-256 is the documented preferred choice for most apps.
   - A certificate fingerprint takes precedence over SPKI. To pin by SPKI, leave both fingerprint fields empty.
   - A domain can carry several pins, for example the current certificate and the next one.
   - Pins for any hostname can be looked up at https://trustpin.cloud/tools/certificate-pins
5. **Apply changes, then publish.** "Apply changes" only saves locally. Nothing reaches devices until the user opens **Publish config** and publishes. This is the most common reason a fresh integration reports `domainNotRegistered`.
6. **Copy the project values** and give them to you:
   - Organization ID
   - Project ID
   - Public Key (Base64-encoded ECDSA P-256)

## Notes to pass on

- Many certificate providers generate a new key pair at renewal (AWS ACM always, Let's Encrypt and Cloudflare by default). When the key changes, the SPKI pin changes, so the new pin must be added and published before the old certificate is replaced.
- Use separate projects for development and production so a permissive development setup never reaches a release build.
