<script lang="ts">
  import ReviewTable from './views/ReviewTable.svelte';
  import RuleProfiles from './views/RuleProfiles.svelte';
  import AuditLog from './views/AuditLog.svelte';
  import Settings from './views/Settings.svelte';
  import ToastContainer from './views/ToastContainer.svelte';

  type Tab = 'review' | 'rules' | 'audit' | 'settings';

  const tabs: { id: Tab; label: string }[] = [
    { id: 'review', label: 'Review' },
    { id: 'rules', label: 'Rule Profiles' },
    { id: 'audit', label: 'Audit Log' },
    { id: 'settings', label: 'Settings' },
  ];

  let activeTab: Tab = $state('review');
</script>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-900 tracking-tight">Zerobox</h1>
      <span class="text-xs text-gray-400">v0.1.0</span>
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
    {/if}
  </main>

  <ToastContainer />
</div>
