<script lang="ts">
  import { api } from '../lib/api';

  type Step = 'provider' | 'folders' | 'ocr' | 'summary';

  let step = $state<Step>('provider');
  let saving = $state(false);
  let validating = $state(false);
  let validationResult: {
    provider_ok: boolean;
    provider_error: string | null;
    tesseract_ok: boolean;
    ghostscript_ok: boolean;
  } | null = $state(null);

  // Provider step
  let provider: 'anthropic' | 'openai' | 'ollama' = $state('anthropic');
  let apiKey = $state('');
  let ollamaUrl = $state('http://localhost:11434');
  let model = $state('claude-sonnet-4-6');

  // Folders step
  let inputFolder = $state('');
  let outputRoot = $state('');
  let profilesDir = $state('');

  // OCR step
  let language = $state('deu+eng');

  // OCR dependency status (fetched on entering the OCR step, refetchable on demand)
  type DepStatus = {
    run_mode: 'dev' | 'installer';
    tesseract_available: boolean;
    tesseract_path: string | null;
    ghostscript_available: boolean;
    ghostscript_path: string | null;
  };
  let depStatus = $state<DepStatus | null>(null);
  let depLoading = $state(false);
  let depError: string | null = $state(null);

  const ocrRequirementsMet = $derived(
    depStatus !== null &&
      depStatus.tesseract_available &&
      depStatus.ghostscript_available,
  );
  // Dev vs installer context (#52): in an installer build the OCR tools are
  // bundled (DD-06), so a miss means a damaged install that must be repaired —
  // Next stays blocked. In dev the user installs the tools manually, so they
  // may continue and verify later.
  const isInstaller = $derived(depStatus?.run_mode === 'installer');
  const isDev = $derived(depStatus?.run_mode === 'dev');
  const nextDisabled = $derived(
    step === 'ocr' && !ocrRequirementsMet && !isDev,
  );
  const nextDisabledReason = $derived(
    isInstaller
      ? 'Repair the installation to continue (re-run the installer).'
      : 'Install the missing OCR dependencies to continue.',
  );

  async function checkDependencies() {
    depLoading = true;
    depError = null;
    try {
      const status = await api.getSetupStatus();
      depStatus = {
        run_mode: status.run_mode,
        tesseract_available: status.tesseract_available,
        tesseract_path: status.tesseract_path,
        ghostscript_available: status.ghostscript_available,
        ghostscript_path: status.ghostscript_path,
      };
    } catch (err) {
      depError = err instanceof Error ? err.message : String(err);
    } finally {
      depLoading = false;
    }
  }

  // Set sensible defaults for folders
  $effect(() => {
    if (!inputFolder) {
      const home = typeof window !== 'undefined' ? '' : '';
      inputFolder = '~/zerobox/inbox';
      outputRoot = '~/zerobox/archive';
      profilesDir = '~/zerobox/profiles';
    }
  });

  // Auto-check OCR dependencies when the user first enters the OCR step
  $effect(() => {
    if (step === 'ocr' && depStatus === null && !depLoading && depError === null) {
      checkDependencies();
    }
  });

  const providerModels: Record<string, { label: string; defaultModel: string }> = {
    anthropic: { label: 'Anthropic (Claude)', defaultModel: 'claude-sonnet-4-6' },
    openai: { label: 'OpenAI (GPT)', defaultModel: 'gpt-4o' },
    ollama: { label: 'Ollama (Local)', defaultModel: 'llama3' },
  };

  function onProviderChange() {
    model = providerModels[provider].defaultModel;
  }

  async function validate() {
    validating = true;
    validationResult = null;
    try {
      validationResult = await api.validateSetup({
        provider,
        api_key: apiKey,
        ollama_base_url: ollamaUrl,
      });
    } catch {
      // Error shown via toast
    } finally {
      validating = false;
    }
  }

  async function save() {
    saving = true;
    try {
      await api.saveSetup({
        input_folder: inputFolder,
        output_root: outputRoot,
        profiles_dir: profilesDir,
        language,
        provider,
        model,
        api_key: apiKey,
        ollama_base_url: ollamaUrl,
      });
      // Reload the app to enter normal mode
      window.location.reload();
    } catch {
      // Error shown via toast
    } finally {
      saving = false;
    }
  }

  function next() {
    if (step === 'provider') step = 'folders';
    else if (step === 'folders') step = 'ocr';
    else if (step === 'ocr') step = 'summary';
  }

  function back() {
    if (step === 'folders') step = 'provider';
    else if (step === 'ocr') step = 'folders';
    else if (step === 'summary') step = 'ocr';
  }

  const steps: { id: Step; label: string }[] = [
    { id: 'provider', label: 'LLM Provider' },
    { id: 'folders', label: 'Folders' },
    { id: 'ocr', label: 'OCR' },
    { id: 'summary', label: 'Summary' },
  ];

  function stepIndex(s: Step): number {
    return steps.findIndex((x) => x.id === s);
  }
