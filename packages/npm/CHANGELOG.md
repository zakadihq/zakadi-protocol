# Changelog

All notable changes to `@zakadi/protocol` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/zakadihq/zakadi-protocol/commits/main
