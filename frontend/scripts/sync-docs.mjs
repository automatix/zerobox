// Copy the repo's user-facing docs into frontend/public/docs/ so Vite bundles
// them into dist/, which Tauri then bundles into the installer. Source of truth
// stays in the repo's `.md` files; `frontend/public/docs/` is git-ignored.
//
// Invoked automatically by `npm run prebuild`.

import { copyFileSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const target = resolve(here, "..", "public", "docs");

const files = [
  ["README.md", "README.md"],
  ["docs/user-guide.md", "user-guide.md"],
  ["docs/architecture.md", "architecture.md"],
  ["docs/dev-testing.md", "dev-testing.md"],
  ["docs/roadmap.md", "roadmap.md"],
];

if (existsSync(target)) {
  rmSync(target, { recursive: true, force: true });
}
mkdirSync(target, { recursive: true });

for (const [src, dst] of files) {
  const from = join(repoRoot, src);
  if (!existsSync(from)) {
    console.error(`sync-docs: missing source file ${from}`);
    process.exit(1);
  }
  copyFileSync(from, join(target, dst));
}

console.log(`sync-docs: copied ${files.length} files into ${target}`);
