// Component tests for bundle files only. No Wasm compilation or product calls.
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { verifyCapabilityBundle } from "../examples/javascript/capability-host.mjs";

const hash = value => crypto.createHash("sha256").update(value).digest("hex");

function writeManifest(directory, manifest) {
  const bytes = JSON.stringify(manifest);
  fs.writeFileSync(path.join(directory, "manifest.json"), bytes);
  fs.writeFileSync(path.join(directory, "bundle-sha256.txt"), hash(bytes) + "\n");
}

function identityAndTamperTests() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "exactscope-bundle-unit-"));
  try {
    const manifest = {
      format: "exactscope.capability.bundle", format_version: "0.1",
      files: { "profile.json": hash("{}") },
    };
    fs.writeFileSync(path.join(directory, "profile.json"), "{}");
    writeManifest(directory, manifest);
    assert.deepEqual(verifyCapabilityBundle(directory), manifest);
    fs.appendFileSync(path.join(directory, "manifest.json"), " ");
    assert.throws(() => verifyCapabilityBundle(directory), /manifest digest mismatch/);
    writeManifest(directory, manifest);
    fs.writeFileSync(path.join(directory, "profile.json"), "[]");
    assert.throws(() => verifyCapabilityBundle(directory), /manifest digest mismatch/);
    fs.writeFileSync(path.join(directory, "profile.json"), "{}");
    fs.writeFileSync(path.join(directory, "extra.json"), "{}");
    assert.throws(() => verifyCapabilityBundle(directory), /inventory mismatch/);
    fs.unlinkSync(path.join(directory, "extra.json"));
    manifest.files["../escape.json"] = hash("{}");
    writeManifest(directory, manifest);
    assert.throws(() => verifyCapabilityBundle(directory), /inventory mismatch|invalid bundle filename/);
    delete manifest.files["../escape.json"];
    writeManifest(directory, manifest);
    fs.unlinkSync(path.join(directory, "profile.json"));
    fs.mkdirSync(path.join(directory, "profile.json"));
    assert.throws(() => verifyCapabilityBundle(directory), /not a regular file/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

function modelSurfaceNegotiationTests() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "exactscope-surface-unit-"));
  try {
    const catalog = {
      format: "exactscope.hotset", format_version: "0.1", abi: "1.0", binding_sha256: "1".repeat(64),
    };
    const payloads = {
      "catalog.json": JSON.stringify(catalog),
      "prompt-fragment.txt": "Use only the bound surface.\n",
      "xs-eval.gbnf": "root ::= \"{}\"\n",
      "xs-eval.tool.json": JSON.stringify({ type: "function" }),
    };
    for (const [name, bytes] of Object.entries(payloads)) fs.writeFileSync(path.join(directory, name), bytes);

    const contract = {
      format: "exactscope.model-surface.contract",
      format_version: "0.1",
      negotiation: "exact-version-and-digest",
      profile: { id: "surface-unit", revision: 1, domain: "statistics" },
      abi_revision: "1.0",
      hotset: { format: "exactscope.hotset", format_version: "0.1", binding_sha256: "1".repeat(64) },
      assets: [
        { path: "prompt-fragment.txt", kind: "prompt", contract_id: "exactscope.prompt-fragment", contract_version: "0.1", sha256: hash(payloads["prompt-fragment.txt"]) },
        { path: "xs-eval.gbnf", kind: "grammar", contract_id: "exactscope.xs-eval.gbnf", contract_version: "0.1", sha256: hash(payloads["xs-eval.gbnf"]) },
        { path: "xs-eval.tool.json", kind: "tool-schema", contract_id: "exactscope.xs-eval.tool", contract_version: "0.1", sha256: hash(payloads["xs-eval.tool.json"]) },
      ],
    };
    let contractBytes = JSON.stringify(contract);
    fs.writeFileSync(path.join(directory, "surface-contract.json"), contractBytes);
    const profile = {
      profile_id: "surface-unit", profile_revision: 1, domain: "statistics",
      bindings: { abi_revision: "1.0", hotset_sha256: "1".repeat(64), surface_contract_sha256: hash(contractBytes) },
    };
    fs.writeFileSync(path.join(directory, "profile.json"), JSON.stringify(profile));

    const names = [...Object.keys(payloads), "surface-contract.json", "profile.json"];
    const manifest = {
      format: "exactscope.capability.bundle", format_version: "0.1",
      files: Object.fromEntries(names.map(name => [name, hash(fs.readFileSync(path.join(directory, name)))])),
    };
    writeManifest(directory, manifest);
    verifyCapabilityBundle(directory);

    contract.assets[2].contract_version = "9.9";
    contractBytes = JSON.stringify(contract);
    fs.writeFileSync(path.join(directory, "surface-contract.json"), contractBytes);
    profile.bindings.surface_contract_sha256 = hash(contractBytes);
    fs.writeFileSync(path.join(directory, "profile.json"), JSON.stringify(profile));
    manifest.files["surface-contract.json"] = hash(contractBytes);
    manifest.files["profile.json"] = hash(fs.readFileSync(path.join(directory, "profile.json")));
    writeManifest(directory, manifest);
    assert.throws(() => verifyCapabilityBundle(directory), /unsupported model-surface asset contract/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

identityAndTamperTests();
modelSurfaceNegotiationTests();
console.log("PASS bundle identity, file boundary and model-surface negotiation rejection");
