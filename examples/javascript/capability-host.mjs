#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

function fail(message) {
  throw new Error(`ExactScope capability host: ${message}`);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

const MODEL_SURFACE_ASSETS = new Map([
  ["constrained-prompt.txt", ["prompt", "exactscope.constrained-prompt", "0.1"]],
  ["prompt-fragment.txt", ["prompt", "exactscope.prompt-fragment", "0.1"]],
  ["xs-calc.gbnf", ["grammar", "exactscope.xs-calc.gbnf", "0.1"]],
  ["xs-calc.tool.json", ["tool-schema", "exactscope.xs-calc.tool", "0.1"]],
  ["xs-eval.gbnf", ["grammar", "exactscope.xs-eval.gbnf", "0.1"]],
  ["xs-eval.tool.json", ["tool-schema", "exactscope.xs-eval.tool", "0.1"]],
  ["xs-request.gbnf", ["grammar", "exactscope.xs-request.gbnf", "0.1"]],
]);

export function verifyModelSurfaceContract(bundleDir, manifest, profile) {
  const contractFile = path.join(bundleDir, "surface-contract.json");
  const binding = profile?.bindings?.surface_contract_sha256;
  if (binding == null && !fs.existsSync(contractFile)) return null;
  if (typeof binding !== "string" || !fs.existsSync(contractFile)) fail("model-surface contract/binding must appear together");
  const contractBytes = fs.readFileSync(contractFile);
  if (sha256(contractBytes) !== binding) fail("model-surface contract digest mismatch");
  const contract = JSON.parse(contractBytes.toString("utf8"));
  if (contract.format !== "exactscope.model-surface.contract" || contract.format_version !== "0.1"
      || contract.negotiation !== "exact-version-and-digest") {
    fail("unsupported model-surface negotiation contract");
  }
  const contractProfile = contract.profile;
  if (!contractProfile || contractProfile.id !== profile.profile_id
      || contractProfile.revision !== profile.profile_revision || contractProfile.domain !== profile.domain) {
    fail("model-surface contract profile identity mismatch");
  }
  const catalog = readJson(path.join(bundleDir, "catalog.json"));
  const hotset = contract.hotset;
  if (contract.abi_revision !== profile.bindings?.abi_revision || !hotset
      || hotset.format !== catalog.format || hotset.format_version !== catalog.format_version
      || hotset.binding_sha256 !== catalog.binding_sha256
      || hotset.binding_sha256 !== profile.bindings?.hotset_sha256) {
    fail("model-surface contract runtime binding mismatch");
  }
  if (!Array.isArray(contract.assets) || contract.assets.length === 0) fail("model-surface contract assets must be nonempty");
  const expectedNames = [...MODEL_SURFACE_ASSETS.keys()].filter(name => manifest.files[name]).sort();
  const actualNames = contract.assets.map(asset => asset?.path);
  if (JSON.stringify(actualNames) !== JSON.stringify(expectedNames)) fail("model-surface contract asset inventory mismatch");
  const seen = new Set();
  for (const asset of contract.assets) {
    const expected = MODEL_SURFACE_ASSETS.get(asset.path);
    if (!expected) fail(`unknown model-surface asset: ${asset.path}`);
    const [kind, contractId, contractVersion] = expected;
    if (seen.has(contractId)) fail(`duplicate model-surface contract id: ${contractId}`);
    seen.add(contractId);
    if (asset.kind !== kind || asset.contract_id !== contractId || asset.contract_version !== contractVersion) {
      fail(`unsupported model-surface asset contract: ${asset.path}`);
    }
    if (asset.sha256 !== manifest.files[asset.path]) fail(`model-surface asset digest mismatch: ${asset.path}`);
  }
  return contract;
}

export function verifyCapabilityBundle(bundleDir) {
  const manifestBytes = fs.readFileSync(path.join(bundleDir, "manifest.json"));
  const detached = fs.readFileSync(path.join(bundleDir, "bundle-sha256.txt"), "utf8").trim();
  if (sha256(manifestBytes) !== detached) fail("manifest digest mismatch");
  const manifest = JSON.parse(manifestBytes.toString("utf8"));
  if (manifest.format !== "exactscope.capability.bundle" || manifest.format_version !== "0.1") {
    fail("unsupported capability bundle manifest");
  }
  if (!manifest.files || typeof manifest.files !== "object" || Array.isArray(manifest.files)) fail("manifest has no file digests");
  const expectedFiles = new Set(["manifest.json", "bundle-sha256.txt", ...Object.keys(manifest.files)]);
  const actualFiles = fs.readdirSync(bundleDir);
  if (actualFiles.length !== expectedFiles.size || actualFiles.some(name => !expectedFiles.has(name))) {
    fail("bundle file inventory mismatch");
  }
  for (const name of expectedFiles) {
    if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(name)) fail(`invalid bundle filename: ${name}`);
    if (!fs.lstatSync(path.join(bundleDir, name)).isFile()) fail(`bundle payload is not a regular file: ${name}`);
  }
  for (const [name, expected] of Object.entries(manifest.files)) {
    if (["manifest.json", "bundle-sha256.txt"].includes(name)) fail("manifest cannot hash itself");
    const file = path.join(bundleDir, name);
    if (!fs.existsSync(file)) fail(`manifest file missing: ${name}`);
    const actual = sha256(fs.readFileSync(file));
    if (actual !== expected) fail(`manifest digest mismatch: ${name}`);
  }
  if (manifest.files["profile.json"]) {
    verifyModelSurfaceContract(bundleDir, manifest, readJson(path.join(bundleDir, "profile.json")));
  }
  return manifest;
}

