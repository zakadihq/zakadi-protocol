# zakadi-protocol

The Zakadi wire protocol (`zakadi.v1`): the source of truth for message schemas, binary framing test vectors, hash-chain vectors, golden media streams and recorded session transcripts that every SDK and the ingest edge run as their conformance suite. The normative text lives in the `zakadi` repository (`spec/01-protocol.md`); this repository will hold the machine-readable artefacts generated from it.

Packages published from here:

- `packages/npm/` - `@zakadi/protocol` (TypeScript): shared protocol constants and types for the web, React, Angular and React Native packages.
- `packages/npm-zakadi/` - `zakadi` (unscoped npm name holder with the same constants; the SDKs are published under `@zakadi/*`).

Status: pre-release.
