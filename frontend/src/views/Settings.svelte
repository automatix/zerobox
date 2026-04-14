<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { AppConfig } from '../lib/types';

  let config: AppConfig | null = $state(null);
  let loading = $state(true);
  let error: string | null = $state(null);

  async function loadConfig() {
    loading = true;
    error = null;
    try {
      config = (await api.getConfig()) as AppConfig;
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load configuration';
    } finally {
      loading = false;
    }
  }

  function formatValue(value: unknown): string {
    if (value === null || value === undefined) return '--';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  }

  function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  onMount(loadConfig);
</script>

<div class="p-6">
  <h2 class="text-2xl font-semibold text-gray-900 mb-2">Settings</h2>
  <p class="text-sm text-gray-500 mb-6">
    Current configuration (read-only). Edit the config file directly to make changes.
  </p>

  {#if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="text-center py-12 text-gray-500">Loading configuration...</div>
  {:else if config}
    <div class="space-y-4">
      {#each Object.entries(config) as [section, value]}
        <div class="border border-gray-200 rounded">
          <div class="bg-gray-50 px-4 py-2 border-b border-gray-200">
            <h3 class="text-sm font-medium text-gray-700">{section}</h3>
          </div>
          <div class="px-4 py-3">
            {#if isObject(value)}
              <dl class="space-y-2">
                {#each Object.entries(value) as [key, val]}
                  <div class="flex gap-4">
                    <dt class="text-sm text-gray-500 w-48 shrink-0">{key}</dt>
                    <dd class="text-sm text-gray-900 font-mono break-all">{formatValue(val)}</dd>
                  </div>
                {/each}
              </dl>
            {:else}
              <pre class="text-sm text-gray-900 font-mono whitespace-pre-wrap">{formatValue(value)}</pre>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="text-center py-12 text-gray-500">No configuration data available.</div>
  {/if}
</div>
