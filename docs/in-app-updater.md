# In-App Updater — Reusable Foundation

A generic, project-independent description of an in-app updating system for desktop apps distributed as installers via public GitHub Releases. Written as the reusable by-product of porting the Receipt Board updater to zerobox (`#136`–`#138`); companion piece to `windows-installer.md` (`#134`).

The pattern assumes: a locally running backend (any HTTP-capable process), a GUI shell (pywebview, Tauri, Electron, …), and releases published on a **public** repo — so the GitHub REST API works **unauthenticated**, no token to ship or protect.

---

## The Flow at a Glance

```
check (silent on startup / manual on demand)
  → compare versions
    → notify (non-blocking banner)
      → user confirms explicitly
        → re-resolve + download from trusted host
          → launch installer detached
            → app terminates itself
              → installer replaces files, relaunches app
```

Two invariants define the UX:

- **Never install without an explicit user confirmation.** Checks may be automatic; installs never are.
- **Never block.** The update offer is a dismissible banner, not a modal.

---

## Components

### `1.` Version source

Each process needs a single, authoritative version constant (e.g. a package-level `__version__`, the app manifest read via the shell's API). It must be part of the release procedure's bump list — a stale hardcoded version makes the updater lie.

### `2.` Release feed

`GET https://api.github.com/repos/{owner}/{repo}/releases/latest` (header `Accept: application/vnd.github+json`). Returns the latest non-draft, non-prerelease release: `tag_name`, `html_url` (release notes), `assets[]`. Make the `{owner}/{repo}` slug a constant with an env-var override so tests and forks can redirect it.

### `3.` Version comparison

Lenient semver: strip a leading `v`, cut pre-release/build suffixes (`-rc1`, `+meta`), compare numeric tuples. Unparsable input degrades to the lowest possible version so garbage never masquerades as an upgrade.

### `4.` Asset selection

Pick the installer out of `assets[]` by a stable naming convention (e.g. suffix `-setup.exe` for an NSIS installer). The release pipeline must guarantee that convention; the updater must tolerate its absence (report "no installer asset" rather than crash).

### `5.` Check endpoint

`GET /update/check` → `UpdateInfo`: `current`, `latest`, `update_available`, `notes_url`, `asset_url`. Pure read, no side effects. Network/parse failure → `502` (the GUI decides whether to surface it). Keep the core logic transport-agnostic (injectable HTTP client) so tests run against a mock transport, never the real network.

### `6.` Trusted download

`POST /update/install` **re-resolves the release server-side** — a client-supplied URL is never trusted. Validate the asset host against an allowlist (`github.com`, `*.githubusercontent.com` — the asset CDN it redirects to). Stream the download to a per-user writable directory (e.g. `%APPDATA%/{app}/updates/`), never into the install directory.

### `7.` Detached installer launch

Spawn the installer so it **survives the parent's exit** (Windows: `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`). The installer runs interactively and UAC-gated — no silent flags; elevation and consent stay visible to the user.

### `8.` App self-termination

Every process holding files in the install directory must exit before the installer runs, but only **after** the install HTTP response has flushed. Pattern: schedule shutdown on a short delayed timer (~`0.7 s`), return the response immediately. Who exits what is shell-specific: a pywebview app destroys its own window via a shutdown hook; a Tauri app splits it — the backend sidecar exits itself, the frontend closes the window after receiving the response.

### `9.` GUI — silent startup check

Fire the check once the main view is up. Show the banner only when newer; **fail quietly** (offline, rate-limited) — startup must never produce update-related error noise.

### `10.` GUI — manual check

A visible "Updates" action that **always gives feedback**: banner when newer, "up to date" toast otherwise, error toast on failure. If a banner is already visible, dismiss it *before* re-checking so the re-check is observable — otherwise the button looks like a no-op (learned the hard way: receipt-board#191).

### `11.` GUI — banner + confirm flow

Non-blocking banner with: version line (`New version vX available (installed: vY)`), release-notes link (opens in the system browser), **Install** and **Later/Dismiss** buttons. On confirm: disable the button, show progress states (`Downloading…` → `Launching the installer…`), then let the shutdown sequence take over. On failure: re-enable and show the error.

---

## Security Invariants

- Asset URL re-resolved server-side; client input never trusted.
- Download host allowlisted; anything else → refuse (`400`).
- No token in the client — public repo, unauthenticated API.
- Installer runs interactively with OS-level elevation prompts; never silent.
- Install requires an explicit user click every time.

---

## Reference Implementations

| Component | Receipt Board (pywebview) | zerobox (Tauri `2` sidecar) |
|---|---|---|
| Tickets | receipt-board#81, #82, #83, #191 | zerobox#136, #137, #138 |
| Core module | `src/receipt_board/core/updates.py` | `backend/src/zerobox/updates.py` |
| Endpoints | `src/receipt_board/api/updates.py` (token-gated) | `backend/src/zerobox/api/routes/update.py` |
| Version source | `app.state.app_version` | `zerobox.__version__` (BE), `getVersion()` (FE) |
| Asset convention | `*-setup.exe` (Inno Setup) | `*-setup.exe` (NSIS via Tauri) |
| Shutdown | `app.state.shutdown_hook` destroys the pywebview window | backend `os._exit` timer + frontend `window.close()` (`core:window:allow-close`) |
| GUI | `gui-src/src/updates.ts` (DOM banner host) | `frontend/src/lib/updates.svelte.ts` + `views/UpdateBanner.svelte` |

---

## Adaptation Checklist for a New Project

`1.` Publish releases on a public repo with a stable installer-asset naming convention.
`2.` Wire a single version source per process into the release bump procedure.
`3.` Port the core module (compare / fetch / select / download / launch) — it is shell-agnostic.
`4.` Add the two endpoints; keep the HTTP client injectable for tests.
`5.` Decide the shutdown choreography for your shell (who closes the window, who kills the backend).
`6.` Build the three GUI flows: silent startup check, manual check (dismiss-first re-check), banner confirm flow.
`7.` Test with a mock transport: newer / equal / no asset / network error / untrusted host — no real network in CI.
