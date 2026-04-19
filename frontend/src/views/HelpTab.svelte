<script lang="ts">
  import { onMount } from 'svelte';
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';

  type Doc = { id: string; label: string; file: string };

  // Files synced from the repo at build time (see frontend/scripts/sync-docs.mjs)
  const docs: Doc[] = [
    { id: 'user-guide', label: 'User Guide', file: '/docs/user-guide.md' },
    { id: 'readme', label: 'README', file: '/docs/README.md' },
    { id: 'architecture', label: 'Architecture', file: '/docs/architecture.md' },
    { id: 'dev-testing', label: 'Dev Testing', file: '/docs/dev-testing.md' },
    { id: 'roadmap', label: 'Roadmap', file: '/docs/roadmap.md' },
  ];

  let activeId: string = $state(docs[0].id);
  let html: string = $state('');
  let loading: boolean = $state(false);
  let error: string | null = $state(null);

  marked.setOptions({ gfm: true, breaks: false });

  async function load(doc: Doc) {
    loading = true;
    error = null;
    try {
      const resp = await fetch(doc.file);
      if (!resp.ok) {
        throw new Error(`Failed to load ${doc.file}: ${resp.status}`);
      }
      const md = await resp.text();
      const rendered = await marked.parse(md);
      html = DOMPurify.sanitize(rendered);
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : String(e);
      html = '';
    } finally {
      loading = false;
    }
  }

  function select(id: string) {
    activeId = id;
    const doc = docs.find((d) => d.id === id);
    if (doc) load(doc);
  }

  onMount(() => load(docs[0]));
</script>

<div class="flex h-full">
  <!-- Sidebar -->
  <aside class="w-56 shrink-0 border-r border-gray-200 bg-white">
    <div class="px-4 py-3 border-b border-gray-200">
      <h2 class="text-sm font-semibold text-gray-700">Documentation</h2>
    </div>
    <nav class="p-2 space-y-1">
      {#each docs as doc (doc.id)}
        <button
          type="button"
          onclick={() => select(doc.id)}
          class="block w-full text-left px-3 py-2 rounded text-sm transition-colors
            {activeId === doc.id
              ? 'bg-indigo-50 text-indigo-700 font-medium'
              : 'text-gray-700 hover:bg-gray-50'}"
        >
          {doc.label}
        </button>
      {/each}
    </nav>
  </aside>

  <!-- Rendered doc -->
  <article class="flex-1 overflow-auto bg-white">
    <div class="max-w-3xl mx-auto px-8 py-6">
      {#if error}
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
          {error}
        </div>
      {:else if loading}
        <p class="text-sm text-gray-500">Loading…</p>
      {:else}
        <div class="markdown-body">
          {@html html}
        </div>
      {/if}
    </div>
  </article>
</div>

<style>
  /* Lightweight Markdown styling — kept inline so the bundle stays self-contained. */
  :global(.markdown-body) {
    color: #1f2937;
    line-height: 1.6;
    font-size: 0.9rem;
  }
  :global(.markdown-body h1) {
    font-size: 1.6rem;
    font-weight: 700;
    margin: 1.2rem 0 0.8rem;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.4rem;
  }
  :global(.markdown-body h2) {
    font-size: 1.3rem;
    font-weight: 600;
    margin: 1.4rem 0 0.6rem;
  }
  :global(.markdown-body h3) {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 1rem 0 0.5rem;
  }
  :global(.markdown-body p),
  :global(.markdown-body ul),
  :global(.markdown-body ol),
  :global(.markdown-body blockquote),
  :global(.markdown-body table) {
    margin: 0.5rem 0;
  }
  :global(.markdown-body ul),
  :global(.markdown-body ol) {
    padding-left: 1.5rem;
  }
  :global(.markdown-body li) {
    margin: 0.2rem 0;
  }
  :global(.markdown-body code) {
    background: #f3f4f6;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    font-size: 0.85em;
    font-family: ui-monospace, monospace;
  }
  :global(.markdown-body pre) {
    background: #f3f4f6;
    padding: 0.8rem;
    border-radius: 6px;
    overflow-x: auto;
    margin: 0.8rem 0;
  }
  :global(.markdown-body pre code) {
    background: transparent;
    padding: 0;
  }
  :global(.markdown-body table) {
    border-collapse: collapse;
    width: 100%;
  }
  :global(.markdown-body th),
  :global(.markdown-body td) {
    border: 1px solid #e5e7eb;
    padding: 0.4rem 0.6rem;
    text-align: left;
    font-size: 0.85em;
  }
  :global(.markdown-body th) {
    background: #f9fafb;
    font-weight: 600;
  }
  :global(.markdown-body blockquote) {
    border-left: 4px solid #d1d5db;
    padding: 0.2rem 0 0.2rem 1rem;
    color: #4b5563;
    background: #f9fafb;
  }
  :global(.markdown-body a) {
    color: #4f46e5;
    text-decoration: underline;
  }
  :global(.markdown-body hr) {
    border: 0;
    border-top: 1px solid #e5e7eb;
    margin: 1.2rem 0;
  }
</style>
