/**
 * The Node-only entry `@zakadi/protocol/vectors`: where the package keeps its
 * copies of `schemas/v1/` and `vectors/` from the zakadi-protocol repository, and
 * a loader that parses the conformance vectors for a test suite.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { AttestMsg, ClientMsg, ServerMsg } from "./generated/messages.js";

/** Absolute path of the shipped `schemas/` directory, which holds `v1/`. */
export function schemasDir(): string {
  return fileURLToPath(new URL("../schemas", import.meta.url));
}

/** Absolute path of the shipped `vectors/` directory. */
export function vectorsDir(): string {
  return fileURLToPath(new URL("../vectors", import.meta.url));
}

/** The header fields a framing case decodes to. */
export interface FramingHeader {
  ver: number;
  type: number;
  keyframe: boolean;
  param_sets: boolean;
  rung_changed: boolean;
  rung: number;
  seq: number;
  pts_ms: number;
}

/**
 * A `framing/*.json` case: one binary media message as hex, with either what it
 * decodes to (`expect`) or the error code decoding must report (`error`).
 */
export interface FramingCase {
  name: string;
  description?: string;
  hex: string;
  expect?: {
    header: FramingHeader;
    payload_hex: string;
    probe_send_time_us?: number;
    audio_batch?: { pts_delta_ms: number; packet_hex: string }[];
  };
  error?: string;
}

/**
 * A `chain/*.json` case: the hash chain over a synthetic media sequence, with H0,
 * the chain after every message and the resulting `attest` message.
 */
export interface ChainCase {
  name: string;
  description?: string;
  session_id: string;
  jti: string;
  token?: string;
  h0: string;
  messages: { hex: string; chained: boolean; chain_after: string }[];
  attest: AttestMsg;
}

/**
 * A `messages/<direction>/<type>/*.json` instance: a `valid*.json` one must pass
 * the schema of its type and its direction aggregate, an `invalid-*.json` one must
 * fail both.
 */
export interface MessageCase {
  direction: "client" | "server";
  /** The message type, the `t` its schema fixes. */
  type: string;
  /** The file name without `.json`. */
  name: string;
  valid: boolean;
  instance: unknown;
}

/** A transcript line after the meta line: a message, a media summary or the close. */
export type TranscriptLine =
  | { t_ms: number; dir: "c2s"; msg: ClientMsg }
  | { t_ms: number; dir: "s2c"; msg: ServerMsg }
  | {
      t_ms: number;
      dir: "c2s";
      media: {
        type: number;
        seq: number;
        pts_ms: number;
        rung: number;
        keyframe?: boolean;
        param_sets?: boolean;
        rung_changed?: boolean;
        bytes: number;
      };
    }
  | { t_ms: number; dir: "s2c"; close: { code: number; reason?: string } };

/** A `sessions/*.jsonl` transcript: its meta line, then every other line in order. */
export interface Transcript {
  meta: {
    name: string;
    protocol: string;
    session_id: string;
    jti: string;
    description?: string;
    expect?: Record<string, unknown>;
  };
  lines: TranscriptLine[];
}

/** Every conformance vector the package ships, each list in file-name order. */
export interface Vectors {
  framing: FramingCase[];
  chain: ChainCase[];
  messages: MessageCase[];
  sessions: Transcript[];
}

/** Parses the framing, chain, message and transcript cases under vectorsDir(). */
export function loadVectors(): Vectors {
  const root = vectorsDir();
  const read = (...path: string[]) => readFileSync(join(root, ...path), "utf8");
  const list = (dir: string, suffix: string) =>
    readdirSync(join(root, dir))
      .filter((name) => name.endsWith(suffix))
      .sort();

  const messages: MessageCase[] = [];
  for (const direction of ["client", "server"] as const) {
    const dir = join("messages", direction);
    const types = readdirSync(join(root, dir), { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort();
    for (const type of types) {
      for (const file of list(join(dir, type), ".json")) {
        const name = file.slice(0, -".json".length);
        if (!/^(valid|invalid-)/.test(name)) {
          throw new Error(`${dir}/${type}/${file}: neither valid nor invalid`);
        }
        const instance: unknown = JSON.parse(read(dir, type, file));
        messages.push({
          direction,
          type,
          name,
          valid: name.startsWith("valid"),
          instance,
        });
      }
    }
  }

  const sessions = list("sessions", ".jsonl").map((file): Transcript => {
    const rows = read("sessions", file)
      .split("\n")
      .filter((row) => row.trim() !== "")
      .map((row) => JSON.parse(row));
    const [first, ...lines] = rows;
    if (!first?.meta) throw new Error(`sessions/${file}: no meta line first`);
    return { meta: first.meta, lines };
  });

  return {
    framing: list("framing", ".json").map(
      (file) => JSON.parse(read("framing", file)) as FramingCase,
    ),
    chain: list("chain", ".json").map(
      (file) => JSON.parse(read("chain", file)) as ChainCase,
    ),
    messages,
    sessions,
  };
}
