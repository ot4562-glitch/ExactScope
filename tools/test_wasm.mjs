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
  "xs_wasm_eval_statistics",
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

function writeDecimal(view, offset, coefficient, exponent) {
  view.setBigInt64(offset, BigInt(coefficient), true);
  view.setInt8(offset + 8, exponent);
  view.setUint8(offset + 9, 0);
  view.setUint16(offset + 10, 0, true);
  view.setUint32(offset + 12, 0, true);
}

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

function callWire(format, input, outputCapacity = 512) {
  const { inputOffset, outputOffset, metaOffset } = layout(input.length, outputCapacity);
  const memory = new Uint8Array(xs.memory.buffer);
  memory.set(input, inputOffset);
  memory.fill(0xa5, outputOffset, outputOffset + outputCapacity);
  initializeMeta(metaOffset);

  const returned = xs.xs_wire_request(
    format,
    inputOffset,
    input.length,
    outputOffset,
    outputCapacity,
    metaOffset,
  );
  const meta = readMeta(metaOffset);
  const responseBytes =
    meta.flags & 1
      ? new Uint8Array(xs.memory.buffer, outputOffset, meta.written).slice()
      : new Uint8Array();
  return { returned, meta, responseBytes, inputOffset, outputOffset, metaOffset };
}

function callJson(request, outputCapacity = 512) {
  const result = callWire(1, encoder.encode(request), outputCapacity);
  return { ...result, response: decoder.decode(result.responseBytes) };
}

function cborHead(major, value) {
  const v = BigInt(value);
  const prefix = major << 5;
  if (v <= 23n) return [prefix | Number(v)];
  if (v <= 0xffn) return [prefix | 0x18, Number(v)];
  if (v <= 0xffffn) return [prefix | 0x19, Number(v >> 8n), Number(v & 0xffn)];
  if (v <= 0xffffffffn) {
    return [
      prefix | 0x1a,
      Number((v >> 24n) & 0xffn),
      Number((v >> 16n) & 0xffn),
      Number((v >> 8n) & 0xffn),
      Number(v & 0xffn),
    ];
  }
  throw new Error("test CBOR integer exceeds u32");
}

function cborInt(value) {
  const v = BigInt(value);
  return v >= 0n ? cborHead(0, v) : cborHead(1, -1n - v);
}

function cborDecimal(exponent, coefficient) {
  return [0xc4, 0x82, ...cborInt(exponent), ...cborInt(coefficient)];
}

function cborVectorRef(values) {
  return [
    0x84,
    0x01,
    0x00,
    0x00,
    ...cborHead(4, values.length),
    ...values.flatMap((value) => cborDecimal(0, value)),
  ];
}

function cborText(value) {
  const bytes = encoder.encode(value);
  return [...cborHead(3, bytes.length), ...bytes];
}

function cborFindRequest(query, limit) {
  return new Uint8Array([
    0xa4,
    0x00,
    0x01,
    0x01,
    0x00,
    0x02,
    ...cborText(query),
    0x03,
    ...cborHead(0, limit),
  ]);
}

function cborEvalRequest(packSlot, operationId, refs) {
  return new Uint8Array([
    0xa8,
    0x00,
    0x01,
    0x01,
    0x01,
    0x02,
    ...cborHead(0, packSlot),
    0x03,
    ...cborHead(0, operationId),
    0x04,
    ...cborHead(4, refs.length),
    ...refs.flat(),
    0x05,
    0x38,
    0x7f,
    0x06,
    0x18,
    0xff,
    0x07,
    0x00,
  ]);
}

const golden = callJson(
  '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}',
);
if (golden.returned !== 0 || golden.meta.status !== 0 || golden.meta.flags !== 1) {
  throw new Error(`golden eval failed: ${JSON.stringify(golden)}`);
}

const boundedPlan = callJson(
  '{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}',
);
if (
  boundedPlan.returned !== 0 ||
  boundedPlan.meta.status !== 0 ||
  boundedPlan.response !== '{"s":0,"v":"16","f":0,"p":"plan-v0.1","r":1}'
) {
  throw new Error(`Tiny JSON bounded plan failed: ${JSON.stringify(boundedPlan)}`);
}

const boundedPlanFailure = callJson('{"p":[{"o":"div","a":["1","0"]}]}');
if (
  boundedPlanFailure.returned !== 13 ||
  boundedPlanFailure.meta.status !== 13 ||
  boundedPlanFailure.response !== '{"s":13,"e":"DIVIDE_BY_ZERO","step":0}'
) {
  throw new Error(`Tiny JSON bounded plan failure drift: ${JSON.stringify(boundedPlanFailure)}`);
}

