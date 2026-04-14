<script lang="ts">
  import type { Proposal } from '../lib/types';

  interface Props {
    proposal: Proposal;
    onSave: (updated: { proposed_name: string; proposed_folder: string }) => void;
    onCancel: () => void;
  }

  let { proposal, onSave, onCancel }: Props = $props();

  let proposedName = $state('');
  let proposedFolder = $state('');

  // Initialize editable fields from the proposal prop
  $effect(() => {
    proposedName = proposal.proposed_name;
    proposedFolder = proposal.proposed_folder;
  });

  function handleSubmit(e: Event) {
    e.preventDefault();
    onSave({ proposed_name: proposedName, proposed_folder: proposedFolder });
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      onCancel();
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      onCancel();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
  role="presentation"
  class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
  onclick={handleBackdropClick}
>
  <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
    <div class="px-6 py-4 border-b border-gray-200">
      <h3 class="text-lg font-semibold text-gray-900">Correct Proposal</h3>
      <p class="text-sm text-gray-500 mt-1">
        Original: <span class="font-mono">{proposal.original_name}</span>
      </p>
    </div>

    <form onsubmit={handleSubmit} class="px-6 py-4 space-y-4">
      <div>
        <label for="proposed-name" class="block text-sm font-medium text-gray-700 mb-1">
          Proposed Name
        </label>
        <input
          id="proposed-name"
          type="text"
          bind:value={proposedName}
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      <div>
        <label for="proposed-folder" class="block text-sm font-medium text-gray-700 mb-1">
          Proposed Folder
        </label>
        <input
          id="proposed-folder"
          type="text"
          bind:value={proposedFolder}
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      <div class="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onclick={onCancel}
          class="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          class="px-4 py-2 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700 transition-colors"
        >
          Save Correction
        </button>
      </div>
    </form>
  </div>
</div>
