<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { Proposal } from '../lib/types';
  import CorrectionDialog from './CorrectionDialog.svelte';

  let proposals: Proposal[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);
  let correcting: Proposal | null = $state(null);
  let statusFilter: string = $state('');

  async function loadProposals() {
    loading = true;
    error = null;
    try {
      proposals = await api.getProposals(statusFilter || undefined) as Proposal[];
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to load proposals';
    } finally {
      loading = false;
    }
  }

  async function runPipeline() {
    loading = true;
    error = null;
    try {
      await api.runPipeline();
      await loadProposals();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Pipeline failed';
      loading = false;
    }
  }

  async function approve(id: string) {
    try {
      await api.updateProposal(id, { status: 'approved' });
      await loadProposals();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to approve';
    }
  }

  async function reject(id: string) {
    try {
      await api.updateProposal(id, { status: 'rejected' });
      await loadProposals();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to reject';
    }
  }

  async function executeAll() {
    try {
      await api.executeProposals();
      await loadProposals();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Execution failed';
    }
  }

  function openCorrection(proposal: Proposal) {
    correcting = { ...proposal };
  }

  async function handleCorrectionSave(updated: { proposed_name: string; proposed_folder: string }) {
    if (!correcting) return;
    try {
      await api.updateProposal(correcting.id, {
        status: 'corrected',
        proposed_name: updated.proposed_name,
        proposed_folder: updated.proposed_folder,
      });
      correcting = null;
      await loadProposals();
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : 'Failed to save correction';
    }
  }

  function confidenceColor(confidence: number): string {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  }

  function statusBadge(status: string): string {
    const base = 'px-2 py-0.5 rounded text-xs font-medium';
    switch (status) {
      case 'pending': return `${base} bg-gray-100 text-gray-700`;
      case 'approved': return `${base} bg-green-100 text-green-700`;
      case 'rejected': return `${base} bg-red-100 text-red-700`;
      case 'corrected': return `${base} bg-blue-100 text-blue-700`;
      default: return base;
    }
  }

  onMount(loadProposals);
</script>

<div class="p-6">
  <div class="flex items-center justify-between mb-6">
    <h2 class="text-2xl font-semibold text-gray-900">Review Proposals</h2>
    <div class="flex gap-2">
      <select
        bind:value={statusFilter}
        onchange={loadProposals}
        class="border border-gray-300 rounded px-3 py-1.5 text-sm"
      >
        <option value="">All statuses</option>
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="corrected">Corrected</option>
      </select>
      <button
        onclick={runPipeline}
        class="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm hover:bg-indigo-700 transition-colors"
      >
        Run Pipeline
      </button>
      <button
        onclick={executeAll}
        class="bg-green-600 text-white px-4 py-1.5 rounded text-sm hover:bg-green-700 transition-colors"
      >
        Execute Approved
      </button>
    </div>
  </div>

  {#if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="text-center py-12 text-gray-500">Loading proposals...</div>
  {:else if proposals.length === 0}
    <div class="text-center py-12 text-gray-500">
      No proposals found. Run the pipeline to process scanned files.
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="w-full text-sm text-left border-collapse">
        <thead>
          <tr class="border-b border-gray-200 text-gray-500 uppercase text-xs">
            <th class="py-3 px-4 font-medium">Original Name</th>
            <th class="py-3 px-4 font-medium">Proposed Name</th>
            <th class="py-3 px-4 font-medium">Proposed Folder</th>
            <th class="py-3 px-4 font-medium">Confidence</th>
            <th class="py-3 px-4 font-medium">Status</th>
            <th class="py-3 px-4 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each proposals as proposal (proposal.id)}
            <tr class="border-b border-gray-100 hover:bg-gray-50">
              <td class="py-3 px-4 font-mono text-xs">{proposal.original_name}</td>
              <td class="py-3 px-4">{proposal.proposed_name}</td>
              <td class="py-3 px-4 text-gray-600">{proposal.proposed_folder}</td>
              <td class="py-3 px-4">
                <span class={confidenceColor(proposal.confidence)}>
                  {(proposal.confidence * 100).toFixed(0)}%
                </span>
              </td>
              <td class="py-3 px-4">
                <span class={statusBadge(proposal.status)}>{proposal.status}</span>
              </td>
              <td class="py-3 px-4">
                {#if proposal.status === 'pending'}
                  <div class="flex gap-1">
                    <button
                      onclick={() => approve(proposal.id)}
                      class="text-green-600 hover:text-green-800 text-xs font-medium"
                    >
                      Approve
                    </button>
                    <button
                      onclick={() => reject(proposal.id)}
                      class="text-red-600 hover:text-red-800 text-xs font-medium"
                    >
                      Reject
                    </button>
                    <button
                      onclick={() => openCorrection(proposal)}
                      class="text-blue-600 hover:text-blue-800 text-xs font-medium"
                    >
                      Correct
                    </button>
                  </div>
                {:else}
                  <span class="text-gray-400 text-xs">--</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  {#if correcting}
    <CorrectionDialog
      proposal={correcting}
      onSave={handleCorrectionSave}
      onCancel={() => { correcting = null; }}
    />
  {/if}
</div>
