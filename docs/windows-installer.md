# Windows Installer & Uninstaller — zerobox

> **Purpose.** This is a deep-dive on how zerobox builds, ships, installs, and
> uninstalls itself on Windows `11`. It is written to double as a **product and
> technical foundation** for giving *another* Python desktop app a Windows
> installer — specifically **Receipt Board** (Python/FastAPI backend + HTML/CSS/JS
> frontend, packaged with PyInstaller). It documents **zerobox only**; it does
> **not** pick an installer technology for Receipt Board. The closing section
> (`§9`) maps which parts transfer, which need adapting, and which simply do not
> apply, and lists the open options neutrally.
>
> Audience: developers / build engineers. For the end-user install steps in their
> shortest form, see [`README.md` → Installation](../README.md#installation).
> For building from source, see [`dev-testing.md`](./dev-testing.md).

---

## Legend — generality of each point

Throughout this document, claims are tagged so you can tell instantly what
carries over to a different app and what is peculiar to zerobox:

| Tag | Meaning |
|---|---|
| 🟦 **GENERAL** | True for essentially any Windows desktop-app installer, regardless of language/stack. |
| 🟨 **PYTHON** | Specific to packaging a **Python** app (the interpreter problem, PyInstaller, hidden imports, …). Transfers to most Python desktop apps. |
| 🟥 **ZEROBOX** | Specific to zerobox's concrete stack or product choices (Tauri shell, OCR tooling, sidecar model, …). Will differ for another app. |

When a single point has both a general kernel and a zerobox-specific detail, it
is tagged with both.

---

## 1. TL;DR

🟥 **ZEROBOX.** zerobox is a **Tauri `2`** desktop app (Rust shell + WebView2)
whose UI is Svelte `5`, with a **Python/FastAPI backend** that runs as a Tauri
**sidecar** (a managed child process the shell launches, spoken to over local
HTTP). Because it is a Tauri app, **the installer comes essentially for free
from the Tauri bundler**: one build command produces both an `.msi` and an
NSIS `.exe`, each with an auto-generated uninstaller.

The whole pipeline is three moving parts:

1. 🟨 **Package the Python backend into a single `.exe`** with **PyInstaller**.
2. 🟥 **Drop that `.exe` into Tauri as a sidecar binary** and let the **Tauri
   bundler** wrap shell + UI + sidecar into installers.
3. 🟥 **Hook NSIS** (`nsis/hooks.nsh`) to handle install-time dependency setup
   and an uninstall-time "remove my data too?" prompt.

A single orchestration script — [`scripts/build-installer.ps1`](../scripts/build-installer.ps1)
— runs steps 1–2; step 3 is configuration the bundler reads.

**Does zerobox have an uninstaller?** **Yes.** Both bundle formats register a
standard Windows uninstaller (Add/Remove Programs / *Apps & features*). zerobox
additionally hooks the NSIS uninstaller to *optionally* wipe user data. (There
is also a developer-only `dev_uninstall.py` CLI — a **separate** testing tool,
not the product uninstaller; see `§7`.)

---

## 2. The end-user experience (User-Sicht)

### 2.1 Where the user gets it

🟦 **GENERAL.** Installers are attached to the project's
[GitHub Releases](https://github.com/automatix/zerobox/releases). The user
downloads one file and runs it. No app store, no package manager.

🟥 **ZEROBOX.** Two artifacts are offered, and the README steers users to the
NSIS one:

| Artifact | Filename pattern | Positioned as |
|---|---|---|
| **NSIS** | `zerobox_X.Y.Z_x64-setup.exe` | **Recommended.** Interactive wizard; can fetch missing OCR tools for you. |
| **MSI** | `zerobox_X.Y.Z_x64_en-US.msi` | Plain Windows Installer for managed / enterprise (Group Policy) deployment. Does **not** offer OCR-tool setup. |

The reason both exist and why the `.exe` is preferred is a real decision with a
real cause — see `§5.4`.

### 2.2 Installing — the NSIS `.exe` (recommended path)

🟦 **GENERAL** wizard skeleton, 🟥 **ZEROBOX** dependency prompts:

1. User double-clicks `…-setup.exe`. Windows SmartScreen may warn because the
   binary is **unsigned** (see `§4`).
2. Standard NSIS pages: license / destination / start-menu, then install.
3. 🟥 **Before files are copied** (the `PREINSTALL` hook), zerobox checks
   whether **Tesseract OCR** and **Ghostscript** are present. For each missing
   tool the user gets a three-way choice:
   - **Yes** → download + install it **system-wide** (silent),
   - **No** → download a **portable** copy into `…\zerobox\resources\…`,
   - **Cancel** → skip; install it manually later.

   The binaries are fetched from their **upstream** projects at install time;
   they are **not** redistributed inside the installer (licensing — see `§5.3`).
4. Files are copied to the chosen location; Start-menu / desktop shortcuts are
   created; the app is registered for uninstall.

### 2.3 Installing — the MSI

🟥 **ZEROBOX.** Same app, but the MSI runs as a plain transactional Windows
Installer package — no interactive dependency prompts. Suitable for silent /
Group-Policy rollout. The user is expected to provide Tesseract + Ghostscript
themselves.

### 2.4 First run

🟦 **GENERAL** pattern (first-run init), 🟥 **ZEROBOX** specifics:

- A **First-Run-Wizard** collects settings and writes `config.json` + `.env`
  to a **per-user config directory** — `%APPDATA%\zerobox\` on Windows (see
  `DD-07` in `§6`). Writing to per-user (not into `Program Files\`) is
  deliberate: `Program Files\` is not user-writable.
- The wizard verifies OCR tools via `GET /setup/status` and shows a coloured
  dot per tool. If the NSIS installer already fetched them, they show green; if
  missing, an amber "OCR tools required" notice links to the docs and lets the
  user continue anyway.

### 2.5 Uninstalling

🟦 **GENERAL.** The app appears in **Settings → Apps → Installed apps** (and
classic *Programs and Features*). Uninstall runs the bundle's generated
uninstaller, removing program files and shortcuts.

🟥 **ZEROBOX.** The NSIS uninstaller additionally asks **"remove user data and
configuration too?"** (`config.json`, `.env`, inbox/archive folders, rule
profiles, audit DB). Default is **keep** — so a reinstall finds prior data.
Detail in `§7`.

---

## 3. The technical pipeline (Technik)

```
            ┌──────────────────────────── scripts/build-installer.ps1 ────────────────────────────┐
            │                                                                                      │
  backend/  │   PyInstaller --onefile --noconsole                                                  │
  (FastAPI) │ ───────────────────────────────────►  binaries/zerobox-backend-<target-triple>.exe   │
            │                                                  │                                    │
            │                                                  ▼  (Tauri externalBin sidecar)       │
  frontend/ │   npm run tauri build  ──────────────►  Tauri bundler (Rust shell + Svelte UI +       │
  (Svelte)  │                                          sidecar + resources + NSIS hooks)            │
            │                                                  │                                    │
            └──────────────────────────────────────────────────┼────────────────────────────────────┘
                                                               ▼
                          target/release/bundle/{msi/*.msi, nsis/*-setup.exe}   (+ uninstaller built in)
```

### 3.1 Step 1 — package the Python backend with PyInstaller

🟨 **PYTHON.** A shipped Python app cannot assume Python is on the target
machine. PyInstaller freezes the interpreter + the app + its dependencies into
a redistributable binary. zerobox uses **one-file, windowed** mode:

```powershell
python -m PyInstaller `
    --name "zerobox-backend-x86_64-pc-windows-msvc" `
    --onefile `
    --noconsole `
    --add-data "src/zerobox;zerobox" `
    --hidden-import "uvicorn.logging" `
    --hidden-import "uvicorn.loops" `
    --hidden-import "uvicorn.loops.auto" `
    ... (more uvicorn.* hidden imports) ...
    src/zerobox/__main__.py
```

Decisions baked in here, and why:

- 🟨 **`--onefile`** → a single `.exe` (simplest to treat as a Tauri sidecar).
  *Trade-off:* one-file unpacks to a temp dir at every launch (slower cold
  start) vs. `--onedir` (a folder, faster start, more files to ship). zerobox
  picked one-file because it slots cleanly into Tauri's single-binary sidecar
  model. **Receipt Board already uses `--onedir`** — a valid, different choice.
- 🟨 **`--noconsole`** (a.k.a. windowed) → no stray console window pops up
  behind the GUI. Required for a polished desktop app.
- 🟨 **`--hidden-import uvicorn.*`** → **the single most common PyInstaller
  gotcha for FastAPI / uvicorn apps.** uvicorn loads its protocol / loop /
  lifespan implementations by **dynamic string import**, which PyInstaller's
  static analysis cannot see, so they are missing at runtime unless declared.
  Any ASGI app frozen with PyInstaller hits this. (See the full list in the
  build script.)
- 🟨 **`--add-data "src/zerobox;zerobox"`** → bundles non-code package data.
  Note the Windows path separator is **`;`** (it is `:` on POSIX).
- 🟥 **`--name …-x86_64-pc-windows-msvc`** → the **target-triple suffix is not
  cosmetic**. Tauri's sidecar mechanism requires the external binary to be named
  `<base>-<target-triple>.exe`; at build time Tauri strips the triple and
  invokes `<base>`. Get this name wrong and the bundler fails to find the
  sidecar. This is a **Tauri** convention, not a PyInstaller one.

🟨 **PYTHON — build from the project's venv.** The script prefers
`backend/.venv\Scripts\python.exe` over whatever `python` is on `PATH`, because
PyInstaller traces imports **using the interpreter it runs under**. If that
interpreter cannot import `fastapi` / `uvicorn` / …, those modules silently miss
the freeze. Building from the populated venv guarantees the analysis sees the
real dependency graph. (See `§5.5`.)

The resulting `.exe` is copied into `frontend/src-tauri/binaries/`.

### 3.2 Step 2 — Tauri bundler configuration

🟥 **ZEROBOX.** [`frontend/src-tauri/tauri.conf.json`](../frontend/src-tauri/tauri.conf.json)
declares both bundle targets, the sidecar, resources, icons, and the NSIS hook
file:

```jsonc
{
  "productName": "zerobox",
  "version": "0.7.0",
  "identifier": "com.zerobox.app",
  "bundle": {
    "active": true,
    "targets": ["msi", "nsis"],            // build BOTH formats
    "icon": ["icons/icon.ico", "icons/icon.png"],
    "externalBin": ["binaries/zerobox-backend"],   // the PyInstaller sidecar (triple appended)
    "windows": {
      "certificateThumbprint": null,       // unsigned (see §4)
      "digestAlgorithm": "sha256",
      "timestampUrl": "",
      "nsis": { "installerHooks": "./nsis/hooks.nsh" }
    },
    "resources": ["resources/*"]           // extra files copied next to the app
  }
}
```

- 🟦 **GENERAL** concepts: a stable **product name**, **version**, and a unique
  **application identifier** (`com.zerobox.app`, reverse-DNS) — every Windows
  installer needs an identity; the identifier underpins uninstall registration
  and upgrade matching.
- 🟥 `externalBin` is the Tauri-specific way to ship the sidecar.
- `npm run tauri build` (run from `frontend/`) does the rest: builds the Svelte
  UI (`beforeBuildCommand`), compiles the Rust shell, embeds UI + sidecar +
  resources, and emits the bundles.

### 3.3 Step 3 — NSIS installer hooks

🟥 **ZEROBOX**, but the *mechanism* (🟦 **GENERAL**: installers expose pre/post-
install and pre/post-uninstall hook points) transfers to any NSIS- or
Inno-Setup-based installer. zerobox's [`nsis/hooks.nsh`](../frontend/src-tauri/nsis/hooks.nsh)
implements two of Tauri's NSIS hook macros:

- **`NSIS_HOOK_PREINSTALL`** — detect & optionally install **Tesseract** and
  **Ghostscript**:
  - *Detection* is layered: registry (UB-Mannheim / Artifex keys, both 64- and
    32-bit registry views) → `PATH` (`where tesseract.exe` / `where
    gswin64c.exe`) → a portable copy under `resources/` from a prior install.
    🟦 The "check several places, don't trust just `PATH`" lesson is general
    (see `§5.2`).
  - *Install* offers system-wide (`installer /S`) or portable
    (`installer /S /D=<INSTDIR>\resources\…`), downloading via `NSISdl::download`
    from pinned upstream URLs, with user-facing error messages on failure.
- **`NSIS_HOOK_POSTUNINSTALL`** — the optional user-data wipe (see `§7`).

### 3.4 The build orchestrator — `build-installer.ps1`

🟦 **GENERAL.** A single scripted entry point so the build is reproducible and
not a sequence of remembered manual commands. It: resolves the interpreter
(prefer venv), installs PyInstaller if needed, freezes the backend, copies the
sidecar, then runs `npm run tauri build`. Output lands in
`frontend/src-tauri/target/release/bundle/` (`msi/`, `nsis/`).

🟦 **GENERAL Windows-PowerShell lesson:** the script is hardened against a
**Windows PowerShell 5.1** trap — see `§5.1`, the single most important
portability fix in the build.

### 3.5 Output artifacts

```
frontend/src-tauri/target/release/bundle/
├── msi/  zerobox_0.7.0_x64_en-US.msi
└── nsis/ zerobox_0.7.0_x64-setup.exe
```

Both are attached to the corresponding GitHub Release, alongside tag-pinned
documentation links (see the **Versioning** procedure in
[`CLAUDE.md`](../CLAUDE.md)).

### 3.6 Runtime dependency — WebView2

🟦 **GENERAL for any WebView-based desktop app** (Tauri, pywebview, Electron-on-
Edge, …): the app renders through **Microsoft Edge WebView2**. On Windows `11`
the runtime is present by default; on older systems it may need the **Evergreen
bootstrapper**. zerobox relies on Windows `11`'s built-in runtime and does not
ship the bootstrapper. Any WebView app must decide how WebView2 is guaranteed
(assume present / bundle bootstrapper / detect-and-fetch like the OCR tools).

---

## 4. Code signing

🟦 **GENERAL.** zerobox currently ships **unsigned** binaries
(`certificateThumbprint: null`). Consequences: Windows **SmartScreen** shows a
"Windows protected your PC / unknown publisher" prompt until the download builds
reputation; some enterprises block unsigned installers outright. Signing
requires an Authenticode (ideally OV/EV) code-signing certificate and wiring its
thumbprint + a `timestampUrl` into the bundler config (or the equivalent
`signtool` step for a non-Tauri installer). This is the same decision for any
Windows app and is left open here.

---

## 5. Problems we hit & how we solved them

Each item: the symptom, the cause, the fix, and how general the lesson is.
Ticket / decision references point at [`MEMORY.md`](../MEMORY.md) and the GitHub
issues.

### 5.1 `#120` — Windows PowerShell 5.1 turns tool stderr into a fatal error

🟦 **GENERAL (Windows PowerShell).** **Symptom:** `build-installer.ps1` aborted
mid-build on a clean machine, even though `pip` / `pyinstaller` / `npm` / `cargo`
had actually succeeded. **Cause:** under **Windows PowerShell 5.1**, with
`$ErrorActionPreference = "Stop"`, *any* native command that merely **writes to
stderr** (pip's upgrade notice, cargo's progress, …) is promoted to a
**terminating** `NativeCommandError` — regardless of a `0` exit code. **Fix:**
set `$ErrorActionPreference = "Continue"` and check **`$LASTEXITCODE`
explicitly** after every native call (an `Invoke-Native` helper that throws only
on a non-zero code), plus silence pip's notice via
`PIP_DISABLE_PIP_VERSION_CHECK=1`. **Lesson:** *any* PowerShell build script that
shells out to native tools and must run under `5.1` needs this pattern — do not
rely on `-ErrorAction Stop` to mean "fail on real errors."

### 5.2 `#68` — detect tools that don't touch `PATH`

🟦 **GENERAL** detection lesson, 🟥 **ZEROBOX** tools. **Symptom:** the OCR check
reported "Not found" even after the user had installed Tesseract and Ghostscript.
**Cause:** their Windows installers drop binaries under `C:\Program Files\…`
**without** adding them to `PATH`. **Fix:** detect via multiple strategies —
registry keys, well-known install globs, *then* `PATH` — rather than `PATH` alone
(mirrored in both the backend's `setup.py` and the NSIS `PREINSTALL` detection).
**Lesson:** never assume a third-party tool is on `PATH`; probe registry +
conventional locations too.

### 5.3 `#126` / `DD-10` — stop bundling OCR tools

🟥 **ZEROBOX** outcome, 🟨/🟦 transferable **licensing** lesson. **History:** the
original plan (`DD-06`) was a zero-prerequisite installer that **bundled**
Python + Tesseract + Ghostscript. **Problem:** **Ghostscript is AGPL-3.0** —
redistributing it inside a closed installer is a licensing liability; the
bundling was never actually implemented (`resources/` shipped empty).
**Decision (`DD-10`):** do **not** bundle the OCR tools. Make them **honest,
documented prerequisites** that the wizard verifies, while the NSIS installer
*offers* to fetch them from upstream at install time (download ≠ redistribute).
The PyInstaller backend + Tauri shell stay bundled. This also retired the
`dev`-vs-`installer` `run_mode` distinction (`DD-09` / `#52`), which only made
sense under the bundling premise. **Lesson:** **audit the license of every
third-party binary before bundling it**; "download from upstream on the user's
machine" is a clean way to sidestep redistribution terms.

### 5.4 `#132` / `#133` — recommend the NSIS `.exe` over the MSI

🟥 **ZEROBOX** recommendation, 🟦 **GENERAL** MSI-vs-NSIS insight.
**Observation:** only the NSIS `.exe` can run the interactive "fetch the OCR
tools for you" flow; the **MSI cannot** do interactive downloads / nested
third-party installs cleanly (that would need a **WiX Burn bootstrapper**, which
Tauri does not generate). **Decision:** rather than retrofit the MSI, **document
the `.exe` as recommended** (best end-user experience) and frame the `.msi` as
the plain managed-deployment option. Docs-only change; no code, no version bump.
**Lesson:** MSI is transactional and enterprise-friendly but a poor fit for
interactive, branching install logic; an NSIS / Inno `.exe` is the natural home
for that. Pick the format per the install behaviour you need.

### 5.5 Build from the backend venv (PyInstaller import tracing)

🟨 **PYTHON.** **Symptom (latent):** a backend frozen with a bare `python` could
miss `fastapi` / `uvicorn` if that interpreter wasn't the one with the deps
installed. **Cause:** PyInstaller analyses imports under the interpreter it runs
with. **Fix:** the build script prefers `backend/.venv` and warns when it falls
back to `PATH`. **Lesson:** always freeze from the environment that actually has
the app's dependencies installed.

### 5.6 `DD-07` — install to a per-user-writable state location

🟦 **GENERAL.** **Problem:** the old config strategy wrote next to the executable,
which fails when the app is installed under `Program Files\` (not user-writable
without elevation). **Fix:** put `config.json` / `.env` in an **OS-conventional
per-user directory** (`%APPDATA%\zerobox\` on Windows), with an env-var override
for dev/tests. **Lesson:** an installed app must never assume its install
directory is writable; user state belongs under `%APPDATA%` / `%LOCALAPPDATA%`.

---

## 6. Key decisions & rationale

| ID | Decision | Why | Generality |
|---|---|---|---|
| `DD-04` | Backend as a **Tauri sidecar** over local HTTP | Keep Python logic; native shell; clean process boundary | 🟥 ZEROBOX (architecture) |
| `DD-06` → `DD-10` | **Don't** bundle OCR tools; treat as prerequisites | Ghostscript AGPL; download-on-demand avoids redistribution | 🟥 outcome / 🟨🟦 licensing lesson |
| `DD-07` | Config/data in **per-user** dirs (`%APPDATA%`) | `Program Files\` isn't user-writable | 🟦 GENERAL |
| `DD-09` (retired) | `run_mode` dev-vs-installer signal | Made sense only under bundling; removed with `DD-10` | 🟥 ZEROBOX |
| `#132` | Recommend NSIS `.exe`; MSI for managed deploy | MSI can't do interactive nested installs without WiX Burn | 🟦 MSI-vs-NSIS / 🟥 recommendation |
| `#120` | `Continue` + explicit `$LASTEXITCODE` in build script | PS 5.1 promotes native stderr to fatal | 🟦 GENERAL (PowerShell) |

Full text and dates for each are in [`MEMORY.md`](../MEMORY.md).

---

## 7. Uninstaller

🟦 **GENERAL.** Both bundle formats register a real uninstaller with Windows, so
zerobox appears under *Apps & features* and uninstalls cleanly (program files +
shortcuts + registry entries). You get this **for free** from the bundler — no
extra work to *have* an uninstaller.

🟥 **ZEROBOX value-add — `NSIS_HOOK_POSTUNINSTALL`.** Removing the program is one
thing; the user's *data* is another. zerobox's POST-uninstall hook prompts:

> "Do you want to remove zerobox user data and configuration as well?
> (config.json, .env, inbox, archive, rule profiles, audit DB)"

- Default is **No / keep** — so a later reinstall finds prior data.
- It does **not** prompt during silent / passive runs or during an **update**
  (guarded by `$PassiveMode` / `$UpdateMode`) — you must never nuke data on an
  upgrade.
- It deletes the default `%USERPROFILE%\zerobox\` tree and config files; it notes
  that **custom** user-configured paths need manual cleanup (the hook can't
  reliably read config that may already be gone). 🟦 The general lesson:
  *deciding* what counts as "user data" and offering keep-vs-remove is a product
  decision every stateful app's uninstaller faces.

🟨 **PYTHON / dev tooling — `dev_uninstall.py` is NOT the product uninstaller.**
[`backend/src/zerobox/dev_uninstall.py`](../backend/src/zerobox/dev_uninstall.py)
(run via `scripts/dev-uninstall.ps1` / `.sh`) is a **developer testing** CLI to
wipe state selectively (config / env / inbox / archive / profiles / audit) so the
First-Run-Wizard can be re-tested from zero. It reads `config.json` to honour
custom paths, prints a deletion plan, and confirms. It ships with the source, not
the installer. Mentioned here only to disambiguate it from the real uninstaller.
The *pattern* (a scriptable "reset my state" command keyed off the same config the
app uses) is reusable — see `§9`.

---

## 8. General vs Python-specific vs zerobox-specific — the consolidated matrix

| Concern | 🟦 General | 🟨 Python-app | 🟥 zerobox-specific |
|---|---|---|---|
| Distribution | GitHub Release, download-and-run | — | Two formats (MSI + NSIS) |
| App identity | name + version + reverse-DNS id | — | `com.zerobox.app` |
| Ship the interpreter | — | PyInstaller freeze (`onefile`/`onedir`, `--noconsole`) | one-file, sidecar-named with target triple |
| Dynamic imports | — | declare `--hidden-import` (uvicorn/ASGI!) | uvicorn protocol/loop/lifespan list |
| Build from correct env | — | freeze from the venv with deps | prefer `backend/.venv` |
| Installer authoring | wizard, shortcuts, uninstall reg. | — | Tauri bundler emits it |
| Install/uninstall hooks | pre/post hook points exist | — | `nsis/hooks.nsh` (OCR setup, data wipe) |
| Third-party native deps | detect beyond `PATH`; mind licenses | — | Tesseract + Ghostscript, AGPL-driven non-bundling |
| Per-user state location | use `%APPDATA%` / `%LOCALAPPDATA%` | — | `%APPDATA%\zerobox\` (`DD-07`) |
| WebView runtime | guarantee WebView2 somehow | — | assume Win 11 built-in |
| Code signing | Authenticode to avoid SmartScreen | — | currently unsigned |
| PS build robustness | `$LASTEXITCODE`, not `-EA Stop` (PS 5.1) | — | `Invoke-Native` helper |
| Uninstall data policy | keep-vs-remove prompt; skip on update | — | `NSIS_HOOK_POSTUNINSTALL` |

---

## 9. Foundation for another Python app (Receipt Board)

This section is the **bridge**. It does **not** choose an installer technology
for Receipt Board — that is left open — it only maps what transfers.

### 9.1 Stack comparison

| Aspect | zerobox (this repo) | Receipt Board (target) |
|---|---|---|
| Backend | Python / FastAPI / uvicorn | Python `3.12` / FastAPI / uvicorn |
| Frontend | Svelte `5` (built by Vite) | TypeScript built by **esbuild** → static files |
| Desktop shell | **Tauri `2`** (Rust + WebView2) | **pywebview** (WebView2), no Rust shell |
| Backend↔UI | Tauri **sidecar** + local HTTP | **in-process**: FastAPI serves the UI at `/app`, pywebview opens it |
| Freeze mode | PyInstaller **`--onefile`** | PyInstaller **`--onedir`** (already in `receipt_board.spec`) |
| Native deps | Tesseract + Ghostscript | **none** (pure Python) |
| Installer today | Tauri bundler → MSI + NSIS | **none** — shipped as a `.zip` |
| Port | fixed `localhost:8000` | **ephemeral**, written to `runtime.json` |
| State dir | `%APPDATA%\zerobox\` | `%LOCALAPPDATA%\receipt-board\` |

### 9.2 What transfers directly (🟦 / 🟨)

- The **PyInstaller-for-FastAPI** know-how: `--noconsole`, **uvicorn hidden
  imports**, `--add-data` with `;`, freeze-from-venv. (Receipt Board already
  PyInstalls; the hidden-import discipline still applies.)
- The **per-user state** principle — Receipt Board already does this
  (`%LOCALAPPDATA%\receipt-board\`), so its uninstaller faces the same
  keep-vs-remove data decision (`receipt_board.sqlite`, `config.toml`,
  `runtime.json`, logs).
- The **PowerShell build-robustness** pattern (`#120`) for any PS build script.
- The **WebView2** runtime question (pywebview uses WebView2 too).
- The **code-signing / SmartScreen** trade-off.
- The **"reset my state" dev CLI** pattern (zerobox's `dev_uninstall.py`).
- The **install / uninstall hook concept**, including the **optional data-wipe on
  uninstall** and **never-wipe-on-update** guard.

### 9.3 What needs adapting (🟥)

- **The installer engine itself.** zerobox gets MSI + NSIS *from Tauri*. Receipt
  Board has **no Tauri**, so there is nothing to emit the installer — it must be
  produced another way. The NSIS *hook techniques* (detection, data-wipe prompt)
  are reusable **as NSIS script**, but the *bundler that generated the rest of
  the `.nsi`* is not present.
- **Sidecar naming / target-triple** convention is Tauri-only — **not needed**
  for Receipt Board.
- **Dependency-fetching hooks** (Tesseract / Ghostscript) are **not applicable** —
  Receipt Board has no native deps. Its installer is correspondingly simpler.
- **`onedir` vs `onefile`**: Receipt Board's installer wraps a **folder** of files
  (the `onedir` output), not a single `.exe`. Most Windows installer tools handle
  "install this directory tree" natively.

### 9.4 Open decision for Receipt Board (presented neutrally — not chosen here)

Because Receipt Board is a PyInstaller-`onedir` app with **no Tauri bundler**, the
installer has to be authored by some other tool. The realistic options, with what
each implies — **no recommendation is made here**:

| Option | What it is | Implication |
|---|---|---|
| **Standalone NSIS** | Hand-written / templated `.nsi` wrapping the `onedir` output | Reuses zerobox's NSIS hook techniques directly (data-wipe prompt, WebView2 check); produces an `.exe`; full scripting control; you author the whole script. |
| **Inno Setup** | A `.iss` script compiler | Simple, well-documented, great for "install this folder + shortcuts + uninstaller"; Pascal scripting for custom steps; produces an `.exe`. |
| **WiX / MSI** | Author an MSI directly | Best for enterprise / Group-Policy; transactional; poor at interactive / branching logic (same limitation as `§5.4`). |
| **Adopt Tauri** | Re-shell RB as a Tauri app, FastAPI as sidecar | Reuses zerobox's *exact* pipeline (MSI + NSIS free) but is a **large** change that replaces pywebview. |

Whichever is chosen, the installer should still: install the `onedir` tree to a
per-user-or-`Program Files` location, create shortcuts, register an uninstaller,
ensure WebView2, decide signing, and (optionally) offer the keep-vs-remove data
prompt on uninstall — i.e. reuse the `§2` / `§7` product behaviour even though the
engine differs.

### 9.5 Pre-flight checklist for Receipt Board's installer

- [ ] Pick the installer engine (`§9.4`) — **decision required**.
- [ ] Confirm the PyInstaller `onedir` build is reproducible (mirror
      `build-installer.ps1`'s freeze-from-venv + `$LASTEXITCODE` discipline).
- [ ] Verify uvicorn / ASGI **hidden imports** are complete for RB.
- [ ] Define app identity: product name (`Receipt Board`), version (`1.1.0`),
      reverse-DNS identifier, **icon** (currently a placeholder).
- [ ] Decide WebView2 strategy (assume Win 11 / bundle bootstrapper / fetch).
- [ ] Decide install scope (per-user vs per-machine) and shortcut set.
- [ ] Uninstaller: confirm it removes program files; decide the keep-vs-remove
      prompt for `%LOCALAPPDATA%\receipt-board\` (DB, config, logs); **never**
      wipe on update.
- [ ] Decide code signing (or accept SmartScreen warnings).
- [ ] Attach the artifact to a GitHub Release with tag-pinned docs.

---

## 10. References

**In this repo**

- [`scripts/build-installer.ps1`](../scripts/build-installer.ps1) — the build orchestrator (PyInstaller → Tauri bundler).
- [`frontend/src-tauri/tauri.conf.json`](../frontend/src-tauri/tauri.conf.json) — bundle targets, sidecar, icons, NSIS hook wiring.
- [`frontend/src-tauri/nsis/hooks.nsh`](../frontend/src-tauri/nsis/hooks.nsh) — PREINSTALL dependency setup + POSTUNINSTALL data-wipe prompt.
- [`backend/src/zerobox/dev_uninstall.py`](../backend/src/zerobox/dev_uninstall.py) — dev-only state reset (not the product uninstaller).
- [`docs/dev-testing.md`](./dev-testing.md) — building the installer from source.
- [`README.md`](../README.md) — end-user installation & prerequisites.
- [`MEMORY.md`](../MEMORY.md) — `DD-*` decisions and ticket journal (`#120`, `#126`, `#132`, …).

**External**

- PyInstaller — <https://pyinstaller.org/>
- Tauri `2` bundler / NSIS hooks — <https://v2.tauri.app/distribute/>
- NSIS — <https://nsis.sourceforge.io/>
- Inno Setup — <https://jrsoftware.org/isinfo.php>
- WiX Toolset — <https://wixtoolset.org/>
- Microsoft Edge WebView2 — <https://developer.microsoft.com/microsoft-edge/webview2/>
</content>
