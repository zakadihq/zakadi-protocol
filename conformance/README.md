# zakadi-conformance

Reference implementation and conformance checker for the Zakadi wire protocol `zakadi.v1`. It generates the JSON Schemas and test vectors in this repository from one source of truth and verifies them; every SDK and the ingest edge run the same vectors.

Run with uv from this directory:

- `uv run zakadi-conformance generate` regenerates `../schemas` and `../vectors` (deterministic; the diff should be empty unless the protocol changed).
- `uv run zakadi-conformance check` validates the schemas against the 2020-12 meta-schema, the message vectors (valid must pass, invalid must fail), the framing vectors, the hash-chain vectors and the session transcripts.
- `uv run pytest` runs the unit tests of the reference implementation.

Not legal or security advice: the vectors prove that an implementation follows the wire format; they do not prove that a liveness system is secure.
