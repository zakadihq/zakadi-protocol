# zakadi-conformance

Reference implementation and conformance checker for the Zakadi wire protocol `zakadi.v1`. It generates the JSON Schemas and test vectors in this repository from one source of truth and verifies them; every SDK and the ingest edge run the same vectors.

Run with uv from this directory:

- `uv run zakadi-conformance generate` regenerates `../schemas` and `../vectors` (deterministic; the diff should be empty unless the protocol changed).
- `uv run zakadi-conformance check` validates the schemas against the 2020-12 meta-schema, the message vectors (valid must pass, invalid must fail), the framing vectors, the hash-chain vectors and the session transcripts, as listed below.
- `uv run pytest` runs the unit tests of the reference implementation and of the checker's rules.

## The test key

`src/zakadi_conformance/test-key.private.jwk.json` is the private JWK of a P-256 key made for the vectors alone (kid `zakadi-vectors-test-1`). `generate` signs every vector token with it (ES256, deterministic per RFC 6979, so the tree is byte-identical on every run) and writes only its public half to `../vectors/keys/jwks.json`. The private JWK stays in this directory: neither the npm package (a copy of `schemas/v1/` and `vectors/`) nor the signed release archive (`schemas/`, `vectors/`, `LICENSE`, `NOTICE`) contains it. It is a test key; nothing outside tests may trust it. Signing and verification use `cryptography`.

## What `check` verifies

- Every vector token (each `hello` token and each chain case's token) verifies with ES256 against `vectors/keys/jwks.json`, carries the claims of `spec/02-api.md` 2.2 with `exp` 300 s after `iat`, and names the vectors' session: in a transcript its `sub`, `jti` and `nonce` equal the meta `session_id`, the meta `jti` and `ready.attest_nonce`, elsewhere the session of the `ready` example or of the chain case.
- Every session id is `ses_` and a ULID, and each `ready` carries its transcript's id.
- The attestation examples carry the `request_hash` of `spec/01-protocol.md` 1.4 over the session id and `attest_nonce`, which the App Attest token's `client_data_hash` repeats.
- In every transcript: `ping` `p1` follows `ready` at once; every ping has one pong; every `say` has one `audio_state` started and one ended; the server never leaves more than 1200 ms without a cue while the phase is framing, action or listening (`spec/03-backend-services.md` 3.4); FRAMING past its 15 s cap has a coaching turn and ends 15 s later with `end` `aborted` `attempts_exhausted`, `retry` true (`spec/01-protocol.md` 1.6); probes are summarised at rung 0 and pts 0.
- In a transcript whose `meta.expect.media` is `continuous`: every video and audio message from `config` to `end`, server pings every 1 s, `stats` every `stats_interval_ms`, `attest` every `attest_interval_ms` of video pts, and each `attest` naming the seqs and the chain of the media before it, computed over zero-filled payloads.

Not legal or security advice: the vectors prove that an implementation follows the wire format; they do not prove that a liveness system is secure.
