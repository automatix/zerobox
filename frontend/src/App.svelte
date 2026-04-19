<script lang="ts">
  import { api } from './lib/api';
  import ReviewTable from './views/ReviewTable.svelte';
  import RuleProfiles from './views/RuleProfiles.svelte';
  import AuditLog from './views/AuditLog.svelte';
  import Settings from './views/Settings.svelte';
  import HelpTab from './views/HelpTab.svelte';
  import SetupWizard from './views/SetupWizard.svelte';
  import ToastContainer from './views/ToastContainer.svelte';

  type Tab = 'review' | 'rules' | 'audit' | 'settings' | 'help';

  const tabs: { id: Tab; label: string }[] = [
    { id: 'review', label: 'Review' },
    { id: 'rules', label: 'Rule Profiles' },
    { id: 'audit', label: 'Audit Log' },
    { id: 'settings', label: 'Settings' },
    { id: 'help', label: 'Help' },
  ];

  let activeTab: Tab = $state('review');
  let setupComplete: boolean | null = $state(null); // null = loading
  let setupError: string | null = $state(null);

  async function checkSetup() {
    setupError = null;
    try {
      const status = await api.getSetupStatus();
      setupComplete = status.setup_complete;
    } catch (err) {
      setupError = err instanceof Error ? err.message : String(err);
    }
  }

  $effect(() => {
    checkSetup();
  });
</script>

{#if setupError !== null}
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-6">
    <div class="max-w-md w-full bg-white border border-red-200 rounded-lg p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-red-700 mb-2">Backend unreachable</h2>
      <p class="text-sm text-gray-700 mb-4">
        Could not load setup status from the backend. Please verify the backend is running
        at <code class="bg-gray-100 px-1 rounded">http://localhost:8000</code>.
      </p>
      <p class="text-xs text-gray-500 mb-4">Details: {setupError}</p>
      <button
        onclick={() => { setupComplete = null; checkSetup(); }}
        class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded hover:bg-indigo-700"
      >
        Retry
      </button>
    </div>
    <ToastContainer />
  </div>
{:else if setupComplete === null}
  <!-- Loading -->
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <p class="text-gray-500 text-sm">Loading...</p>
  </div>
{:else if !setupComplete}
  <SetupWizard />
  <ToastContainer />
{:else}
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <h1 class="text-xl font-bold text-gray-900 tracking-tight">zerobox</h1>
        <span class="text-xs text-gray-400">v0.5.0</span>
      </div>
    </header>

    <!-- Tab navigation -->
    <nav class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-6">
        <div class="flex gap-6">
          {#each tabs as tab (tab.id)}
            <button
              onclick={() => { activeTab = tab.id; }}
              class="py-3 text-sm font-medium border-b-2 transition-colors {activeTab === tab.id
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            >
              {tab.label}
            </button>
          {/each}
        </div>
      </div>
    </nav>

    <!-- Content -->
    <main class="max-w-7xl mx-auto">
      {#if activeTab === 'review'}
        <ReviewTable />
      {:else if activeTab === 'rules'}
        <RuleProfiles />
      {:else if activeTab === 'audit'}
        <AuditLog />
      {:else if activeTab === 'settings'}
        <Settings />
      {:else if activeTab === 'help'}
        <HelpTab />
      {/if}
    </main>

    <ToastContainer />
  </div>
{/if}
