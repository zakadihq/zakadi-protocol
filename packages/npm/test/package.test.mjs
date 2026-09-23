import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import * as protocol from "../dist/index.js";

const pkg = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf8"),
);

// The module specifiers a built file imports or re-exports.
function specifiers(url) {
  const source = readFileSync(url, "utf8");
  return [
    ...source.matchAll(
      /^\s*(?:import|export)\b[^;]*?\bfrom\s*["']([^"']+)["']/gm,
    ),
    ...source.matchAll(/^\s*import\s*["']([^"']+)["']/gm),
    ...source.matchAll(/\b(?:import|require)\s*\(\s*["']([^"']+)["']/g),
  ].map((m) => m[1]);
}

test("the package declares no runtime dependency and its main entry imports no Node built-in", () => {
  for (const field of [
    "dependencies",
    "peerDependencies",
    "optionalDependencies",
    "bundleDependencies",
    "bundledDependencies",
  ]) {
    assert.equal(pkg[field], undefined, field);
  }
  const seen = new Set();
  const queue = [new URL("../dist/index.js", import.meta.url).href];
  while (queue.length) {
    const url = queue.pop();
    if (seen.has(url)) continue;
    seen.add(url);
    for (const specifier of specifiers(new URL(url))) {
      assert.match(specifier, /^\.\.?\//, `${url} imports ${specifier}`);
      queue.push(new URL(specifier, url).href);
    }
  }
  for (const dir of ["client", "server"]) {
    const validators = `../dist/generated/${dir}-validators.js`;
    assert.ok(seen.has(new URL(validators, import.meta.url).href), validators);
  }
  const vectors = new URL("../dist/vectors.js", import.meta.url);
  for (const specifier of specifiers(vectors)) {
    assert.match(specifier, /^node:/, `the vectors entry imports ${specifier}`);
  }
});

test("every export of 0.0.1 remains", () => {
  for (const name of [
    "ZAKADI_SUBPROTOCOL",
    "SESSION_STATES",
    "ERROR_CODES",
    "isErrorCode",
    "TERMINAL_STATES",
    "END_OUTCOMES",
    "END_REASONS",
    "terminalStateForEnd",
    "CloseCode",
    "CHALLENGE_KINDS",
  ]) {
    assert.ok(name in protocol, name);
  }
});
