#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";

const path = process.argv[2];
if (!path) {
  console.error("usage: node tools/test_wasm.mjs <exactscope.wasm>");
  process.exit(2);
}

const bytes = fs.readFileSync(path);
const { instance } = await WebAssembly.instantiate(bytes, {});
const xs = instance.exports;

for (const name of [
  "memory",
  "xs_abi_version",
  "xs_wasm_reserved_end",
  "xs_wasm_memory_alignment",
  "xs_wire_request",
]) {
  if (!(name in xs)) {
    throw new Error(`missing WebAssembly export: ${name}`);
  }
}

if (xs.xs_abi_version() !== 0x0001_0000) {
  throw new Error(`unexpected ABI: ${xs.xs_abi_version().toString(16)}`);
}

const alignment = xs.xs_wasm_memory_alignment();
if (alignment !== 8) {
  throw new Error(`unexpected host-memory alignment: ${alignment}`);
}

const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });

function alignUp(value, alignmentValue) {
  return Math.ceil(value / alignmentValue) * alignmentValue;
}

function ensureMemory(end) {
  if (end <= xs.memory.buffer.byteLength) return;
  const needed = end - xs.memory.buffer.byteLength;
  xs.memory.grow(Math.ceil(needed / 65536));
}

function layout(inputLength, outputCapacity) {
  const reserved = xs.xs_wasm_reserved_end();
  const inputOffset = alignUp(reserved, alignment);
  const outputOffset = alignUp(inputOffset + inputLength, alignment);
  const metaOffset = alignUp(outputOffset + Math.max(outputCapacity, 1), alignment);
  ensureMemory(metaOffset + 16);
  return { inputOffset, outputOffset, metaOffset };
}

function initializeMeta(metaOffset) {
  const view = new DataView(xs.memory.buffer);
  view.setUint32(metaOffset, 16, true);
  view.setUint16(metaOffset + 4, 0xffff, true);
  view.setUint16(metaOffset + 6, 0xffff, true);
  view.setUint32(metaOffset + 8, 0xffffffff, true);
  view.setUint32(metaOffset + 12, 0xffffffff, true);
}

function readMeta(metaOffset) {
  const view = new DataView(xs.memory.buffer);
  return {
    structSize: view.getUint32(metaOffset, true),
    status: view.getUint16(metaOffset + 4, true),
    flags: view.getUint16(metaOffset + 6, true),
    written: view.getUint32(metaOffset + 8, true),
    required: view.getUint32(metaOffset + 12, true),
  };
}

function callJson(request, outputCapacity = 512) {
  const input = encoder.encode(request);
  const { inputOffset, outputOffset, metaOffset } = layout(input.length, outputCapacity);
  const memory = new Uint8Array(xs.memory.buffer);
  memory.set(input, inputOffset);
  memory.fill(0xa5, outputOffset, outputOffset + outputCapacity);
  initializeMeta(metaOffset);

  const returned = xs.xs_wire_request(
    1,
    inputOffset,
    input.length,
    outputOffset,
    outputCapacity,
    metaOffset,
  );
  const meta = readMeta(metaOffset);
  const response =
    meta.flags & 1
      ? decoder.decode(new Uint8Array(xs.memory.buffer, outputOffset, meta.written))
      : "";
  return { returned, meta, response, inputOffset, outputOffset, metaOffset };
}

const golden = callJson(
  '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}',
);
if (golden.returned !== 0 || golden.meta.status !== 0 || golden.meta.flags !== 1) {
  throw new Error(`golden eval failed: ${JSON.stringify(golden)}`);
}
const expectedGolden =
  '{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}';
if (golden.response !== expectedGolden) {
  throw new Error(`golden response mismatch: ${golden.response}`);
}

const discovery = callJson('{"q":"midpoint price elasticity","n":3}');
if (discovery.returned !== 0 || discovery.meta.status !== 0) {
  throw new Error(`discovery failed: ${JSON.stringify(discovery)}`);
}
const expectedFind =
  '{"s":0,"m":[{"op":"econ.ped.mid","sig":"econ.ped.mid(p1,p2,q1,q2)","method":"midpoint"}]}';
if (discovery.response !== expectedFind) {
  throw new Error(`discovery response mismatch: ${discovery.response}`);
}

const ambiguous = callJson('{"q":"price elasticity","n":5}');
if (ambiguous.returned !== 7 || ambiguous.meta.status !== 7 || ambiguous.meta.flags !== 1) {
  throw new Error(`ambiguity was not preserved: ${JSON.stringify(ambiguous)}`);
}
if (ambiguous.response !== '{"s":7,"e":"AMBIGUOUS_METHOD","need":["method"]}') {
  throw new Error(`ambiguity response mismatch: ${ambiguous.response}`);
}

const tooSmall = callJson(
  '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}',
  8,
);
if (
  tooSmall.returned !== 17 ||
  tooSmall.meta.status !== 17 ||
  tooSmall.meta.flags !== 0 ||
  tooSmall.meta.written !== 0 ||
  tooSmall.meta.required <= 8
) {
  throw new Error(`buffer sizing contract failed: ${JSON.stringify(tooSmall)}`);
}

{
  const input = encoder.encode(
    '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}',
  );
  const { inputOffset, metaOffset } = layout(input.length, 512);
  const memory = new Uint8Array(xs.memory.buffer);
  memory.set(input, inputOffset);
  initializeMeta(metaOffset);
  const returned = xs.xs_wire_request(
    1,
    inputOffset,
    input.length,
    inputOffset,
    512,
    metaOffset,
  );
  const meta = readMeta(metaOffset);
  if (returned !== 1 || meta.status !== 1 || meta.flags !== 0) {
    throw new Error(`overlap was not rejected: returned=${returned} meta=${JSON.stringify(meta)}`);
  }
}

{
  const input = encoder.encode("{}");
  const { inputOffset, outputOffset, metaOffset } = layout(input.length, 64);
  new Uint8Array(xs.memory.buffer).set(input, inputOffset);
  initializeMeta(metaOffset);
  const returned = xs.xs_wire_request(
    2,
    inputOffset,
    input.length,
    outputOffset,
    64,
    metaOffset,
  );
  const meta = readMeta(metaOffset);
  if (returned !== 21 || meta.status !== 21 || meta.flags !== 0) {
    throw new Error(`Tiny CBOR should be explicitly unsupported: ${JSON.stringify(meta)}`);
  }
}

console.log(
  `PASS wasm-runtime abi=1.0 reserved=${xs.xs_wasm_reserved_end()} ` +
    `memory=${xs.memory.buffer.byteLength} golden=${golden.response}`,
);