function requestSurface(profile, request) {
  if (!request || typeof request !== "object" || Array.isArray(request)) fail("request must be a JSON object");
  if (Object.hasOwn(request, "p")) {
    if (!profile.runtime_surface?.xs_calc?.enabled) fail("xs_calc is not enabled by the selected capability profile");
    return "xs_calc";
  }
  if (typeof request.op === "string") {
    const allowed = profile.runtime_surface?.xs_eval?.operations;
    if (!Array.isArray(allowed) || !allowed.includes(request.op)) {
      fail(`semantic operation is outside the selected capability profile: ${request.op}`);
    }
    return "xs_eval";
  }
  fail("request does not match an enabled serving surface");
}

function alignUp(value, alignment) {
  return Math.ceil(value / alignment) * alignment;
}

function initializeMeta(xs, metaOffset) {
  const view = new DataView(xs.memory.buffer);
  view.setUint32(metaOffset, 16, true);
  view.setUint16(metaOffset + 4, 0xffff, true);
  view.setUint16(metaOffset + 6, 0xffff, true);
  view.setUint32(metaOffset + 8, 0xffffffff, true);
  view.setUint32(metaOffset + 12, 0xffffffff, true);
}

export async function loadCapabilityBundle(bundleDir) {
  const manifest = verifyCapabilityBundle(bundleDir);
  if (!manifest.files["runtime.wasm"]) fail("bundle is not artifact-bound: runtime.wasm missing");

  const profile = readJson(path.join(bundleDir, "profile.json"));
  const wasmBytes = fs.readFileSync(path.join(bundleDir, "runtime.wasm"));
  if (wasmBytes.length !== manifest.artifact_measurements?.bytes) fail("runtime byte measurement mismatch");
  if (sha256(wasmBytes) !== manifest.files["runtime.wasm"]) fail("runtime digest mismatch");

  const module = await WebAssembly.compile(wasmBytes);
  const imports = WebAssembly.Module.imports(module);
  if (imports.length !== manifest.artifact_measurements?.imports) fail("runtime import count mismatch");
  if (imports.length !== 0) fail("reference host accepts only no-import capability runtimes");
  const instance = await WebAssembly.instantiate(module, {});
  const xs = instance.exports;
  for (const name of ["memory", "xs_abi_version", "xs_wasm_reserved_end", "xs_wasm_memory_alignment", "xs_wire_request"]) {
    if (!(name in xs)) fail(`required Wasm export missing: ${name}`);
  }
  if (xs.xs_abi_version() !== 0x0001_0000) fail("unexpected ExactScope ABI version");
  if (manifest.artifact_measurements?.initial_memory_pages != null
      && xs.memory.buffer.byteLength !== manifest.artifact_measurements.initial_memory_pages * 65536) {
    fail("initial Wasm linear-memory measurement mismatch");
  }

  return {
    manifest,
    profile,
    async executeTinyJson(requestText, outputCapacity = 512) {
      if (typeof requestText !== "string") fail("Tiny JSON request must be text");
      if (!Number.isInteger(outputCapacity) || outputCapacity < 0 || outputCapacity > 0xffff_ffff) {
        fail("output capacity must be an unsigned 32-bit integer");
      }
      const requestBytes = new TextEncoder().encode(requestText);
      const requestLimit = profile.model_budget?.request_bytes_max;
      if (!Number.isInteger(requestLimit) || requestBytes.length > requestLimit) fail("request exceeds profile byte limit");
      let parsed;
      try {
        parsed = JSON.parse(requestText);
      } catch {
        fail("request is not valid JSON");
      }
      const surface = requestSurface(profile, parsed);

      const alignment = xs.xs_wasm_memory_alignment();
      const inputOffset = alignUp(xs.xs_wasm_reserved_end(), alignment);
      const outputOffset = alignUp(inputOffset + requestBytes.length, alignment);
      const metaOffset = alignUp(outputOffset + Math.max(outputCapacity, 1), alignment);
      const required = metaOffset + 16;
      if (required > xs.memory.buffer.byteLength) {
        fail(`request/output layout exceeds selected runtime linear-memory bound: need ${required}, have ${xs.memory.buffer.byteLength}`);
      }
      const memory = new Uint8Array(xs.memory.buffer);
      memory.set(requestBytes, inputOffset);
      memory.fill(0, outputOffset, outputOffset + outputCapacity);
      initializeMeta(xs, metaOffset);
      const returned = xs.xs_wire_request(1, inputOffset, requestBytes.length, outputOffset, outputCapacity, metaOffset);
      const view = new DataView(xs.memory.buffer);
      const status = view.getUint16(metaOffset + 4, true);
      const flags = view.getUint16(metaOffset + 6, true);
      const written = view.getUint32(metaOffset + 8, true);
      const requiredOutput = view.getUint32(metaOffset + 12, true);
      const response = flags & 1
        ? new TextDecoder("utf-8", { fatal: true }).decode(memory.slice(outputOffset, outputOffset + written))
        : "";
      if (returned !== status) fail(`ABI status/meta status disagree: ${returned} vs ${status}`);
      return { surface, status, flags, written, required: requiredOutput, response };
    },
  };
}

async function main() {
  const [bundleDir, requestText] = process.argv.slice(2);
  if (!bundleDir || !requestText) {
    console.error("usage: node examples/javascript/capability-host.mjs <bound-capability-bundle> '<tiny-json-request>'");
    process.exit(2);
  }
  const host = await loadCapabilityBundle(bundleDir);
  const result = await host.executeTinyJson(requestText);
  process.stdout.write(JSON.stringify(result) + "\n");
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  await main();
}
