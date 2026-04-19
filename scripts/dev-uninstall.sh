#!/usr/bin/env bash
# Wipe zerobox state selectively for dev-testing.
#
# Thin wrapper around `python -m zerobox.dev_uninstall`. Forwards every
# argument to the Python module. See docs/dev-testing.md for flags and
# full usage.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT/backend"
exec python -m zerobox.dev_uninstall "$@"
