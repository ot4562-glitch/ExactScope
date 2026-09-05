#!/usr/bin/env node
// Executes the same gold corpus through the actual no-import artifact.
import fs from "node:fs";
import crypto from "node:crypto";

const [wasmPath, corpusPath, outputPath] = process.argv.slice(2);
if (!wasmPath || !corpusPath) throw new Error("usage: check_statistics_wasm.mjs <wasm> <corpus> [evidence.json]");
const bytes = fs.readFileSync(wasmPath);
const corpus = fs.readFileSync(corpusPath);
const module = await WebAssembly.compile(bytes);
if (WebAssembly.Module.imports(module).length) throw new Error("imports forbidden");
const xs = (await WebAssembly.instantiate(module, {})).exports;
if (xs.xs_abi_version() !== 0x10000) throw new Error("ABI mismatch");
const initialBytes = xs.memory.buffer.byteLength;
const align = value => Math.ceil(value / xs.xs_wasm_memory_alignment()) * xs.xs_wasm_memory_alignment();
const input = align(xs.xs_wasm_reserved_end());
const output = align(input + 512);
const meta = align(output + 512);
if (xs.memory.buffer.byteLength < meta + 16) xs.memory.grow(Math.ceil((meta + 16 - xs.memory.buffer.byteLength) / 65536));
const memory = new Uint8Array(xs.memory.buffer);
const view = new DataView(xs.memory.buffer);
const rows = corpus.toString("utf8").trim().split(/\r?\n/).map(JSON.parse);
const results = [];
for (const row of rows) {
  if (row.call === null) continue;
  const request = new TextEncoder().encode(JSON.stringify(row.call));
  if (request.length > 512) throw new Error(`unbounded gold: ${row.id}`);
  memory.set(request, input);
  view.setUint32(meta, 16, true);
  const status = xs.xs_wire_request(1, input, request.length, output, 512, meta);
  const length = view.getUint32(meta + 8, true);
  if (length > 512) throw new Error("invalid output length");
  const actual = JSON.parse(new TextDecoder().decode(memory.subarray(output, output + length)));
  if (status !== actual.s || Object.entries(row.expected).some(([k, v]) => actual[k] !== v)) {
    throw new Error(`gold mismatch ${row.id}: ${JSON.stringify(actual)}`);
  }
  if (status !== 0 && "v" in actual) throw new Error("numeric failure");
  results.push({ id: row.id, response: actual });
}
const sha256 = value => crypto.createHash("sha256").update(value).digest("hex");
const evidence = { format: "exactscope.statistics.wasm-conformance", revision: 1,
  artifact_sha256: sha256(bytes), corpus_sha256: sha256(corpus), artifact_bytes: bytes.length,
  imports: 0, initial_memory_bytes: initialBytes, grown_memory_bytes: memory.byteLength,
  abi: "1.0", runtime: process.version, checked_calls: results.length, results };
if (outputPath) fs.writeFileSync(outputPath, JSON.stringify(evidence, null, 2) + "\n", { flag: "wx" });
console.log(`PASS Statistics Wasm calls=${results.length} bytes=${bytes.length} imports=0`);
