#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";

const [path, selectedCsv, calcMode = "calc"] = process.argv.slice(2);
if (!path || selectedCsv === undefined || !["calc", "no-calc"].includes(calcMode)) {
  console.error("usage: node tools/test_selected_statistics_wasm.mjs <exactscope.wasm> <op[,op...]|-> [calc|no-calc]");
  process.exit(2);
}

const OPERATIONS = new Map([
  ["stats.sum", { id: 1, request: '{"op":"stats.sum","a":[["1","2","3"]]}' }],
  ["stats.mean", { id: 2, request: '{"op":"stats.mean","a":[["1","2","3"]]}' }],
  ["stats.mean.weighted", { id: 3, request: '{"op":"stats.mean.weighted","a":[["1","3"],["1","1"]]}' }],
  ["stats.var.pop", { id: 4, request: '{"op":"stats.var.pop","a":[["1","2","3"]]}' }],
  ["stats.var.sample", { id: 5, request: '{"op":"stats.var.sample","a":[["1","2","3"]]}' }],
  ["stats.sd.pop", { id: 6, request: '{"op":"stats.sd.pop","a":[["1","2","3"]]}' }],
  ["stats.sd.sample", { id: 7, request: '{"op":"stats.sd.sample","a":[["1","2","3"]]}' }],
  ["stats.cov.pop", { id: 8, request: '{"op":"stats.cov.pop","a":[["1","2","3"],["2","4","6"]]}' }],
  ["stats.cov.sample", { id: 9, request: '{"op":"stats.cov.sample","a":[["1","2","3"],["2","4","6"]]}' }],
  ["stats.corr.pearson", { id: 10, request: '{"op":"stats.corr.pearson","a":[["1","2","3"],["2","4","6"]]}' }],
  ["stats.regression.linear", { id: 11, request: '{"op":"stats.regression.linear","a":[["1","2","3"],["3","5","7"]]}' }],
]);

const selected = new Set(selectedCsv === "-" ? [] : selectedCsv.split(",").filter(Boolean));
if ([...selected].some(op => !OPERATIONS.has(op))) {
  throw new Error(`unknown selected operation set: ${selectedCsv}`);
}

const bytes = fs.readFileSync(path);
const module = new WebAssembly.Module(bytes);
if (WebAssembly.Module.imports(module).length !== 0) throw new Error("imports forbidden");
const xs = new WebAssembly.Instance(module, {}).exports;
const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });
const alignment = xs.xs_wasm_memory_alignment();

function alignUp(value, align) {
  return Math.ceil(value / align) * align;
}

function ensureMemory(end) {
  if (end <= xs.memory.buffer.byteLength) return;
  xs.memory.grow(Math.ceil((end - xs.memory.buffer.byteLength) / 65536));
}

function callJson(text) {
  const input = encoder.encode(text);
  const reserved = xs.xs_wasm_reserved_end();
  const inputOffset = alignUp(reserved, alignment);
  const outputOffset = alignUp(inputOffset + input.length, alignment);
  const metaOffset = alignUp(outputOffset + 512, alignment);
  ensureMemory(metaOffset + 16);
  new Uint8Array(xs.memory.buffer).set(input, inputOffset);
  const view = new DataView(xs.memory.buffer);
  view.setUint32(metaOffset, 16, true);
  const returned = xs.xs_wire_request(1, inputOffset, input.length, outputOffset, 512, metaOffset);
  const status = view.getUint16(metaOffset + 4, true);
  const flags = view.getUint16(metaOffset + 6, true);
  const written = view.getUint32(metaOffset + 8, true);
  const response = flags & 1
    ? decoder.decode(new Uint8Array(xs.memory.buffer, outputOffset, written))
    : "";
  return { returned, status, response };
}

const calc = callJson('{"p":[{"o":"mul","a":["6","7"]}]}');
if (calcMode === "calc") {
  if (calc.status !== 0 || !calc.response.includes('"v":"42"')) {
    throw new Error(`xs_calc regression: ${JSON.stringify(calc)}`);
  }
} else if (calc.status === 0 || calc.response.includes('"v":')) {
  throw new Error(`xs_calc unexpectedly reachable: ${JSON.stringify(calc)}`);
}

for (const [op, spec] of OPERATIONS) {
  const result = callJson(spec.request);
  if (selected.has(op)) {
    if (result.returned !== 0 || result.status !== 0 || !result.response.includes('"v":')) {
      throw new Error(`selected operation failed ${op}: ${JSON.stringify(result)}`);
    }
  } else if (result.status === 0 || result.response.includes('"v":')) {
    throw new Error(`excluded operation became reachable ${op}: ${JSON.stringify(result)}`);
  }
}

for (const request of [
  '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}',
  '{"q":"mean","n":3}',
]) {
  const result = callJson(request);
  if (result.status === 0 || result.response.includes('"v":')) {
    throw new Error(`non-selected serving path became reachable: ${request}`);
  }
}

{
  const reserved = xs.xs_wasm_reserved_end();
  const xOffset = alignUp(reserved, alignment);
  const yOffset = alignUp(xOffset + 3 * 16, alignment);
  const resultOffset = alignUp(yOffset + 3 * 16, alignment);
  ensureMemory(resultOffset + 112);
  const view = new DataView(xs.memory.buffer);
  for (const [offset, values] of [[xOffset, [1, 2, 3]], [yOffset, [2, 4, 6]]]) {
    values.forEach((value, index) => {
      const base = offset + index * 16;
      view.setBigInt64(base, BigInt(value), true);
      view.setInt8(base + 8, 0);
      view.setUint8(base + 9, 0);
      view.setUint16(base + 10, 0, true);
      view.setUint32(base + 12, 0, true);
    });
  }
  for (const [op, spec] of OPERATIONS) {
    if (selected.has(op)) continue;
    new Uint8Array(xs.memory.buffer, resultOffset, 112).fill(0);
    view.setUint32(resultOffset, 112, true);
    const returned = xs.xs_wasm_eval_statistics(spec.id, xOffset, 3, yOffset, 3, resultOffset);
    const status = view.getUint16(resultOffset + 4, true);
    const valueCount = view.getUint16(resultOffset + 8, true);
    if (returned === 0 || status === 0 || valueCount !== 0) {
      throw new Error(`excluded direct operation ${op}/${spec.id} became reachable`);
    }
  }
}

{
  const input = new Uint8Array([0xa0]);
  const reserved = xs.xs_wasm_reserved_end();
  const inputOffset = alignUp(reserved, alignment);
  const outputOffset = alignUp(inputOffset + input.length, alignment);
  const metaOffset = alignUp(outputOffset + 32, alignment);
  ensureMemory(metaOffset + 16);
  new Uint8Array(xs.memory.buffer).set(input, inputOffset);
  const view = new DataView(xs.memory.buffer);
  view.setUint32(metaOffset, 16, true);
  xs.xs_wire_request(2, inputOffset, input.length, outputOffset, 32, metaOffset);
  if (view.getUint16(metaOffset + 4, true) === 0) {
    throw new Error("TinyWire unexpectedly enabled in selected specialization");
  }
}

console.log(
  `PASS selected Statistics Wasm ops=${[...selected].sort().join(",")} bytes=${bytes.length} imports=0 memory=${xs.memory.buffer.byteLength}`,
);
