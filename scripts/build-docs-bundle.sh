#!/usr/bin/env bash
# Bundle the repo documentation into docs.zip for release attachment.
#
# Collects README.md and the user-facing files under docs/ into docs.zip
# in the repo root, ready to be uploaded to a GitHub Release alongside
# the installer MSI/NSIS. See docs/dev-testing.md for usage in the
# release flow. Implements IDEA-13 phase 1.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STAGING="$REPO_ROOT/.docs-bundle-staging"
OUTPUT="$REPO_ROOT/docs.zip"

rm -rf "$STAGING"
rm -f "$OUTPUT"
mkdir -p "$STAGING/docs"

cp "$REPO_ROOT/README.md" "$STAGING/"
cp "$REPO_ROOT/docs/user-guide.md" "$STAGING/docs/"
cp "$REPO_ROOT/docs/architecture.md" "$STAGING/docs/"
cp "$REPO_ROOT/docs/dev-testing.md" "$STAGING/docs/"
cp "$REPO_ROOT/docs/roadmap.md" "$STAGING/docs/"
cp -r "$REPO_ROOT/docs/postman" "$STAGING/docs/"

(cd "$STAGING" && zip -rq "$OUTPUT" .)
rm -rf "$STAGING"

echo "Created: $OUTPUT"
