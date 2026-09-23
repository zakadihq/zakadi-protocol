import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { URL, fileURLToPath } from "node:url";
import {
  validateAttestMsg,
  validateClientMsg,
  validateServerMsg,
} from "../dist/index.js";
import { loadVectors, schemasDir, vectorsDir } from "../dist/vectors.js";

// The repository root, on the commit the package is built from.
const repo = fileURLToPath(new URL("../../../", import.meta.url));
const tree = (root) =>
  readdirSync(root, { recursive: true })
    .filter((f) => statSync(join(root, f)).isFile())
    .sort();
const count = (dir, suffix) =>
  tree(join(repo, "vectors", dir)).filter((f) => f.endsWith(suffix)).length;
const counts = {
  framing: count("framing", ".json"),
  chain: count("chain", ".json"),
  sessions: count("sessions", ".jsonl"),
  messages: count("messages", ".json"),
};
const vectors = loadVectors();

test(`loadVectors returns ${counts.framing} framing cases, ${counts.chain} chain cases, ${counts.sessions} transcripts and ${counts.messages} message vectors, the file counts under vectors/`, () => {
  assert.equal(vectors.framing.length, counts.framing);
  assert.equal(vectors.chain.length, counts.chain);
  assert.equal(vectors.sessions.length, counts.sessions);
  assert.equal(vectors.messages.length, counts.messages);
  for (const c of vectors.framing) {
    assert.match(c.hex, /^([0-9a-f]{2})*$/, c.name);
    assert.notEqual("expect" in c, "error" in c, c.name);
  }
  for (const c of vectors.chain) {
    assert.equal(c.attest.chain, c.messages.at(-1)?.chain_after ?? c.h0);
    assert.ok(validateAttestMsg(c.attest), c.name);
  }
  for (const s of vectors.sessions) {
    assert.equal(s.meta.protocol, "zakadi.v1", s.meta.name);
    assert.ok("close" in s.lines.at(-1), s.meta.name);
    for (const line of s.lines.filter((l) => "msg" in l)) {
      const valid = line.dir === "c2s" ? validateClientMsg : validateServerMsg;
      assert.ok(valid(line.msg), `${s.meta.name} at ${line.t_ms} ms`);
    }
  }
});

test("schemasDir and vectorsDir hold exact copies of schemas/v1 and vectors", () => {
  assert.deepEqual(readdirSync(schemasDir()), ["v1"]);
  for (const [shipped, source] of [
    [join(schemasDir(), "v1"), join(repo, "schemas", "v1")],
    [vectorsDir(), join(repo, "vectors")],
  ]) {
    assert.deepEqual(tree(shipped), tree(source));
    for (const f of tree(source)) {
      const same = readFileSync(join(shipped, f)).equals(
        readFileSync(join(source, f)),
      );
      assert.ok(same, f);
    }
  }
});
