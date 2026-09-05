#!/usr/bin/env node

import fs from "node:fs";
import crypto from "node:crypto";

const [wasmPath, corpusPath, domain, outputPath, emptyMode = "require-calls"] = process.argv.slice(2);
if (!wasmPath || !corpusPath || !domain || !["require-calls", "allow-empty"].includes(emptyMode)) {
  throw new Error("usage: check_capability_wasm.mjs <wasm> <corpus> <domain> [evidence.json] [require-calls|allow-empty]");
}
if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(domain)) throw new Error("invalid domain");

const bytes = fs.readFileSync(wasmPath);
const corpus = fs.readFileSync(corpusPath);
const module = await WebAssembly.compile(bytes);
if (WebAssembly.Module.imports(module).length !== 0) throw new Error("imports forbidden");
const xs = (await WebAssembly.instantiate(module, {})).exports;
if (xs.xs_abi_version() !== 0x10000) throw new Error("ABI mismatch");
const initialBytes = xs.memory.buffer.byteLength;
const align = value => Math.ceil(value / xs.xs_wasm_memory_alignment()) * xs.xs_wasm_memory_alignment();
const input = align(xs.xs_wasm_reserved_end());
const output = align(input + 512);
const meta = align(output + 512);
if (meta + 16 > xs.memory.buffer.byteLength) {
  throw new Error("conformance request regions exceed the fixed artifact memory");
}
const memory = new Uint8Array(xs.memory.buffer);
const view = new DataView(xs.memory.buffer);
const corpusText = corpus.toString("utf8").trim();
const rows = corpusText ? corpusText.split(/\r?\n/).map(JSON.parse) : [];
if (rows.length === 0 && emptyMode !== "allow-empty") throw new Error("empty conformance corpus");

const seen = new Set();
const operations = new Set();
const results = [];
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
for (const row of rows) {
  if (!row || typeof row !== "object" || typeof row.id !== "string" || !row.id) {
    throw new Error("invalid conformance row identity");
  }
  if (seen.has(row.id)) throw new Error(`duplicate conformance row id: ${row.id}`);
  seen.add(row.id);
  if (!row.call || typeof row.call !== "object" || typeof row.call.op !== "string") {
    throw new Error(`conformance row has no semantic call: ${row.id}`);
  }
  if (!row.expected || typeof row.expected !== "object" || !Number.isInteger(row.expected.s)) {
    throw new Error(`conformance row has no typed expected response: ${row.id}`);
  }
  operations.add(row.call.op);
  const request = new TextEncoder().encode(JSON.stringify(row.call));
  if (request.length > 512) throw new Error(`unbounded gold: ${row.id}`);
  memory.set(request, input);
  view.setUint32(meta, 16, true);
  const status = xs.xs_wire_request(1, input, request.length, output, 512, meta);
  const length = view.getUint32(meta + 8, true);
  if (length > 512) throw new Error("invalid output length");
  const actual = JSON.parse(new TextDecoder().decode(memory.subarray(output, output + length)));
  if (status !== actual.s || status !== row.expected.s
      || Object.entries(row.expected).some(([key, value]) => !same(actual[key], value))) {
    throw new Error(`gold mismatch ${row.id}: ${JSON.stringify(actual)}`);
  }
  if (status !== 0 && "v" in actual) throw new Error(`numeric failure leaked a value: ${row.id}`);
  if (status === 0 && !("v" in actual)) throw new Error(`successful response has no value: ${row.id}`);
  results.push({ id: row.id, response: actual });
}

const sha256 = value => crypto.createHash("sha256").update(value).digest("hex");
const evidence = {
  format: "exactscope.capability.wasm-conformance",
  format_version: "0.1",
  domain,
  artifact_sha256: sha256(bytes),
  corpus_sha256: sha256(corpus),
  artifact_bytes: bytes.length,
  imports: 0,
  initial_memory_bytes: initialBytes,
  final_memory_bytes: memory.byteLength,
  abi: "1.0",
  runtime: process.version,
  operations: [...operations].sort(),
  checked_calls: results.length,
  results,
};
if (outputPath) fs.writeFileSync(outputPath, JSON.stringify(evidence, null, 2) + "\n", { flag: "wx" });
console.log(`PASS capability Wasm domain=${domain} calls=${results.length} bytes=${bytes.length} imports=0`);
