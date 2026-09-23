# @zakadi/protocol

The Zakadi wire protocol `zakadi.v1` for the face-liveness SDKs. Zakadi is an active face liveness check delivered as a short automated video call: the client is a thin capture-and-display shell, one WebSocket session carries continuous encoded video and audio, and all perception runs on the server.

Each version of this package pins one revision of the protocol: an SDK that installs `@zakadi/protocol` at an exact version gets the schemas, message types, validators and conformance vectors of that revision, built from the same commit of https://github.com/zakadihq/zakadi-protocol. The web, React, Angular and React Native packages depend on it. It has no runtime dependencies and contains no networking, no camera code and no UI.

Status: pre-release. Contents track the Zakadi protocol specification; nothing is stable before 1.0.

## What it ships

- **Constants** every Zakadi client and server agree on: session states, SDK error codes, terminal states, WebSocket close codes, challenge kinds and the protocol version, with a TypeScript type for each.
- **Message types**, generated from the JSON Schemas: one per message type, named after its `t` (`HelloMsg`, `ConfigMsg`, `ReadyMsg`, `ActionMsg`, ...), with the direction as a prefix for the two types both directions send (`ClientPingMsg`, `ClientPongMsg`, `ServerPingMsg`, `ServerPongMsg`), and the unions `ClientMsg` and `ServerMsg`. `ActionMsg` is discriminated by `kind`, so `params` is typed for each challenge. A type lists the fields its schema names; the protocol lets receivers ignore any other.
- **Validators**, generated at build time with Ajv's standalone mode, so nothing of Ajv ships: `validateHelloMsg` and one per message type, plus `validateClientMsg` and `validateServerMsg` for the direction aggregates. Each is a type guard over a parsed JSON value; after a call, its `errors` property lists the violations, or is null. The aggregates accept known message types only, while the protocol requires unknown types to be ignored, so a client reads `t` before treating a failure as an error.
- **`schemas/v1/` and `vectors/`**: copies of the JSON Schemas (draft 2020-12) and of the conformance vectors: framing, hash-chain, message and session-transcript cases.
- **`@zakadi/protocol/vectors`**, for Node only: `schemasDir()` and `vectorsDir()` return the absolute paths of the shipped `schemas/` and `vectors/` directories, and `loadVectors()` parses the framing, chain, message and transcript cases for a test suite.

```ts
import assert from "node:assert/strict";
import { validateServerMsg } from "@zakadi/protocol";
import { loadVectors } from "@zakadi/protocol/vectors";

for (const c of loadVectors().messages) {
  if (c.direction === "server") {
    assert.equal(validateServerMsg(c.instance), c.valid, c.name);
  }
}
```

Links: https://zakadi.dev (documentation), https://github.com/zakadihq/zakadi-protocol (source).

## Licence

Zakadi SDKs and client libraries are open source under the Apache License 2.0 (see `LICENSE`; the `NOTICE` file reserves the Zakadi trademarks). They are clients for the Zakadi service, which is proprietary; using it requires an account and acceptance of the Zakadi Terms of Service. Zakadi and the Zakadi logo are trademarks and are not covered by the Apache licence.
