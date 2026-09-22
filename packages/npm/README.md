# @zakadi/protocol

Shared protocol types and constants for the Zakadi face-liveness SDKs. Zakadi is an active face liveness check delivered as a short automated video call: the client is a thin capture-and-display shell, one WebSocket session carries continuous encoded video and audio, and all perception runs on the server.

This package holds the values every Zakadi client and server agree on: session states, SDK error codes, terminal states, WebSocket close codes, challenge kinds and the protocol version, with TypeScript types for each. The web, React, Angular and React Native packages depend on it. It contains no networking, no camera code and no UI.

Status: pre-release. Contents track the Zakadi protocol specification; nothing is stable before 1.0.

Links: https://zakadi.dev (documentation), https://github.com/mosesgameli/zakadi-protocol (source).
