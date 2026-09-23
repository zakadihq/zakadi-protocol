import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import { join } from "node:path";
import { URL, fileURLToPath } from "node:url";
import ts from "typescript";
import * as protocol from "../dist/index.js";
import { loadVectors, schemasDir } from "../dist/vectors.js";

// Every message type under schemas/v1/client and schemas/v1/server, with the name
// the package exports for it: HelloMsg for `hello`, and the direction as a prefix
// for a type both directions send (ClientPingMsg, ServerPingMsg).
const pascal = (s) =>
  s
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join("");
const schemaTypes = ["client", "server"].flatMap((direction) =>
  readdirSync(join(schemasDir(), "v1", direction)).map((file) => ({
    direction,
    type: file.replace(/\.schema\.json$/, ""),
  })),
);
const both = (type) => schemaTypes.filter((s) => s.type === type).length > 1;
const typeName = (direction, type) =>
  `${both(type) ? pascal(direction) : ""}${pascal(type)}Msg`;
const unionName = (direction) => `${pascal(direction)}Msg`;
const { messages } = loadVectors();

// Type-checks a module in test/ against the built declarations, with the
// package's compiler settings and no Node types, and returns the errors.
function typeErrors(source) {
  const file = fileURLToPath(new URL("./types-check.ts", import.meta.url));
  const options = {
    strict: true,
    exactOptionalPropertyTypes: true,
    noUncheckedIndexedAccess: true,
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.NodeNext,
    moduleResolution: ts.ModuleResolutionKind.NodeNext,
    noEmit: true,
    skipDefaultLibCheck: true,
    types: [],
  };
  const host = ts.createCompilerHost(options);
  const { fileExists, readFile, getSourceFile } = host;
  host.fileExists = (f) => f === file || fileExists.call(host, f);
  host.readFile = (f) => (f === file ? source : readFile.call(host, f));
  host.getSourceFile = (f, language, ...rest) =>
    f === file
      ? ts.createSourceFile(f, source, language)
      : getSourceFile.call(host, f, language, ...rest);
  const program = ts.createProgram([file], options, host);
  return ts.getPreEmitDiagnostics(program).map((d) => {
    const line = d.file?.getLineAndCharacterOfPosition(d.start ?? 0).line;
    const text = ts.flattenDiagnosticMessageText(d.messageText, "\n");
    return `${d.file?.fileName ?? ""}:${line === undefined ? "" : line + 1} ${text}`;
  });
}

test("a type is exported for every message type and both unions, and a valid instance of each compiles", () => {
  const valid = messages.filter((c) => c.valid);
  const typed = new Set(valid.map((c) => typeName(c.direction, c.type)));
  assert.deepEqual(
    [...typed].sort(),
    schemaTypes.map((s) => typeName(s.direction, s.type)).sort(),
    "every message type has a valid vector",
  );
  const hello = valid.find((c) => c.type === "hello").instance;
  const action = valid.find(
    (c) => c.type === "action" && c.instance.kind === "head_turn",
  ).instance;
  const lines = [
    'import * as P from "../dist/index.js";',
    "declare const input: unknown;",
    ...valid.flatMap((c, i) => [
      `export const m${i}: P.${typeName(c.direction, c.type)} = ${JSON.stringify(c.instance)};`,
      `export const u${i}: P.${unionName(c.direction)} = ${JSON.stringify(c.instance)};`,
    ]),
    // Each validator narrows to its own type and to no other.
    ...[
      ...schemaTypes.map((s) => typeName(s.direction, s.type)),
      ...["client", "server"].map(unionName),
    ].flatMap((name) => [
      `if (P.validate${name}(input)) {`,
      `  const ok: P.${name} = input;`,
      "  // @ts-expect-error a validator narrows to its own type",
      `  const no: P.${name === "HelloMsg" ? "ReadyMsg" : "HelloMsg"} = input;`,
      "}",
    ]),
    "// @ts-expect-error hello requires consent",
    `export const x1: P.HelloMsg = ${JSON.stringify({ ...hello, consent: undefined })};`,
    "// @ts-expect-error a head turn takes head-turn params",
    `export const x2: P.ActionMsg = ${JSON.stringify({ ...action, params: { count: 2, hand: "left", placement: "beside_face" } })};`,
    "// @ts-expect-error an unknown t is not a server message",
    'export const x3: P.ServerMsg = { t: "unknown" };',
    "export type Kept = [P.SessionState, P.ErrorCode, P.TerminalState, P.EndOutcome, P.EndReason, P.CloseCode, P.ChallengeKind];",
  ];
  assert.deepEqual(typeErrors(lines.join("\n")), []);
});

test("the validators of every message type and both aggregates pass every valid*.json and fail every invalid-*.json", () => {
  assert.ok(messages.some((c) => c.valid) && messages.some((c) => !c.valid));
  for (const c of messages) {
    const label = `messages/${c.direction}/${c.type}/${c.name}.json`;
    const own = protocol[`validate${typeName(c.direction, c.type)}`];
    const aggregate = protocol[`validate${unionName(c.direction)}`];
    assert.equal(own(c.instance), c.valid, label);
    assert.equal(own.errors === null, c.valid, `${label}: errors`);
    assert.equal(aggregate(c.instance), c.valid, `${label}: aggregate`);
  }
});
