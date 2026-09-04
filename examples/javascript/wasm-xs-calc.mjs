#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";

const wasmPath = process.argv[2];
if (!wasmPath) {
  console.error("usage: node examples/javascript/wasm-xs-calc.mjs <exactscope_wasm.wasm>");
  process.exit(2);
}

const { instance } = await WebAssembly.instantiate(fs.readFileSync(wasmPath), {});
const xs = instance.exports;
const request = new TextEncoder().encode(
  '{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}',
);
const alignment = xs.xs_wasm_memory_alignment();
const align = (value) => Math.ceil(value / alignment) * alignment;
const inputOffset = align(xs.xs_wasm_reserved_end());
const outputOffset = align(inputOffset + request.length);
const outputCapacity = 512;
const metaOffset = align(outputOffset + outputCapacity);
const requiredBytes = metaOffset + 16;
if (xs.memory.buffer.byteLength < requiredBytes) {
  xs.memory.grow(Math.ceil((requiredBytes - xs.memory.buffer.byteLength) / 65536));
}

const memory = new Uint8Array(xs.memory.buffer);
memory.set(request, inputOffset);
const view = new DataView(xs.memory.buffer);
view.setUint32(metaOffset, 16, true);

const status = xs.xs_wire_request(
  1, // XS_WIRE_FORMAT_TINY_JSON_V1
  inputOffset,
  request.length,
  outputOffset,
  outputCapacity,
  metaOffset,
);
const written = view.getUint32(metaOffset + 8, true);
const response = new TextDecoder().decode(memory.slice(outputOffset, outputOffset + written));

if (status !== 0 || response !== '{"s":0,"v":"16","f":0,"p":"plan-v0.1","r":1}') {
  throw new Error(`xs_calc failed: status=${status} response=${response}`);
}
console.log(response);
