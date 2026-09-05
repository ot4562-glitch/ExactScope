#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";

const [path, calcMode = "no-calc"] = process.argv.slice(2);
if (!path || !["calc", "no-calc"].includes(calcMode)) {
  console.error("usage: node tools/test_selected_economics_wasm.mjs <exactscope.wasm> [calc|no-calc]");
  process.exit(2);
}

const bytes = fs.readFileSync(path);
const module = new WebAssembly.Module(bytes);
if (WebAssembly.Module.imports(module).length !== 0) throw new Error("imports forbidden");
const xs = new WebAssembly.Instance(module, {}).exports;
const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });
const alignment = xs.xs_wasm_memory_alignment();

for (const name of [
  "memory", "xs_abi_version", "xs_wasm_eval_statistics", "xs_wasm_memory_alignment",
  "xs_wasm_reserved_end", "xs_wire_request",
]) {
  if (!(name in xs)) throw new Error(`missing stable Wasm export: ${name}`);
}

function alignUp(value, align) {
  return Math.ceil(value / align) * align;
}

function callJson(text) {
  const input = encoder.encode(text);
  const reserved = xs.xs_wasm_reserved_end();
  const inputOffset = alignUp(reserved, alignment);
  const outputOffset = alignUp(inputOffset + input.length, alignment);
  const metaOffset = alignUp(outputOffset + 512, alignment);
  if (metaOffset + 16 > xs.memory.buffer.byteLength) {
    throw new Error("test request exceeds fixed one-page memory instead of fitting the profile");
  }
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

const cases = [
  [
    '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}',
    0,
    '{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}',
  ],
  [
    '{"op":"econ.ped.mid","a":["10","20","20","10"]}',
    0,
    '{"s":0,"v":"-1","c":"unit_elastic","p":"econ-undergrad@0.1.0","r":1}',
  ],
  [
    '{"op":"econ.ped.mid","a":["10","12","100","95"]}',
    0,
    '{"s":0,"v":"-0.282051","c":"inelastic","p":"econ-undergrad@0.1.0","r":1}',
  ],
  [
    '{"op":"econ.ped.mid","a":["10","10","100","80"]}',
    13,
    '{"s":13,"e":"DIVIDE_BY_ZERO"}',
  ],
  [
    '{"op":"econ.ped.mid","a":["-1","10","100","80"]}',
    11,
    '{"s":11,"e":"CONSTRAINT_VIOLATION","i":0,"d":1}',
  ],
  [
    '{"op":"econ.ped.mid","a":["10","20","0","0"]}',
    13,
    '{"s":13,"e":"DIVIDE_BY_ZERO"}',
  ],
  [
    '{"op":"econ.ped.mid","a":["10","20","-1","5"]}',
    11,
    '{"s":11,"e":"CONSTRAINT_VIOLATION","i":2,"d":3}',
  ],
  [
    '{"op":"econ.ped.mid","a":["bad","20","10","5"]}',
    9,
    '{"s":9,"e":"INVALID_DECIMAL","i":0}',
  ],
];
for (const [request, expectedStatus, expectedResponse] of cases) {
  const result = callJson(request);
  if (result.returned !== expectedStatus || result.status !== expectedStatus || result.response !== expectedResponse) {
    throw new Error(`PED differential mismatch: ${JSON.stringify({ request, result, expectedStatus, expectedResponse })}`);
  }
}

const calc = callJson('{"p":[{"o":"add","a":["2","3"]}]}');
if (calcMode === "calc") {
  if (calc.status !== 0 || !calc.response.includes('"v":"5"')) {
    throw new Error(`xs_calc regression: ${JSON.stringify(calc)}`);
  }
} else if (calc.status === 0 || calc.response.includes('"v":')) {
  throw new Error(`xs_calc unexpectedly reachable: ${JSON.stringify(calc)}`);
}

for (const request of [
  '{"op":"econ.gdp.deflator100","a":["120","100"]}',
  '{"op":"stats.mean","a":[["1","2","3"]]}',
  '{"q":"midpoint price elasticity","n":3}',
]) {
  const result = callJson(request);
  if (result.status === 0 || result.response.includes('"v":')) {
    throw new Error(`excluded serving path became reachable: ${request}`);
  }
}

if (xs.xs_wasm_eval_statistics(1, 0, 0, 0, 0, 0) === 0) {
  throw new Error("Economics-only artifact unexpectedly enabled direct Statistics evaluation");
}

{
  const input = new Uint8Array([0xa0]);
  const reserved = xs.xs_wasm_reserved_end();
  const inputOffset = alignUp(reserved, alignment);
  const outputOffset = alignUp(inputOffset + input.length, alignment);
  const metaOffset = alignUp(outputOffset + 32, alignment);
  if (metaOffset + 16 > xs.memory.buffer.byteLength) throw new Error("TinyCBOR test exceeds memory");
  new Uint8Array(xs.memory.buffer).set(input, inputOffset);
  const view = new DataView(xs.memory.buffer);
  view.setUint32(metaOffset, 16, true);
  xs.xs_wire_request(2, inputOffset, input.length, outputOffset, 32, metaOffset);
  if (view.getUint16(metaOffset + 4, true) === 0) {
    throw new Error("TinyCBOR unexpectedly enabled in Economics specialization");
  }
}

console.log(`PASS selected Economics Wasm op=econ.ped.mid bytes=${bytes.length} imports=0 memory=${xs.memory.buffer.byteLength}`);
