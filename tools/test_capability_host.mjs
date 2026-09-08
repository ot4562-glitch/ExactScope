#!/usr/bin/env node

import path from "node:path";
import process from "node:process";
import { loadCapabilityBundle } from "../examples/javascript/capability-host.mjs";

const bundleArg = process.argv[2];
if (!bundleArg) {
  throw new Error("usage: node tools/test_capability_host.mjs <combined-capability-bundle>");
}
const bundle = path.resolve(bundleArg);
const host = await loadCapabilityBundle(bundle);

const mean = await host.executeTinyJson('{"op":"stats.mean","a":[["1","2","3"]]}');
if (mean.surface !== "xs_eval" || mean.status !== 0 || !mean.response.includes('"v":"2"')) {
  throw new Error(`mean host flow failed: ${JSON.stringify(mean)}`);
}

const calc = await host.executeTinyJson('{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}');
if (calc.surface !== "xs_calc" || calc.status !== 0 || !calc.response.includes('"v":"16"')) {
  throw new Error(`calc host flow failed: ${JSON.stringify(calc)}`);
}

let excluded = false;
try {
  await host.executeTinyJson('{"op":"stats.regression.linear","a":[["1","2"],["3","4"]]}');
} catch (error) {
  excluded = String(error).includes("outside the selected capability profile");
}
if (!excluded) throw new Error("profile-excluded operation was not rejected by reference host");

let oversized = false;
try {
  await host.executeTinyJson(JSON.stringify({ p: [{ o: "add", a: ["1", "2"] }], x: "x".repeat(600) }));
} catch (error) {
  oversized = String(error).includes("request exceeds profile byte limit");
}
if (!oversized) throw new Error("oversized request was not rejected by reference host");

console.log("PASS capability host bundle identity, allowlist, calc/eval and request bounds");
