#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";

const path = process.argv[2];
if (!path) {
  console.error("usage: node tools/test_statistics_core_8_wasm.mjs <exactscope.wasm>");
  process.exit(2);
}

const bytes = fs.readFileSync(path);
const { instance } = await WebAssembly.instantiate(bytes, {});
const xs = instance.exports;
const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });
const alignment = xs.xs_wasm_memory_alignment();

function alignUp(value, alignmentValue) {
  return Math.ceil(value / alignmentValue) * alignmentValue;
}

function ensureMemory(end) {
  if (end > xs.memory.buffer.byteLength) {
    xs.memory.grow(Math.ceil((end - xs.memory.buffer.byteLength) / 65536));
  }
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

const sixtyFourOnes = Array.from({ length: 64 }, () => '"1"').join(",");
const x32 = Array.from({ length: 32 }, (_, index) => `"${index + 1}"`).join(",");
const y32 = Array.from({ length: 32 }, (_, index) => `"${(index + 1) * 2}"`).join(",");

for (const [request, expectedFragment] of [
  ['{"p":[{"o":"add","a":["2","3"]}]}', '"v":"5"'],
  ['{"op":"stats.mean","a":[["1","2","3"]]}', '"v":"2"'],
  ['{"op":"stats.corr.pearson","a":[["1","2","3"],["1","2","4"]]}', '"v":"0.981981"'],
  [`{"op":"stats.mean","a":[[${sixtyFourOnes}]]}`, '"v":"1"'],
  [`{"op":"stats.corr.pearson","a":[[${x32}],[${y32}]]}`, '"v":"1"'],
]) {
  const result = callJson(request);
  if (result.returned !== 0 || result.status !== 0 || !result.response.includes(expectedFragment)) {
    throw new Error(`selected request failed: ${request} -> ${JSON.stringify(result)}`);
  }
}

for (const request of [
  '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}',
  '{"op":"stats.cov.pop","a":[["1","2"],["3","4"]]}',
  '{"op":"stats.cov.sample","a":[["1","2"],["3","4"]]}',
  '{"op":"stats.regression.linear","a":[["1","2"],["3","5"]]}',
  '{"q":"mean","n":3}',
]) {
  const result = callJson(request);
  if (result.status === 0 || result.response.includes('"v":')) {
    throw new Error(`excluded request became reachable: ${request} -> ${JSON.stringify(result)}`);
  }
}

{
  const reserved = xs.xs_wasm_reserved_end();
  const xOffset = alignUp(reserved, alignment);
  const resultOffset = alignUp(xOffset + 2 * 16, alignment);
  ensureMemory(resultOffset + 112);
  const view = new DataView(xs.memory.buffer);
  for (let index = 0; index < 2; index += 1) {
    view.setBigInt64(xOffset + index * 16, BigInt(index + 1), true);
    view.setInt8(xOffset + index * 16 + 8, 0);
    view.setUint8(xOffset + index * 16 + 9, 0);
    view.setUint16(xOffset + index * 16 + 10, 0, true);
    view.setUint32(xOffset + index * 16 + 12, 0, true);
  }
  for (const excludedId of [8, 9, 11]) {
    new Uint8Array(xs.memory.buffer, resultOffset, 112).fill(0);
    view.setUint32(resultOffset, 112, true);
    const returned = xs.xs_wasm_eval_statistics(excludedId, xOffset, 2, xOffset, 2, resultOffset);
    const status = view.getUint16(resultOffset + 4, true);
    const valueCount = view.getUint16(resultOffset + 8, true);
    if (returned === 0 || status === 0 || valueCount !== 0) {
      throw new Error(`excluded typed operation ${excludedId} became reachable`);
    }
  }
}

{
  const result = (() => {
    const input = new Uint8Array([0xa0]);
    const reserved = xs.xs_wasm_reserved_end();
    const inputOffset = alignUp(reserved, alignment);
    const outputOffset = alignUp(inputOffset + input.length, alignment);
    const metaOffset = alignUp(outputOffset + 32, alignment);
    ensureMemory(metaOffset + 16);
    new Uint8Array(xs.memory.buffer).set(input, inputOffset);
    const view = new DataView(xs.memory.buffer);
    view.setUint32(metaOffset, 16, true);
    const returned = xs.xs_wire_request(2, inputOffset, input.length, outputOffset, 32, metaOffset);
    return { returned, status: view.getUint16(metaOffset + 4, true) };
  })();
  if (result.status === 0) throw new Error(`TinyWire unexpectedly enabled: ${JSON.stringify(result)}`);
}

console.log(`PASS Statistics-8 specialized Wasm bytes=${bytes.length} imports=${WebAssembly.Module.imports(new WebAssembly.Module(bytes)).length}`);
