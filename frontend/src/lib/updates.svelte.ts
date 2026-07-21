// In-app updater UI state (#138): a manual "Updates" action plus a silent check on startup
// that shows a non-blocking banner when a newer public release exists. Installing is always
// explicit — never automatic. Mirrors the Receipt Board flow (receipt-board#83, #191).

import { getCurrentWindow } from '@tauri-apps/api/window';
import { api } from './api';
import { addToast } from './toast.svelte';
import type { UpdateInfo } from './types';

// Give the backend time to flush the install response before the window goes away.
const CLOSE_DELAY_MS = 800;

interface UpdaterState {
  info: UpdateInfo | null; // banner is visible while set
  installing: boolean;
  launching: boolean;
}

export const updater: UpdaterState = $state({
  info: null,
  installing: false,
  launching: false,
});

export function dismissBanner(): void {
  updater.info = null;
}

// Manual check (header button): always gives feedback, success or failure. An already-shown
// banner is hidden up front so the re-check is visible — it disappears on click and returns
// with the (possibly fresh) result (receipt-board#191).
export async function checkForUpdatesManually(): Promise<void> {
  dismissBanner();
  try {
    const info = await api.checkUpdate();
    if (info.update_available) {
      updater.info = info;
    } else {
      addToast(`zerobox is up to date (v${info.current})`, 'success');
    }
  } catch {
    // fetchJson already surfaced an error toast.
  }
}

// Silent check on startup: only surfaces a banner if a newer version exists.
export async function checkForUpdatesOnStartup(): Promise<void> {
  try {
    const info = await api.checkUpdate({ silent: true });
    if (info.update_available) {
      updater.info = info;
    }
  } catch {
    // Stay quiet on startup failures (offline, rate-limited, etc.).
  }
}

export async function startInstall(): Promise<void> {
  updater.installing = true;
  try {
    await api.installUpdate();
    // The backend has downloaded + launched the (UAC-gated) installer and will exit
    // itself; close the Tauri window so the installer can replace all files.
    updater.launching = true;
    setTimeout(() => {
      getCurrentWindow()
        .close()
        .catch(() => {
          // Not running inside Tauri (browser dev mode) — nothing to close.
        });
    }, CLOSE_DELAY_MS);
  } catch {
    updater.installing = false;
  }
}
