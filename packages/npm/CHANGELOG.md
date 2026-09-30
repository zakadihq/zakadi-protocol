# Changelog

All notable changes to `@zakadi/protocol` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `vectors/loop/*.json`, ten control-loop traces of the client's 200 ms loop, and
  `schemas/v1/loop-trace.schema.json`: per-tick queue, drain and encoded rate, server pings,
  `set_rung`, keyframe requests and IDRs on `webcodecs`, `native` and `mediarecorder`, with the
  rungs, the changes of decimation and the floor tick the reference loop yields from them under
  one reading of the floor rule: it breaches on the 15th tick after the step down to rung 4, a
  tick skipped for a keyframe request holding the count. `loadVectors()` does not parse them.

### Changed

- `vectors/sessions/floor-breached.jsonl`: the client's loop ticks every 200 ms from
  `probe_result`, and `bye` `floor_breached` comes on the 15th tick after the step down to rung 4,
  3000 ms after it rather than 3065 ms.

### Fixed

- `schemas/v1/chain-vector.schema.json` describes a chain case's `token` as an ES256 JWS signed
  by the test key of `vectors/keys/jwks.json`, no longer as an unsigned JWT; the README and the
  doc comments of `@zakadi/protocol/vectors` name that JWKS, its kid `zakadi-vectors-test-1`, its
  test-only trust and `vectorsDir()` as where a test reads it, since `loadVectors()` does not
  parse it.

## [0.2.0] - 2026-09-26

### Added

- `vectors/keys/jwks.json`, the public JWKS of the test key (kid `zakadi-vectors-test-1`) that
  signs every vector token.
- `vectors/sessions/framing-timeout.jsonl`, the no-face session: FRAMING passes its 15 s cap, a
  coaching turn follows and `end` `aborted` `attempts_exhausted` with `retry` true comes 15 s
  later, with continuous media, pings, `stats` and `attest` throughout.

### Changed

- Every vector token is an ES256 JWS signed by that key with the claims of the API's
  `client_token`, and every vector names one session id, `ses_` and a ULID, so a server that
  verifies tokens replays the vectors unmodified.
- The transcripts follow `ready` with `ping` `p1`, bracket every `say` with `audio_state` started
  and ended, never leave more than 1.2 s without a cue while framing, acting or listening, keep
  FRAMING's 15 s cap and summarise probes at rung 0; the attestation examples carry the
  `request_hash` of the vectors' session.

## [0.1.0] - 2026-09-23

### Added

- The protocol revision the package is built from: a type generated from the schemas
  for every message (`HelloMsg`, `ReadyMsg`, ...) with the `ClientMsg` and `ServerMsg`
  unions, a standalone validator for every message type and both direction aggregates
  (no runtime dependency), copies of `schemas/v1/` and `vectors/`, and the Node-only
  `@zakadi/protocol/vectors` entry with `schemasDir()`, `vectorsDir()` and
  `loadVectors()`.

### Changed

- Licence: Apache License 2.0 with a NOTICE file (0.0.1 shipped with an
  all-rights-reserved placeholder).

## [0.0.1] - 2026-09-23

### Added

- Initial release: protocol version, session states, SDK error codes, terminal states
  with cues and redial availability, `end` reason mapping, WebSocket close codes and
  challenge kinds from the Zakadi protocol specification.

[Unreleased]: https://github.com/zakadihq/zakadi-protocol/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/zakadihq/zakadi-protocol/releases/tag/v0.2.0
[0.1.0]: https://github.com/zakadihq/zakadi-protocol/releases/tag/v0.1.0
