# Verifying tokens in the API

Source: https://docs.trustpin.cloud/attestation/backend and /attestation/gateways. Use this when the user wants their backend, or an API gateway, to check the `TrustPin-Attestation` header.

## The token

A JWT signed by the user's verifier with ES256. Header: `alg: ES256`, `typ: trustpin-attest+jwt`, `kid`.

| Claim | Meaning |
|---|---|
| `iss` | The verifier's issuer: by default `tprn::attest::<org id>::<project id>`, or its public URL when discovery is on |
| `aud` | By default `tprn::project::<org id>::<project id>` |
| `sub` | The device key. It changes on reinstall, reset or key replacement: **not** a device or user identifier |
| `iat`, `exp`, `jti` | Times and a random id |
| `bind` | Only when the app bound the token: `base64url(SHA-256(bound value))`, unpadded |
| `tp.prj` | The project, `tprn::project::<org id>::<project id>` |
| `tp.plat` | `apple`, `android`, or `debug` |
| `tp.app` | `<teamId>.<bundleId>` on Apple, the package name on Android |
| `tp.ev` | An **array**: `app_attest`, `key_attestation`, `play_integrity`, `debug_token` |
| `tp.env` | `production`, `development` (Xcode-run builds), or `debug` |
| `tp.pv` | The policy version |
| `tp.mode`, `tp.result`, `tp.reasons` | `monitor` or `enforce`, `pass` or `fail`, and the reason codes |

## Verification steps

1. Fetch and cache `GET <verifier>/.well-known/jwks.json`. Refetch on an unknown `kid`, at most once every 30 s, with a 5 s timeout. Use the JWT library's remote JWKS support rather than writing a cache.
2. Accept only `alg` `ES256` and `typ` `trustpin-attest+jwt`. The type check also rejects key certificates and any other JWT signed by the same keys.
3. Check the signature with the key named by `kid`.
4. Check `iss`, `aud` and `exp`, with at most 60 seconds of clock skew, and that `tp.prj` equals the project. Refuse a token without `tp.prj`.
5. With binding: require `bind` and compare it with `base64url(SHA-256(<agreed value>))`, unpadded, over the value exactly as received. With the SDKs' `bindToHeader("Authorization")`, the agreed value is the request's `Authorization` header. With **Require token binding** on, refuse a token without `bind`.
6. Refuse `tp.env == "debug"` outside development environments.
7. Apply the mode rules below.

Write this in the API's existing language and JWT library (for example `jose` in Node.js, `PyJWT` with `PyJWKClient` in Python, `golang-jwt` with a JWKS client in Go, Nimbus in Java). Put it in the existing auth middleware, next to the session check. Read the verifier URL, issuer, audience and project from configuration, not from code.

## Monitor and enforce

| Policy mode | Tokens | The API should |
|---|---|---|
| Monitor | `tp.result` may be `fail`, with `tp.reasons` | Log result and reasons, and allow the request |
| Enforce | New tokens always carry `pass`; a failing device gets none. Tokens issued before the switch keep `fail` until they expire | Refuse requests without a valid token on protected endpoints. For an immediate cut-off, also refuse `tp.result == "fail"` |

## Requests without the header

The SDKs never block the app's requests, so these arrive: old app versions, unsupported devices, failures, requests sent before a token was ready. Decide per endpoint with the user: refuse sensitive operations, rate-limit harder, or flag the session. Do not refuse everything by default while the policy is in monitor mode.

## Assertions for sensitive operations

From SDK 7.1 and verifier contract version 2, a request for one operation can carry, next to the token:

```text
TrustPin-Assertion: <base64url(clientData)>.<base64url(signature)>
```

To verify, compute the API's own SHA-256 of the same bytes the app digested (usually the request body) and call the verifier:

```http
POST <verifier>/v1/assertion
Content-Type: application/json

{ "token": "<TrustPin-Attestation value>", "assertion": "<TrustPin-Assertion value>", "payload": "<base64url(SHA-256 digest)>" }
```

A `200` returns the token's claims with the verified assertion, and the verifier checks the token itself. Anything else (`403 attestation_failed` with `assertion_invalid`, `payload_mismatch`, `key_mismatch` or `counter_invalid`; `401 invalid_challenge` for an expired or reused nonce) means the operation must be refused. Call the verifier from the backend over its private route, with a short timeout, and refuse the operation when the call fails.

## At a gateway

The docs offer tested recipes for nginx, Envoy, Kong, Cloudflare Workers and AWS API Gateway (HTTP API): https://docs.trustpin.cloud/attestation/gateways. They enforce whatever the policy's mode, so during monitor check tokens in the API instead. A gateway's built-in JWT authorizer checks the signature, `iss`, `aud` and `exp`, but not `typ`, `tp.prj`, debug tokens or the binding: use a recipe, or add those checks in the API.

## Do not

- Do not use `sub` as a user or device identifier, or as a rate-limit key that should survive a reinstall.
- Do not log the token, the assertion, or the bound value. Log `tp.result`, `tp.reasons`, `tp.plat`, `tp.app`, and a request id.
- Do not accept `alg: none`, HS256 or keys from the token header. Only the JWKS.
