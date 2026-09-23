# zakadi-protocol

The Zakadi wire protocol `zakadi.v1`: the machine-readable source of truth that every SDK and the ingest edge conform to. The normative text is `spec/01-protocol.md` in the `zakadi` repository; a mismatch between that text and this repository is a bug here.

## Contents

- `schemas/v1/` - JSON Schemas (draft 2020-12) for every control message, one file per message type under `client/` and `server/`, the direction aggregates `client.schema.json` and `server.schema.json`, shared definitions in `common.schema.json`, and the schemas of the vector files themselves. Unknown message types and unknown fields are valid on the wire and must be ignored; the schemas validate known types only.
- `vectors/` - conformance vectors: message instances (valid and invalid), binary framing cases with `.bin` files, hash-chain cases, and session transcripts for fake-server and client-simulator harnesses. See `vectors/README.md`.
- `conformance/` - the uv-managed Python reference implementation (framing, hash chain), the generator that writes `schemas/` and `vectors/` deterministically, and the checker. See `conformance/README.md`.
- `packages/npm/` - `@zakadi/protocol` (TypeScript constants and types); `packages/npm-zakadi/` - the unscoped `zakadi` name holder with the same content.

## Using the vectors in an SDK

Run every file under `vectors/` in your test suite: decode each framing case and compare the header and payload (or the error code); validate every message instance against the schema of its type and assert the `invalid-*` ones fail; recompute each chain case from `session_id` and `jti` and compare every `chain_after`; replay the `s2c` lines of each transcript and assert your client emits the `c2s` lines in order (or the reverse for a server). Unknown `t` values in a transcript must be ignored, not rejected.

## Releases

Tags `v<version>` run `.github/workflows/release.yml`: tests, then `npm stage publish` of both npm packages through the trusted publisher (no token, no 2FA in CI). A staged version is not public until a maintainer runs `npm stage approve <stage-id>` (2FA prompt); `npm stage list <package>` shows pending stage ids. Versions are permanent once approved.

CI (`ci.yml`) runs the conformance unit tests, regenerates the vectors and fails on any diff, runs the checker, and runs the npm package tests.

## Licence

Zakadi SDKs and client libraries are open source under the Apache License 2.0 (see `LICENSE`; the `NOTICE` file reserves the Zakadi trademarks). They are clients for the Zakadi service, which is proprietary; using it requires an account and acceptance of the Zakadi Terms of Service. Zakadi and the Zakadi logo are trademarks and are not covered by the Apache licence.
