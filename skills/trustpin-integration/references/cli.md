# CLI, pin rotation, and CI

Source: https://docs.trustpin.cloud/cli/overview, /cli/installation, /cli/commands, /cli/devops-guide, and the official CLI documentation at https://trustpin-cloud.github.io/homebrew-trustpin/trustpin-cli. Applies to trustpin-cli 6.0.0. Run `trustpin-cli <command> --help` to confirm flags on the installed version.

## Contents

1. Safety rules
2. Install and authenticate
3. The model: stage, then sign
4. Command reference
5. Rotating a certificate
6. Bring your own key
7. CI pipelines
8. Embedded configuration in release builds
9. Exit codes
10. Behavior to rely on

## 1. Safety rules

- **`projects sign` publishes to every installed app.** Do not run it without the user's explicit go-ahead in this conversation. Offer `--dry-run` first.
- **Secrets stay out of the chat and the repository.** The API token (`tp_...`), the master password, and a bring-your-own-key private key are secrets. Do not ask the user to paste them, do not read them, and never put a secret value in a command, a file, or a message. The user enters them at the CLI's own prompt, or supplies them from their CI secret store as TrustPin's DevOps guide describes (https://docs.trustpin.cloud/cli/devops-guide).
- **Staging commands are safe to preview.** `upsert`, `cleanup`, and `refresh-certs` accept `--dry-run`. Use it before the real run when working on a production project.
- **Read commands are safe.** `user info`, `projects list`, `projects get`, `projects config`, `projects jws`, `domains certificates` change nothing.

## 2. Install and authenticate

```bash
brew tap trustpin-cloud/trustpin-cli
brew trust trustpin-cloud/trustpin-cli   # one-time, required by Homebrew 6.0+
brew install trustpin-cli
```

Update with `brew update && brew upgrade trustpin-cli`. To install through a Brewfile, mark the formula as trusted so `brew bundle` does not prompt: `tap "trustpin-cloud/trustpin-cli"` and `brew "trustpin-cli", trusted: true` (Homebrew 6.0+). Check the installed version with `trustpin-cli --version`. Upgrading from v5 keeps existing commands, flags, exit codes, and JSON envelopes.

Direct download (CI), pinned to the version this skill covers. The release publishes no checksum file, so verify against the SHA-256 digest shown on the release page (https://github.com/trustpin-cloud/homebrew-trustpin/releases/tag/v6.0.0). The binaries and their digests for v6.0.0:

| File | SHA-256 |
|---|---|
| `trustpin-cli-linux-x64` | `5bb889bc6ae131d2caef0fb6ec59f97aab95a5f400bc7ecb902494f522afce83` |
| `trustpin-cli-linux-arm64` | `6b683fbcdde46c0a430364645f1e063149ce6a1f5a1fd696aa4a6303c7cbc091` |
| `trustpin-cli-macos-x64` | `40389c349a9903a516f18790755ecaae55e7ddc2984b25e7f56b8367fbc7b893` |
| `trustpin-cli-macos-arm64` | `b37ed6c7cabb7be80f11620cc095abc7628012ad8c7f93863bd183937566ce90` |

Linux x64 example:

```bash
curl -fL https://github.com/trustpin-cloud/homebrew-trustpin/releases/download/v6.0.0/trustpin-cli-linux-x64 -o trustpin-cli
echo "5bb889bc6ae131d2caef0fb6ec59f97aab95a5f400bc7ecb902494f522afce83  trustpin-cli" | sha256sum -c -
chmod +x trustpin-cli && sudo mv trustpin-cli /usr/local/bin/
```

When the CLI moves to a newer release, change both the version in the URL and the digest. Use `trustpin-cli-linux-arm64` on ARM runners and ARM Lambda functions.

Authentication uses a Personal Access Token the user creates at https://app.trustpin.cloud/account/access-tokens. The user runs `trustpin-cli configure` themselves and enters the token at the prompt. For CI, the user supplies the token from their CI secret store. Read TrustPin's DevOps guide (https://docs.trustpin.cloud/cli/devops-guide) for the current variable names and setup, and do not write token values anywhere.

Find the IDs:

```bash
trustpin-cli user info
trustpin-cli projects list --output json | jq -r '.data.projects[] | "\(.organization_id) \(.id) \(.name)"'
```

## 3. The model: stage, then sign

1. **Stage** pin changes in the stored configuration (`refresh-certs`, or `cleanup` plus `upsert`). Nothing reaches devices.
2. **Sign** the configuration (`projects sign`). This publishes it and it is live.

`projects get` shows `Configuration Version` and `Published Version`. If they differ, there are unpublished changes.

## 4. Command reference

| Command | Effect |
|---|---|
| `projects get <org> <project>` | Project details, public key, stored vs published version |
| `projects config <org> <project>` | The stored configuration as JSON (domains, pins, expiry) |
| `domains certificates <domain>` | Live and Certificate Transparency certificates for a host, with all pin formats |
| `projects refresh-certs <org> <project> --domain <fqdn> [--remove-expired]` | Pins every certificate TrustPin can see for that host as SPKI SHA-256. Adds the domain if missing. Never discards existing pins. Writes nothing if the lookup fails |
| `projects upsert <org> <project> --domain <d> --pin <type>:<value> [--expires <ISO8601>]` | Add or update one pin by hand. Types: `spki-sha256`, `spki-sha512`, `sha256`, `sha512` |
| `projects cleanup <org> <project>` | Remove already-expired pins across the whole project |
| `projects sign <org> <project> [--dry-run]` | Sign and publish. Key options: see `projects sign --help` |
| `projects jws <org> <project> [--verify] [--decode] [--output-file <path>]` | Fetch the published signed configuration from the CDN |

Most commands accept `--output json`.

Use `refresh-certs` when the certificate is live or visible in Certificate Transparency. Use `upsert` for a host TrustPin cannot observe (internal only), a specific digest type, or a custom expiry.

## 5. Rotating a certificate

The safe order is: new pin published first, new certificate deployed second.

```bash
# 1. Stage: pick up the new certificate (already issued and in CT, or already live)
trustpin-cli projects refresh-certs "$ORG_ID" "$PROJECT_ID" \
  --domain api.example.com --remove-expired --output json

# 2. Review what changed: Configuration Version now differs from Published Version
trustpin-cli projects get "$ORG_ID" "$PROJECT_ID"
```

3. **Publish is the user's step.** Offer `trustpin-cli projects sign "$ORG_ID" "$PROJECT_ID" --dry-run` first, which fails on a bad key or password before anything goes live, then the same command without `--dry-run`. The CLI asks for the master password at its own prompt. Run it only with the user's go-ahead, and never put the password in a command.
4. **Confirm what is live:** `trustpin-cli projects jws "$ORG_ID" "$PROJECT_ID" --verify`.

Then the user deploys the new certificate to the servers. Keep the old and new pins active together during the overlap. The documentation recommends adding the new pin 7 to 14 days before the old certificate is replaced, because an app only picks up a new configuration when it is next opened. If the renewal reuses the same key pair, the SPKI pin does not change and only the expiry needs updating.

If signing fails, the previously published configuration stays active.

## 6. Bring your own key

For projects of type "Bring Your Own Keys", the private key never leaves the user's side and publishing from the web dashboard may be disabled, so the CLI is how configurations get published.

The user runs `trustpin-cli projects sign` with the `--private-key` option pointing at their PEM file, first with `--dry-run`, then without it. The key must be PEM. A key generated with `openssl ecparam -genkey` also prints an `EC PARAMETERS` block. Keep only the `EC PRIVATE KEY` block in the file (reported from a working deployment, not in the documentation). If it is password-protected, the CLI prompts. `--dry-run` validates the key against the project's public key: a wrong key fails with `INVALID_KEY_PAIR`, a wrong password with `INCORRECT_PASSWORD`. Run `trustpin-cli projects sign --help` for the exact options on the installed version.

Do not read, print, copy, or commit the key file. In CI, the user writes it from their secret store to a temporary file with restricted permissions and deletes it at the end of the job.

## 7. CI pipelines

For a complete walk-through of a pipeline on AWS (including pinning automatically when an ACM certificate renews) or another CI system, use the `trustpin-cicd` skill. A scheduled job can refresh pins and publish only when something changed. TrustPin's DevOps guide (https://docs.trustpin.cloud/cli/devops-guide) has the current CI examples, including how to supply the API token and the signing credentials from the CI secret store. Follow it for that part, and do not write secret names or values into a pipeline file yourself.

The job, in order:

1. Install the CLI pinned to a version, as in section 2, including the digest check.
2. Authenticate and rehearse signing with `--dry-run`, so bad credentials fail before anything is staged.
3. Refresh the pins and detect whether anything changed:

   ```bash
   set -euo pipefail
   BEFORE=$(trustpin-cli projects get "$ORG_ID" "$PROJECT_ID" --output json | jq -r '.data.project.config_version')
   trustpin-cli projects refresh-certs "$ORG_ID" "$PROJECT_ID" --domain api.example.com --remove-expired --output json
   AFTER=$(trustpin-cli projects get "$ORG_ID" "$PROJECT_ID" --output json | jq -r '.data.project.config_version')
   if [ "$BEFORE" = "$AFTER" ]; then echo "No pin changes."; exit 0; fi
   ```

4. Only when something changed: sign, then confirm with `trustpin-cli projects jws "$ORG_ID" "$PROJECT_ID" --verify`.

To refresh every host in the project, read the list from the stored configuration:

```bash
trustpin-cli projects config "$ORG_ID" "$PROJECT_ID" | jq -r '.data.config.domains[].domain'
```

Writing a pipeline file is an edit to the user's repository like any other. Creating the secrets and enabling the workflow are the user's steps. An unattended job that signs is publishing without a human in the loop, so state that plainly when you propose one.

## 8. Embedded configuration in release builds

Only for apps protected by RASP (see the rule in `SKILL.md`). The bundled file must be regenerated on every release so it is never older than the app:

```bash
trustpin-cli projects jws "$ORG_ID" "$PROJECT_ID" --output-file path/to/trustpin-seed.b64
```

Write it to the location the platform reference file gives, in a build step that runs before the app is compiled.

## 9. Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (including a no-op) |
| 1 | CLI not configured |
| 2 | API error |
| 3 | Authentication error |
| 4 | Validation error (bad arguments) |
| 5 | Resource not found |
| 6 | Key error |
| 7 | File error |
| 8 | Cryptography error (for example signature verification failed) |
| 9 | Cancelled by user |
| 10 | Permission error |
| 99 | Unexpected error |

## 10. Behavior to rely on

From the command reference and the DevOps guide:

- **`refresh-certs` is safe to run unattended.** It never discards existing pins. A failed lookup, or a lookup that returns no certificates, writes nothing at all (not even expired-pin removal), so a transient DNS or TLS failure cannot strip a domain's pins. A run that changes nothing sends no request and does not bump the configuration version.
- **`refresh-certs` adds the domain if missing, and never removes one.** It writes pins as SPKI SHA-256. It pins every unexpired certificate TrustPin can see (the live one plus Certificate Transparency issuances), so a newly issued certificate is pinned alongside the one still served. That is the dual-pin overlap that makes rotation safe.
- **Expired-pin removal has two scopes.** `refresh-certs --remove-expired` prunes only the named domain. `projects cleanup` sweeps the whole project. Both remove only pins whose expiry is in the past, and pins with no expiry are kept. `cleanup --output json` reports `data.removed_pins`.
- **`upsert` is idempotent.** Pins match by type and value, and the expiry is not part of the key. Use it for a host TrustPin cannot observe, a specific digest type, or a custom expiry.
- **`domains certificates` labels each certificate** as live or Certificate Transparency. "Not available for this record" on a certificate digest is expected for precertificates. The SPKI digest is always present, which is why it is the recommended pin.
- **`projects sign --dry-run` and `--verbose` print the signed token** (`data.jws` with `--output json`). It is not secret: the identical token is served from the public CDN once published. If signing fails, the previously published configuration stays active.
- **Signing an unchanged configuration is rejected.** The API answers an HTTP 400 error (exit code 2), reported from a working deployment and not in the documentation. Sign only when a staging command changed something: compare the configuration version before and after (`projects get`), or read `upsert`'s `action` (`added` and `updated` both change the version) and `cleanup`'s `data.removed_pins`.
- **`projects jws`** has `--verify`, `--decode`, and `--output-file`. It exits 0 with empty output when nothing is published yet, exits 8 when verification fails, and exits 7 when it cannot write the file.
- **The API token is user-scoped and can expire.** Unless credentials come from the environment, the CLI stores what `configure` is given under `~/.trustpin/`. Remove that directory at the end of a job on a persistent or shared machine.
- **Global flags:** `--verbose`, `--debug`, `--log-http`, and `--version`. Use `--verbose --log-http` to diagnose a lookup or an API error.
