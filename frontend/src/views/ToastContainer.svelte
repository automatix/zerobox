<script lang="ts">
  import { getToasts, removeToast, type Toast } from '../lib/toast.svelte';

  function typeClasses(type: Toast['type']): string {
    switch (type) {
      case 'success':
        return 'bg-green-600 text-white';
      case 'error':
        return 'bg-red-600 text-white';
      case 'info':
        return 'bg-blue-600 text-white';
    }
  }
</script>

<div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
  {#each getToasts() as toast (toast.id)}
    <div
      class="flex items-center justify-between gap-3 px-4 py-3 rounded shadow-lg text-sm {typeClasses(toast.type)}"
      role="alert"
    >
      <span>{toast.message}</span>
      <button
        onclick={() => removeToast(toast.id)}
        class="shrink-0 opacity-80 hover:opacity-100 text-lg leading-none"
        aria-label="Dismiss"
      >&times;</button>
    </div>
  {/each}
</div>