</script>

<div class="min-h-screen bg-gray-50 flex items-center justify-center p-6">
  <div class="w-full max-w-xl bg-white rounded-lg shadow-lg overflow-hidden">
    <!-- Header -->
    <div class="bg-indigo-600 px-6 py-4">
      <h1 class="text-lg font-bold text-white">zerobox Setup</h1>
      <p class="text-indigo-200 text-sm mt-1">Configure your document processing pipeline</p>
    </div>

    <!-- Step indicator -->
    <div class="px-6 py-3 bg-gray-50 border-b border-gray-200">
      <div class="flex gap-2">
        {#each steps as s, i (s.id)}
          <div class="flex items-center gap-2">
            <span
              class="w-6 h-6 rounded-full text-xs font-medium flex items-center justify-center
                {stepIndex(step) >= i
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 text-gray-500'}"
            >
              {i + 1}
            </span>
            <span class="text-xs text-gray-600 hidden sm:inline">{s.label}</span>
            {#if i < steps.length - 1}
              <span class="text-gray-300 mx-1">/</span>
            {/if}
          </div>
        {/each}
      </div>
    </div>

    <!-- Content -->
    <div class="p-6 space-y-4">
      <!-- Step 1: Provider -->
      {#if step === 'provider'}
        <div class="space-y-4">
          <div>
            <label for="provider" class="block text-sm font-medium text-gray-700">LLM Provider</label>
            <select
              id="provider"
              bind:value={provider}
              onchange={onProviderChange}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-2 border"
            >
              {#each Object.entries(providerModels) as [key, val]}
                <option value={key}>{val.label}</option>
              {/each}
            </select>
          </div>

          {#if provider !== 'ollama'}
            <div>
              <label for="apiKey" class="block text-sm font-medium text-gray-700">API Key</label>
              <input
                id="apiKey"
                type="password"
                bind:value={apiKey}
                placeholder={provider === 'anthropic' ? 'sk-ant-...' : 'sk-...'}
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-2 border"
              />
            </div>
          {:else}
            <div>
              <label for="ollamaUrl" class="block text-sm font-medium text-gray-700">Ollama URL</label>
              <input
                id="ollamaUrl"
                type="text"
                bind:value={ollamaUrl}
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-2 border"
              />
            </div>
          {/if}

          <div>
            <label for="model" class="block text-sm font-medium text-gray-700">Model</label>
            <input
              id="model"
              type="text"
              bind:value={model}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-2 border"
            />
          </div>

          <!-- Test connection -->
          <div class="pt-2">
            <button
              onclick={validate}
              disabled={validating}
              class="text-sm text-indigo-600 hover:text-indigo-800 disabled:text-gray-400"
            >
              {validating ? 'Testing...' : 'Test connection'}
            </button>
            {#if validationResult}
              <p class="mt-1 text-sm {validationResult.provider_ok ? 'text-green-600' : 'text-red-600'}">
                {validationResult.provider_ok
                  ? 'Connection successful'
                  : validationResult.provider_error ?? 'Connection failed'}
              </p>
            {/if}
          </div>
        </div>

      <!-- Step 2: Folders -->
      {:else if step === 'folders'}
        <div class="space-y-4">
          <div>
            <label for="inputFolder" class="block text-sm font-medium text-gray-700">Input Folder (Inbox)</label>
            <input
              id="inputFolder"
              type="text"
              bind:value={inputFolder}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-2 border font-mono"
            />
            <p class="mt-1 text-xs text-gray-500">Drop scanned files here for processing</p>
          </div>

          <div>
            <label for="outputRoot" class="block text-sm font-medium text-gray-700">Output Folder (Archive)</label>
            <input
              id="outputRoot"
              type="text"
              bind:value={outputRoot}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-2 border font-mono"
            />
            <p class="mt-1 text-xs text-gray-500">Classified files are moved here</p>
          </div>

          <div>
            <label for="profilesDir" class="block text-sm font-medium text-gray-700">Profiles Folder</label>
            <input
              id="profilesDir"
              type="text"
              bind:value={profilesDir}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-2 border font-mono"
            />
            <p class="mt-1 text-xs text-gray-500">JSON rule profiles are stored here</p>
          </div>
        </div>

      <!-- Step 3: OCR -->
      {:else if step === 'ocr'}
        <div class="space-y-4">
          <div>
            <label for="language" class="block text-sm font-medium text-gray-700">OCR Language(s)</label>
            <input
              id="language"
              type="text"
              bind:value={language}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm p-2 border font-mono"
            />
            <p class="mt-1 text-xs text-gray-500">
              Tesseract language codes, e.g. <code class="bg-gray-100 px-1 rounded">deu+eng</code> for German + English
            </p>
          </div>

          <!-- Dependency status (auto-fetched on OCR step entry; user can re-check) -->
          <div class="pt-2 space-y-2">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-medium text-gray-700">OCR Requirements</h3>
              <button
                onclick={checkDependencies}
                disabled={depLoading}
                class="text-xs text-indigo-600 hover:text-indigo-800 disabled:text-gray-400"
              >
                {depLoading ? 'Checking...' : 'Check requirements'}
              </button>
            </div>

            {#if depLoading && depStatus === null}
              <p class="text-sm text-gray-500">Checking dependencies...</p>
            {:else if depError}
              <p class="text-sm text-red-600">Could not check dependencies: {depError}</p>
            {:else if depStatus}
              <div class="space-y-2">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full {depStatus.tesseract_available ? 'bg-green-500' : 'bg-red-500'}"></span>
                  <span class="text-sm text-gray-700">
                    Tesseract OCR: {depStatus.tesseract_available ? 'Found' : 'Not found'}
                  </span>
                  {#if depStatus.tesseract_path}
                    <span class="text-xs text-gray-400 font-mono">{depStatus.tesseract_path}</span>
                  {/if}
                </div>
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full {depStatus.ghostscript_available ? 'bg-green-500' : 'bg-red-500'}"></span>
                  <span class="text-sm text-gray-700">
                    Ghostscript: {depStatus.ghostscript_available ? 'Found' : 'Not found'}
                  </span>
                  {#if depStatus.ghostscript_path}
                    <span class="text-xs text-gray-400 font-mono">{depStatus.ghostscript_path}</span>
                  {/if}
                </div>
                {#if !ocrRequirementsMet}
                  {#if isInstaller}
                    <div class="mt-2 rounded-md bg-red-50 border border-red-200 p-3">
                      <p class="text-xs text-red-700 font-medium">
                        Damaged installation
                      </p>
                      <p class="text-xs text-red-700 mt-1">
                        These OCR components ship with the zerobox installer, so they should never be missing on an installed build. This indicates an incomplete or damaged installation. Please repair zerobox by re-running the installer, then click "Check requirements" again.
                      </p>
                    </div>
                  {:else}
                    <p class="text-xs text-amber-600 mt-2">
                      OCR is required for zerobox to process scans. As you are running from source, install the missing tools yourself — see the Prerequisites section in README.md — then click "Check requirements" to re-verify. You may continue setup now and verify later.
                    </p>
                  {/if}
                {/if}
              </div>
            {/if}
          </div>
        </div>

      <!-- Step 4: Summary -->
      {:else if step === 'summary'}
        <div class="space-y-3">
          <h3 class="text-sm font-medium text-gray-700">Review your configuration</h3>
          <dl class="divide-y divide-gray-100">
            <div class="py-2 flex justify-between">
              <dt class="text-sm text-gray-500">Provider</dt>
              <dd class="text-sm text-gray-900">{providerModels[provider].label}</dd>
            </div>
            <div class="py-2 flex justify-between">
              <dt class="text-sm text-gray-500">Model</dt>
              <dd class="text-sm text-gray-900 font-mono">{model}</dd>
            </div>
            <div class="py-2 flex justify-between">
              <dt class="text-sm text-gray-500">API Key</dt>
              <dd class="text-sm text-gray-900 font-mono">
                {provider === 'ollama' ? '(not needed)' : apiKey ? '***' + apiKey.slice(-4) : '(not set)'}
              </dd>
            </div>
            <div class="py-2 flex justify-between">
              <dt class="text-sm text-gray-500">Input Folder</dt>
              <dd class="text-sm text-gray-900 font-mono">{inputFolder}</dd>
            </div>
            <div class="py-2 flex justify-between">
              <dt class="text-sm text-gray-500">Output Folder</dt>
              <dd class="text-sm text-gray-900 font-mono">{outputRoot}</dd>
            </div>
            <div class="py-2 flex justify-between">
              <dt class="text-sm text-gray-500">OCR Language</dt>
              <dd class="text-sm text-gray-900 font-mono">{language}</dd>
            </div>
          </dl>
        </div>
      {/if}
    </div>

    <!-- Footer / Navigation -->
    <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
      {#if step !== 'provider'}
        <button
          onclick={back}
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Back
        </button>
      {:else}
        <div></div>
      {/if}

      {#if step === 'summary'}
        <button
          onclick={save}
          disabled={saving}
          class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Finish Setup'}
        </button>
      {:else}
        <div class="flex flex-col items-end gap-1">
          <button
            onclick={next}
            disabled={nextDisabled}
            title={nextDisabled ? nextDisabledReason : ''}
            class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
          </button>
          {#if nextDisabled}
            <span class="text-xs text-amber-600">{nextDisabledReason}</span>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div>
