"""Dev-only CLI: wipe zerobox state selectively.

Reads the current `config.json` if present so user-configured paths are
honoured, then offers selective or full deletion of: config, env,
data-inbox, data-output, profiles, audit.

Run it via the ``scripts/dev-uninstall.(ps1|sh)`` wrappers, or directly:

    python -m zerobox.dev_uninstall [flags]

See ``docs/dev-testing.md`` for full usage.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from zerobox.paths import config_file, env_file


TARGET_DESCRIPTIONS: dict[str, str] = {
    "config": "config.json (wizard settings)",
    "env": ".env (API keys)",
    "data-inbox": "intake input folder (scans waiting to be processed)",
    "data-output": "archive/output folder (filed scans)",
    "profiles": "rule profiles directory",
    "audit": "audit.db (action log)",
}


def _expand(p: str | Path) -> Path:
    return Path(p).expanduser()


def _resolve_targets() -> dict[str, Path]:
    """Map target name -> concrete path, using `config.json` where present."""
    cfg_path = config_file()
    env_path = env_file()

    home = Path.home()
    inbox = home / "zerobox" / "inbox"
    output = home / "zerobox" / "archive"
    profiles = home / "zerobox" / "profiles"
    audit = home / "zerobox" / "audit.db"

    if cfg_path.exists():
        try:
            with open(cfg_path, encoding="utf-8") as f:
                data = json.load(f)
            inbox = _expand(data.get("intake", {}).get("input_folder", inbox))
            output = _expand(
                data.get("filemanager", {}).get("output_root", output)
            )
            profiles = _expand(data.get("profiles_dir", profiles))
            audit = _expand(data.get("audit", {}).get("db_path", audit))
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "config": cfg_path,
        "env": env_path,
        "data-inbox": inbox,
        "data-output": output,
        "profiles": profiles,
        "audit": audit,
    }


def _delete(path: Path) -> bool:
    """Remove `path`. Returns True if something was deleted, False if missing."""
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def _print_plan(targets: dict[str, Path], out=sys.stdout) -> None:
    print("The following will be deleted:", file=out)
    for name, path in targets.items():
        marker = "*" if path.exists() else " "
        print(f"  [{marker}] {name:<12} {path}", file=out)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zerobox-dev-uninstall",
        description="Wipe zerobox state selectively for dev-testing.",
    )
    parser.add_argument(
        "--all", action="store_true", help="Wipe every target below."
    )
    parser.add_argument("--config", action="store_true", help="Remove config.json.")
    parser.add_argument("--env", action="store_true", help="Remove .env (API keys).")
    parser.add_argument(
        "--data-inbox", action="store_true", help="Remove intake input folder."
    )
    parser.add_argument(
        "--data-output",
        action="store_true",
        help="Remove archive/output folder.",
    )
    parser.add_argument(
        "--profiles", action="store_true", help="Remove rule profiles directory."
    )
    parser.add_argument("--audit", action="store_true", help="Remove audit.db.")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt."
    )
    return parser


def _collect_from_flags(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(TARGET_DESCRIPTIONS.keys())
    mapping = {
        "config": "config",
        "env": "env",
        "data_inbox": "data-inbox",
        "data_output": "data-output",
        "profiles": "profiles",
        "audit": "audit",
    }
    return [name for attr, name in mapping.items() if getattr(args, attr)]


def _collect_interactive(
    all_targets: dict[str, Path], input_fn=input
) -> list[str]:
    print("zerobox dev-uninstall (interactive)")
    print("Answer y/N for each target:")
    selected: list[str] = []
    for name, path in all_targets.items():
        state = "exists" if path.exists() else "missing"
        ans = (
            input_fn(
                f"  Delete {name} ({TARGET_DESCRIPTIONS[name]}) "
                f"-- {path} [{state}]? [y/N] "
            )
            .strip()
            .lower()
        )
        if ans == "y":
            selected.append(name)
    return selected


def run(argv: list[str] | None = None, *, input_fn=input) -> int:
    args = _build_parser().parse_args(argv)
    all_targets = _resolve_targets()

    selected = _collect_from_flags(args)
    interactive = not selected and not args.all
    if interactive:
        selected = _collect_interactive(all_targets, input_fn=input_fn)

    if not selected:
        print("Nothing selected, exiting.")
        return 0

    targets = {name: all_targets[name] for name in selected}

    print()
    _print_plan(targets)
    print()

    if not args.yes:
        confirm = input_fn("Proceed? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 0

    failures = 0
    for name, path in targets.items():
        try:
            if _delete(path):
                print(f"  removed: {path}")
            else:
                print(f"  skipped (not present): {path}")
        except OSError as exc:
            print(f"  ERROR removing {path}: {exc}", file=sys.stderr)
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
