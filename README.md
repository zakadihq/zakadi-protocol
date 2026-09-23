# zakadi-protocol

The Zakadi wire protocol `zakadi.v1`: the machine-readable source of truth that every SDK and the ingest edge conform to. The normative text is `spec/01-protocol.md` in the `zakadi` repository; a mismatch between that text and this repository is a bug here.

## Contents

- `schemas/v1/` - JSON Schemas (draft 2020-12) for every control message, one file per message type under `client/` and `server/`, the direction aggregates `client.schema.json` and `server.schema.json`, shared definitions in `common.schema.json`, and the schemas of the vector files themselves. Unknown message types and unknown fields are valid on the wire and must be ignored; the schemas validate known types only.
- `vectors/` - conformance vectors: message instances (valid and invalid), binary framing cases with `.bin` files, hash-chain cases, and session transcripts for fake-server and client-simulator harnesses. See `vectors/README.md`.
- `conformance/` - the uv-managed Python reference implementation (framing, hash chain), the generator that writes `schemas/` and `vectors/` deterministically, and the checker. See `conformance/README.md`.
- `packages/npm/` - `@zakadi/protocol`, the artefact SDKs pin: the protocol constants, a TypeScript type and a standalone validator (no runtime dependency) generated for every message type and both direction aggregates, copies of `schemas/v1/` and `vectors/`, and the Node-only `@zakadi/protocol/vectors` entry that locates and parses them; `npm test` there copies, generates, builds and tests. `packages/npm-zakadi/` - the unscoped `zakadi` name holder with the same constants.

## Using the vectors in an SDK

Run every file under `vectors/` in your test suite: decode each framing case and compare the header and payload (or the error code); validate every message instance against the schema of its type and assert the `invalid-*` ones fail; recompute each chain case from `session_id` and `jti` and compare every `chain_after`; replay the `s2c` lines of each transcript and assert your client emits the `c2s` lines in order (or the reverse for a server). Unknown `t` values in a transcript must be ignored, not rejected.

## Releases

Tags `v<version>` run `.github/workflows/release.yml`, where `<version>` is the tag without its `v`:

- `publish`, after `test`: `npm stage publish` of both npm packages through the trusted publisher (no token, no 2FA in CI), on tags only. A staged version is not public until a maintainer runs `npm stage approve <stage-id>` (2FA prompt); `npm stage list <package>` shows pending stage ids. Versions are permanent once approved.
- `vectors`: regenerates the schemas and vectors and fails on any diff, runs the checker, packs the commit with `git archive`, signs the archive keyless with cosign under the workflow's GitHub OIDC identity, verifies the signature, and attaches two assets to the tag's GitHub release, creating the release when it is missing.

| Asset | Contents |
| --- | --- |
| `zakadi-protocol-vectors-<version>.tar.gz` | `schemas/`, `vectors/`, `LICENSE` and `NOTICE` under `zakadi-protocol-vectors-<version>/`; packing the same commit twice gives byte-identical archives |
| `zakadi-protocol-vectors-<version>.tar.gz.sigstore.json` | its Sigstore bundle: the signature, the signing certificate and the transparency-log proof |

Download both from `https://github.com/zakadihq/zakadi-protocol/releases/download/v<version>/` and verify them with cosign 3:

```sh
cosign verify-blob --bundle zakadi-protocol-vectors-<version>.tar.gz.sigstore.json \
  --certificate-identity https://github.com/zakadihq/zakadi-protocol/.github/workflows/release.yml@refs/tags/v<version> \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  zakadi-protocol-vectors-<version>.tar.gz
```

`Verified OK` means the archive is the one `release.yml` signed while running on the tag `v<version>` of this repository. A `workflow_dispatch` run from a branch packs the short commit sha as `<version>`, signs and verifies under that branch's identity (`release.yml@refs/heads/<branch>`), creates no release and stages no npm package.

Pinning a tag archive by SHA-256 stays supported: the pin proves the bytes, the signature proves who produced them. `v0.1.0` predates the signed archive and has none of these assets; pin its tag archive `https://github.com/zakadihq/zakadi-protocol/archive/refs/tags/v0.1.0.tar.gz` by SHA-256 `de94fc3693659e0016d6eedb7e3b0e7fd688cc6e30247d387fb2eab4175759ba`.

CI (`ci.yml`) runs the conformance unit tests, regenerates the vectors and fails on any diff, runs the checker, and runs the npm package tests.

## Licence

Zakadi SDKs and client libraries are open source under the Apache License 2.0 (see `LICENSE`; the `NOTICE` file reserves the Zakadi trademarks). They are clients for the Zakadi service, which is proprietary; using it requires an account and acceptance of the Zakadi Terms of Service. Zakadi and the Zakadi logo are trademarks and are not covered by the Apache licence.
