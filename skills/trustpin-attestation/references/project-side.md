# The project side: policy, verifier, domain, CLI

Source: https://docs.trustpin.cloud/attestation/setup, /attestation/verifier, /attestation/rollout, and the CLI's attestation guide. These are steps the **user** does in the TrustPin console, their own infrastructure, or with the CLI. Walk them through what is missing; do not do it for them.

## Before attestation

- A TrustPin project with pinning set up and its configuration published.
- The project signs with a cloud key (master password) or with the user's own key (BYOK, a PEM file). Projects protected with FIDO cannot use app attestation.
- Apple Developer portal access for Apple apps. Play Console and Google Cloud access for Android apps that use Play Integrity.

## 1. Apps in the policy

**Apple**, per app:

1. Enable **App Attest** on the App ID in the Apple Developer portal.
2. Add the **App Attest** capability in Xcode. Its entitlement `com.apple.developer.devicecheck.appattest-environment` is `development` for builds run from Xcode and `production` for TestFlight and the App Store.
3. The policy needs the **Team ID** and **Bundle ID**.
4. **Accept development builds** must be on while testing Xcode-run builds, or they are refused with `dev_environment`. Turn it off for production.

**Android**, per app:

1. The **Package name**.
2. The **Signing certificate SHA-256** of every certificate that signs an accepted build: the debug key (Android Studio builds), the upload key if builds signed with it are installed, and the **Play app signing** key (Play Console, Test and release, App integrity). `keytool -list -v -keystore <keystore> -alias <alias> | grep 'SHA256:'` prints it.
3. **Evidence**: **Key Attestation only** is the simplest start (no Google setup). **Either**, **Both** and **Play Integrity only** need Play Integrity: the API enabled in a Google Cloud project linked to the app in Play Console, a service account for the verifier, and the Cloud project **number** in both the policy and the app.

## 2. Policy settings to start with

| Setting | Start with |
|---|---|
| Mode | **Monitor (recommended to start)**: tokens are issued even when checks fail, so the API can measure before enforcing |
| Access token lifetime | 1 h |
| Key certificate lifetime | 30 days |
| Require token binding | Off until the API checks `bind` |
| Allow debug tokens | On for staging only |

Setting up attestation and its **first publish** happen in the console: project, **Attestation** page, **Set up**, add the apps, then **Sign and publish**. Running verifiers pick up a new version within their refresh interval (5 minutes by default), with no redeploy.

## 3. The verifier

The verifier runs in the user's infrastructure, behind their gateway, from the deployment bundle on the console's **Deployment** tab (Docker Compose, Kubernetes, or an env file). The image is `trustpincloud/attest-verifier`, pinned to an exact version (1.0.0 or later). Its signing keys and challenge secrets are generated with the image's `keygen` command and kept in the user's secret store. Full steps: https://docs.trustpin.cloud/attestation/verifier.

The SDKs 7.1 require a verifier at contract version 2 or newer (0.2.2 or later). An older one makes the SDK report `verifierIncompatible` and send no header.

## 4. Register the verifier's domain

The SDKs pin their calls to the verifier, so its host (for example `attest.example.com`) must be a registered domain of the same TrustPin project, with the pin configuration signed and published again. In strict mode an unregistered verifier host fails every call with `verifierUnavailable`.

## 5. Policy as code with the CLI (trustpin-cli 7.0.0 or later)

After the first publish in the console, the policy can live in the repository and be published from CI. The rules of the `trustpin-integration` skill's `references/cli.md` apply: never ask for, print, or write the API token, master password, or private key, and never sign without the user's explicit go-ahead.

```text
trustpin-cli projects attestation get     <org-id> <project-id> [--output json]
trustpin-cli projects attestation update  <org-id> <project-id> --file <settings.json | ->
trustpin-cli projects attestation config  <org-id> <project-id> [--raw]
trustpin-cli projects attestation sign    <org-id> <project-id> [-k key.pem] [--dry-run] [--jws-out file]
trustpin-cli projects attestation publish <org-id> <project-id> --jws <file | ->
trustpin-cli projects attestation bundle  <org-id> <project-id> --format compose|kubernetes|env [--environment name] [--out dir]
```

Export the editable part once and commit it:

```bash
trustpin-cli projects attestation get "$ORG_ID" "$PROJECT_ID" --output json \
  | jq '.data | {policy, deployment}' > attestation.json
```

- `update` stores and validates a change as a new, unpublished policy version. An identical file keeps the version, so running it on every build is safe. The API rejects the first invalid or unknown field and names it.
- `sign` signs the current version and publishes it. When the current version is already published it does nothing and succeeds, so `update` then `sign` is safe on every merge. Cloud-key projects prompt for the master password; BYOK projects pass `-k key.pem`. Rehearse with `--dry-run`.
- `sign --jws-out` signs without publishing, where the key lives; `publish --jws` publishes that file elsewhere with a member token.
- In the file, signing digests are the unpadded base64url of the SHA-256, not the colon-separated hex `keytool` prints: `echo '<SHA256 value>' | tr -d ':' | xxd -r -p | base64 | tr '+/' '-_' | tr -d '='`.
- The token must belong to a **member** of the organization: viewers can run `get`, `config` and `bundle` only.
- Disabling, re-enabling and abandoning attestation stay in the console.

`attestation get` shows `Published version: <n> (up to date)` once a change is live. Each verifier also logs `policy updated` with the new version within its refresh interval.

## 6. Rolling out: monitor to enforce

1. **Monitor.** The API logs `tp.result` and `tp.reasons` and allows every request.
2. **Measure** per endpoint: the share of requests without the header, and `fail` results by reason, platform and app, over a full release cycle.
3. **Adjust** the policy for legitimate devices that fail.
4. **Enforce** in the policy, then refuse in the API, starting with the most sensitive endpoints. Turn **Allow debug tokens** off, and remove certificates no longer shipped.
5. **Keep a fallback** for app versions without attestation, per endpoint.

Moving to enforce is the user's call. Full guide: https://docs.trustpin.cloud/attestation/rollout.
