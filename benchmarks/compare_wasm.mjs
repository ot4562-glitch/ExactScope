#!/usr/bin/env node
// Paired in-process microbenchmark; never model or real-device latency evidence.
import fs from "node:fs";
import crypto from "node:crypto";
import os from "node:os";
import { performance } from "node:perf_hooks";

const [beforePath, afterPath, outputPath] = process.argv.slice(2);
if (!beforePath || !afterPath || !outputPath) throw new Error("usage: compare_wasm.mjs before.wasm after.wasm output.json");
const sha = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
async function runner(path) {
  const bytes = fs.readFileSync(path);
  const xs = (await WebAssembly.instantiate(bytes, {})).instance.exports;
  const align = x => Math.ceil(x / 8) * 8;
  const input = align(xs.xs_wasm_reserved_end()), output = input + 512, meta = output + 512;
  if (meta + 16 > xs.memory.buffer.byteLength) xs.memory.grow(Math.ceil((meta + 16 - xs.memory.buffer.byteLength) / 65536));
  const memory = new Uint8Array(xs.memory.buffer), view = new DataView(xs.memory.buffer);
  view.setUint32(meta, 16, true);
  return { sha256: sha(bytes), bytes: bytes.length,
    prepare(request) {
      const encoded = new TextEncoder().encode(JSON.stringify(request));
      memory.set(encoded, input);
      const call = () => xs.xs_wire_request(1, input, encoded.length, output, 512, meta);
      call();
      const result = new TextDecoder().decode(memory.subarray(output, output + view.getUint32(meta + 8, true)));
      return { call, result };
    }
  };
}
const before = await runner(beforePath), after = await runner(afterPath);
const requests = {
  "calc-rationals": { p: [{ o: "div", a: ["1234567", "999983"] }, { o: "mul", a: ["#0", "0.000123"] }, { o: "div", a: ["#1", "7.25"] }] },
  "statistics-variance": { op: "stats.var.sample", a: [["1.2", "3.7", "-2.1", "8.2", "3.4", "2.6"]] },
  "statistics-correlation": { op: "stats.corr.pearson", a: [["1", "2", "3", "4", "5", "6"], ["6", "2", "7", "4", "9", "3"]] }
};
const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
const samples = {};
for (const [name, request] of Object.entries(requests)) {
  const pair = [before.prepare(request), after.prepare(request)];
  if (pair[0].result !== pair[1].result || JSON.parse(pair[0].result).s !== 0) throw new Error(`semantic mismatch ${name}`);
  for (let i = 0; i < 1000; i++) for (const lane of pair) lane.call();
  const measured = [[], []], iterations = 2000;
  for (let round = 0; round < 7; round++) {
    for (const index of round % 2 ? [1, 0] : [0, 1]) {
      const start = performance.now();
      for (let i = 0; i < iterations; i++) pair[index].call();
      measured[index].push((performance.now() - start) * 1000 / iterations);
    }
  }
  samples[name] = { request, response: pair[0].result, iterations, before_us: measured[0], after_us: measured[1],
    before_median_us: median(measured[0]), after_median_us: median(measured[1]) };
}
const result = { scope: "desktop in-process Wasm wire microbenchmark, concurrent system load possible",
  node: process.version, os: `${os.platform()} ${os.release()}`, cpu: os.cpus()[0].model,
  before: { sha256: before.sha256, bytes: before.bytes }, after: { sha256: after.sha256, bytes: after.bytes }, samples };
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + "\n", { flag: "wx" });
for (const [name, s] of Object.entries(samples)) console.log(`${name}: ${s.before_median_us.toFixed(2)} -> ${s.after_median_us.toFixed(2)} us`);
