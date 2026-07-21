<script lang="ts">
  import { updater, dismissBanner, startInstall } from '../lib/updates.svelte';
</script>

{#if updater.info}
  <div class="bg-indigo-50 border-b border-indigo-200">
    <div class="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
      {#if updater.launching}
        <p class="text-sm text-indigo-900">
          Launching the installer — the app will close now.
        </p>
      {:else}
        <p class="text-sm text-indigo-900">
          New version <strong>v{updater.info.latest}</strong> available
          (installed: v{updater.info.current}).
        </p>
        <div class="flex items-center gap-3">
          {#if updater.info.notes_url}
            <a
              href={updater.info.notes_url}
              target="_blank"
              rel="noopener noreferrer"
              class="text-sm text-indigo-600 hover:underline"
            >
              What's new
            </a>
          {/if}
          <button
            onclick={() => startInstall()}
            disabled={updater.installing}
            class="px-3 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded hover:bg-indigo-700 disabled:opacity-60"
          >
            {updater.installing ? 'Downloading…' : 'Install now'}
          </button>
          <button
            onclick={() => dismissBanner()}
            disabled={updater.installing}
            class="px-3 py-1.5 text-sm font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-60"
          >
            Later
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}