{
  const reserved = xs.xs_wasm_reserved_end();
  const xOffset = alignUp(reserved, alignment);
  const yOffset = alignUp(xOffset + 3 * 16, alignment);
  const resultOffset = alignUp(yOffset + 3 * 16, alignment);
  ensureMemory(resultOffset + 112);
  const view = new DataView(xs.memory.buffer);
  [1, 2, 3].forEach((value, index) => writeDecimal(view, xOffset + index * 16, value, 0));
  [1, 2, 4].forEach((value, index) => writeDecimal(view, yOffset + index * 16, value, 0));
  view.setUint32(resultOffset, 112, true);
  const returned = xs.xs_wasm_eval_statistics(10, xOffset, 3, yOffset, 3, resultOffset);
  if (returned !== 0 || view.getUint16(resultOffset + 4, true) !== 0) {
    throw new Error(`typed statistics eval failed: ${returned}`);
  }
  if (
    view.getBigInt64(resultOffset + 32, true) !== 981981n ||
    view.getInt8(resultOffset + 40) !== -6 ||
    view.getUint8(resultOffset + 41) !== 0
  ) {
    throw new Error("typed statistics result drift");
  }
  if ((view.getUint32(resultOffset + 44, true) & 3) !== 3) {
    throw new Error("typed statistics rounded/inexact flags missing");
  }
}
const expectedGolden =
  '{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}';
if (golden.response !== expectedGolden) {
  throw new Error(`golden response mismatch: ${golden.response}`);
}

const statisticsMean = callJson('{"op":"stats.mean","a":[["1","2","3"]]}');
if (
  statisticsMean.returned !== 0 ||
  statisticsMean.meta.status !== 0 ||
  statisticsMean.response !== '{"s":0,"v":"2","p":"statistics-core@0.1.0","r":1}'
) {
  throw new Error(`Tiny JSON statistics mean failed: ${JSON.stringify(statisticsMean)}`);
}

const statisticsRegression = callJson(
  '{"op":"stats.regression.linear","a":[["1","2","3"],["3","5","7"]]}',
);
if (
  statisticsRegression.returned !== 0 ||
  statisticsRegression.meta.status !== 0 ||
  statisticsRegression.response !==
    '{"s":0,"v":["2","1"],"names":["slope","intercept"],"p":"statistics-core@0.1.0","r":1}'
) {
  throw new Error(`Tiny JSON statistics regression failed: ${JSON.stringify(statisticsRegression)}`);
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

const statisticsDiscovery = callJson('{"q":"sample variance","n":3}');
if (statisticsDiscovery.returned !== 0 || statisticsDiscovery.meta.status !== 0) {
  throw new Error(`statistics discovery failed: ${JSON.stringify(statisticsDiscovery)}`);
}
if (
  statisticsDiscovery.response !==
  '{"s":0,"m":[{"op":"stats.var.sample","sig":"stats.var.sample(values)","method":"two_pass_sample"}]}'
) {
  throw new Error(`statistics discovery response mismatch: ${statisticsDiscovery.response}`);
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
  const economics = callWire(2, cborFindRequest("midpoint price elasticity", 3), 512);
  if (economics.returned !== 0 || economics.meta.status !== 0 || economics.meta.flags !== 1) {
    throw new Error(`TinyWire economics find failed: ${JSON.stringify(economics.meta)}`);
  }
  if (!Buffer.from(economics.responseBytes).includes(Buffer.from("econ.ped.mid"))) {
    throw new Error("TinyWire economics find lost canonical operation key");
  }

  const statistics = callWire(2, cborFindRequest("pearson correlation", 3), 512);
  if (statistics.returned !== 0 || statistics.meta.status !== 0 || statistics.meta.flags !== 1) {
    throw new Error(`TinyWire statistics find failed: ${JSON.stringify(statistics.meta)}`);
  }
  if (!Buffer.from(statistics.responseBytes).includes(Buffer.from("stats.corr.pearson"))) {
    throw new Error("TinyWire statistics find lost canonical operation key");
  }

  const ambiguousFind = callWire(2, cborFindRequest("price elasticity", 3), 128);
  if (ambiguousFind.returned !== 7 || ambiguousFind.meta.status !== 7) {
    throw new Error(`TinyWire ambiguity drift: ${JSON.stringify(ambiguousFind.meta)}`);
  }
}

{
  const input = cborEvalRequest(2, 10, [
    cborVectorRef([1, 2, 3]),
    cborVectorRef([1, 2, 4]),
  ]);
  const result = callWire(2, input, 256);
  if (result.returned !== 0 || result.meta.status !== 0 || result.meta.flags !== 1) {
    throw new Error(`TinyWire statistics eval failed: ${JSON.stringify(result.meta)}`);
  }
  const responseHex = Buffer.from(result.responseBytes).toString("hex");
  const expectedHex = "a9000101188102000381c482251a000efbdd040005030683020a0107060800";
  if (responseHex !== expectedHex) {
    throw new Error(`TinyWire response drift: ${responseHex}`);
  }

  const tooSmall = callWire(2, input, 4);
  if (
    tooSmall.returned !== 17 ||
    tooSmall.meta.status !== 17 ||
    tooSmall.meta.flags !== 0 ||
    tooSmall.meta.required <= 4
  ) {
    throw new Error(`TinyWire sizing contract failed: ${JSON.stringify(tooSmall.meta)}`);
  }
}

console.log(
  `PASS wasm-runtime abi=1.0 reserved=${xs.xs_wasm_reserved_end()} ` +
    `memory=${xs.memory.buffer.byteLength} golden=${golden.response}`,
);
