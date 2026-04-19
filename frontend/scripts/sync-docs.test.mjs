// Sanity test for scripts/sync-docs.mjs.
// Runs the sync script and asserts that every expected file exists in
// frontend/public/docs/. Run with: `node scripts/sync-docs.test.mjs`.

import { execFileSync } from "node:child_process";
import { existsSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const syncScript = resolve(here, "sync-docs.mjs");
const target = resolve(here, "..", "public", "docs");

const expected = [
  "README.md",
  "user-guide.md",
  "architecture.md",
  "dev-testing.md",
  "roadmap.md",
];

execFileSync("node", [syncScript], { stdio: "inherit" });

let failures = 0;
for (const name of expected) {
  const path = resolve(target, name);
  if (!existsSync(path)) {
    console.error(`FAIL: missing ${path}`);
    failures += 1;
    continue;
  }
  if (statSync(path).size === 0) {
    console.error(`FAIL: empty ${path}`);
    failures += 1;
    continue;
  }
  console.log(`OK:   ${name}`);
}

if (failures > 0) {
  console.error(`sync-docs.test: ${failures} failure(s)`);
  process.exit(1);
}
console.log(`sync-docs.test: all ${expected.length} expected files present`);
