# @zakadi/protocol

Shared protocol types and constants for the Zakadi face-liveness SDKs. Zakadi is an active face liveness check delivered as a short automated video call: the client is a thin capture-and-display shell, one WebSocket session carries continuous encoded video and audio, and all perception runs on the server.

This package holds the values every Zakadi client and server agree on: session states, SDK error codes, terminal states, WebSocket close codes, challenge kinds and the protocol version, with TypeScript types for each. The web, React, Angular and React Native packages depend on it. It contains no networking, no camera code and no UI.

Status: pre-release. Contents track the Zakadi protocol specification; nothing is stable before 1.0.

Links: https://zakadi.dev (documentation), https://github.com/zakadihq/zakadi-protocol (source).

## Licence

Zakadi SDKs and client libraries are open source under the Apache License 2.0 (see `LICENSE`; the `NOTICE` file reserves the Zakadi trademarks). They are clients for the Zakadi service, which is proprietary; using it requires an account and acceptance of the Zakadi Terms of Service. Zakadi and the Zakadi logo are trademarks and are not covered by the Apache licence.
