<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { AuditEntry } from '../lib/types';

  let entries: AuditEntry[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);

  let filterAction = $state('');
  let filterDateFrom = $state('');
  let filterDateTo = $state('');

  async function loadAuditLog() {
    loading = true;
    error = null;
    try {
      const params: Record<string, string> = {};
      if (filterAction) params.action = filterAction;
      if (filterDateFrom) params.from = filterDateFrom;
      if (filterDateTo) params.to = filterDateTo;
      entries = (await api.getAuditLog(
        Object.keys(params).length > 0 ? params : undefined,
      )) as AuditEntry[];
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load audit log';
    } finally {
      loading = false;
    }
  }

  function formatTimestamp(ts: string): string {
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  }

  function clearFilters() {
    filterAction = '';
    filterDateFrom = '';
    filterDateTo = '';
    loadAuditLog();
  }

  onMount(loadAuditLog);
</script>

<div class="p-6">
  <h2 class="text-2xl font-semibold text-gray-900 mb-6">Audit Log</h2>

  {#if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
      {error}
    </div>
  {/if}

  <!-- Filters -->
  <div class="flex flex-wrap gap-3 mb-4 items-end">
    <div>
      <label for="filter-action" class="block text-xs text-gray-500 mb-1">Action</label>
      <input
        id="filter-action"
        type="text"
        placeholder="e.g. rename, move"
        bind:value={filterAction}
        class="border border-gray-300 rounded px-3 py-1.5 text-sm w-40"
      />
    </div>
    <div>
      <label for="filter-from" class="block text-xs text-gray-500 mb-1">From</label>
      <input
        id="filter-from"
        type="date"
        bind:value={filterDateFrom}
        class="border border-gray-300 rounded px-3 py-1.5 text-sm"
      />
    </div>
    <div>
      <label for="filter-to" class="block text-xs text-gray-500 mb-1">To</label>
      <input
        id="filter-to"
        type="date"
        bind:value={filterDateTo}
        class="border border-gray-300 rounded px-3 py-1.5 text-sm"
      />
    </div>
    <button
      onclick={loadAuditLog}
      class="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm hover:bg-indigo-700 transition-colors"
    >
      Apply
    </button>
    <button
      onclick={clearFilters}
      class="text-gray-500 hover:text-gray-700 px-3 py-1.5 text-sm"
    >
      Clear
    </button>
  </div>

  {#if loading}
    <div class="text-center py-12 text-gray-500">Loading audit log...</div>
  {:else if entries.length === 0}
    <div class="text-center py-12 text-gray-500">No audit entries found.</div>
  {:else}
    <div class="overflow-x-auto">
      <table class="w-full text-sm text-left border-collapse">
        <thead>
          <tr class="border-b border-gray-200 text-gray-500 uppercase text-xs">
            <th class="py-3 px-4 font-medium">ID</th>
            <th class="py-3 px-4 font-medium">Timestamp</th>
            <th class="py-3 px-4 font-medium">Action</th>
            <th class="py-3 px-4 font-medium">Source</th>
            <th class="py-3 px-4 font-medium">Target</th>
            <th class="py-3 px-4 font-medium">Rule ID</th>
            <th class="py-3 px-4 font-medium">Details</th>
          </tr>
        </thead>
        <tbody>
          {#each entries as entry (entry.id)}
            <tr class="border-b border-gray-100 hover:bg-gray-50">
              <td class="py-3 px-4 text-gray-400">{entry.id}</td>
              <td class="py-3 px-4 text-xs">{formatTimestamp(entry.timestamp)}</td>
              <td class="py-3 px-4">
                <span class="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs font-medium">
                  {entry.action}
                </span>
              </td>
              <td class="py-3 px-4 font-mono text-xs max-w-48 truncate">{entry.source}</td>
              <td class="py-3 px-4 font-mono text-xs max-w-48 truncate">{entry.target ?? '--'}</td>
              <td class="py-3 px-4 text-xs">{entry.rule_id ?? '--'}</td>
              <td class="py-3 px-4 text-xs text-gray-500 max-w-64 truncate">
                {JSON.stringify(entry.details)}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
