<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { RuleProfile } from '../lib/types';

  let profiles: RuleProfile[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);
  let selectedProfileId: string | null = $state(null);
  let showCreateForm = $state(false);
  let showAddRuleForm = $state(false);

  // New profile form
  let newProfileName = $state('');
  let newProfileDescription = $state('');

  // New rule form
  let newRulePatterns = $state('');
  let newRuleNameTemplate = $state('');
  let newRuleFolderTemplate = $state('');
  let newRulePriority = $state(0);

  $effect(() => {
    if (profiles.length > 0 && !selectedProfileId) {
      selectedProfileId = profiles[0].id;
    }
  });

  function selectedProfile(): RuleProfile | undefined {
    return profiles.find((p) => p.id === selectedProfileId);
  }

  async function loadProfiles() {
    loading = true;
    error = null;
    try {
      profiles = (await api.getProfiles()) as RuleProfile[];
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load profiles';
    } finally {
      loading = false;
    }
  }

  async function createProfile() {
    if (!newProfileName.trim()) return;
    try {
      await api.createProfile({
        name: newProfileName,
        description: newProfileDescription,
      });
      newProfileName = '';
      newProfileDescription = '';
      showCreateForm = false;
      await loadProfiles();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to create profile';
    }
  }

  async function deleteProfile(id: string) {
    try {
      await api.deleteProfile(id);
      if (selectedProfileId === id) selectedProfileId = null;
      await loadProfiles();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete profile';
    }
  }

  async function addRule() {
    if (!selectedProfileId || !newRulePatterns.trim()) return;
    try {
      await api.addRule(selectedProfileId, {
        patterns: newRulePatterns.split(',').map((p) => p.trim()),
        target_name_template: newRuleNameTemplate,
        target_folder_template: newRuleFolderTemplate,
        priority: newRulePriority,
      });
      newRulePatterns = '';
      newRuleNameTemplate = '';
      newRuleFolderTemplate = '';
      newRulePriority = 0;
      showAddRuleForm = false;
      await loadProfiles();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to add rule';
    }
  }

  async function deleteRule(profileId: string, ruleId: string) {
    try {
      await api.deleteRule(profileId, ruleId);
      await loadProfiles();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to delete rule';
    }
  }

  onMount(loadProfiles);
</script>

<div class="p-6">
  <div class="flex items-center justify-between mb-6">
    <h2 class="text-2xl font-semibold text-gray-900">Rule Profiles</h2>
    <button
      onclick={() => { showCreateForm = !showCreateForm; }}
      class="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm hover:bg-indigo-700 transition-colors"
    >
      {showCreateForm ? 'Cancel' : 'New Profile'}
    </button>
  </div>

  {#if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
      {error}
    </div>
  {/if}

  {#if showCreateForm}
    <div class="bg-gray-50 border border-gray-200 rounded p-4 mb-4">
      <h3 class="text-sm font-medium text-gray-700 mb-3">Create New Profile</h3>
      <div class="space-y-3">
        <input
          type="text"
          placeholder="Profile name"
          bind:value={newProfileName}
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Description"
          bind:value={newProfileDescription}
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        <button
          onclick={createProfile}
          class="bg-green-600 text-white px-4 py-1.5 rounded text-sm hover:bg-green-700"
        >
          Create
        </button>
      </div>
    </div>
  {/if}

  {#if loading}
    <div class="text-center py-12 text-gray-500">Loading profiles...</div>
  {:else}
    <div class="flex gap-6">
      <!-- Profile list -->
      <div class="w-64 shrink-0">
        {#if profiles.length === 0}
          <p class="text-gray-500 text-sm">No profiles yet.</p>
        {:else}
          <div class="space-y-1">
            {#each profiles as profile (profile.id)}
              <div
                role="button"
                tabindex="0"
                class="flex items-center justify-between px-3 py-2 rounded cursor-pointer text-sm transition-colors {selectedProfileId === profile.id ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'}"
                onclick={() => { selectedProfileId = profile.id; }}
                onkeydown={(e) => { if (e.key === 'Enter') selectedProfileId = profile.id; }}
              >
                <span class="truncate">{profile.name}</span>
                <button
                  onclick={(e) => { e.stopPropagation(); deleteProfile(profile.id); }}
                  class="text-red-400 hover:text-red-600 ml-2 shrink-0"
                  title="Delete profile"
                >
                  x
                </button>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Rules panel -->
      <div class="flex-1 min-w-0">
        {#if selectedProfile()}
          {@const profile = selectedProfile()!}
          <div class="mb-4">
            <h3 class="text-lg font-medium text-gray-900">{profile.name}</h3>
            {#if profile.description}
              <p class="text-sm text-gray-500 mt-1">{profile.description}</p>
            {/if}
          </div>

          <div class="flex items-center justify-between mb-3">
            <h4 class="text-sm font-medium text-gray-700">
              Rules ({profile.rules?.length ?? 0})
            </h4>
            <button
              onclick={() => { showAddRuleForm = !showAddRuleForm; }}
              class="text-sm text-indigo-600 hover:text-indigo-800"
            >
              {showAddRuleForm ? 'Cancel' : '+ Add Rule'}
            </button>
          </div>

          {#if showAddRuleForm}
            <div class="bg-gray-50 border border-gray-200 rounded p-4 mb-4">
              <div class="space-y-3">
                <input
                  type="text"
                  placeholder="Patterns (comma-separated)"
                  bind:value={newRulePatterns}
                  class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  placeholder="Name template"
                  bind:value={newRuleNameTemplate}
                  class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  placeholder="Folder template"
                  bind:value={newRuleFolderTemplate}
                  class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  placeholder="Priority"
                  bind:value={newRulePriority}
                  class="w-32 border border-gray-300 rounded px-3 py-2 text-sm"
                />
                <button
                  onclick={addRule}
                  class="bg-green-600 text-white px-4 py-1.5 rounded text-sm hover:bg-green-700"
                >
                  Add Rule
                </button>
              </div>
            </div>
          {/if}

          {#if !profile.rules || profile.rules.length === 0}
            <p class="text-gray-500 text-sm">No rules in this profile.</p>
          {:else}
            <div class="space-y-2">
              {#each profile.rules as rule (rule.id)}
                <div class="border border-gray-200 rounded p-3">
                  <div class="flex items-start justify-between">
                    <div class="text-sm">
                      <div class="font-medium text-gray-900">
                        Patterns: <span class="font-mono text-xs">{rule.patterns.join(', ')}</span>
                      </div>
                      <div class="text-gray-600 mt-1">
                        Name: <span class="font-mono text-xs">{rule.target_name_template}</span>
                      </div>
                      <div class="text-gray-600">
                        Folder: <span class="font-mono text-xs">{rule.target_folder_template}</span>
                      </div>
                      <div class="text-gray-400 text-xs mt-1">
                        Priority: {rule.priority}
                      </div>
                    </div>
                    <button
                      onclick={() => deleteRule(profile.id, rule.id)}
                      class="text-red-400 hover:text-red-600 text-sm shrink-0"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        {:else}
          <p class="text-gray-500 text-sm">Select a profile to view its rules.</p>
        {/if}
      </div>
    </div>
  {/if}
</div>
