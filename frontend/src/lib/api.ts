import { addToast } from './toast.svelte';

const BASE_URL = 'http://localhost:8000';

export async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let message = `API error: ${res.status}`;
    try {
      const body = await res.json();
      if (body.error) message = body.error;
    } catch {
      // ignore parse errors
    }
    addToast(message, 'error');
    throw new Error(message);
  }
  return res.json();
}

export const api = {
  // Pipeline
  runPipeline: async () => {
    const result = await fetchJson('/pipeline/run', { method: 'POST' });
    addToast('Pipeline started successfully', 'success');
    return result;
  },
  runAndExecute: (autoApprove = false) =>
    fetchJson(`/pipeline/run-and-execute?auto_approve=${autoApprove}`, { method: 'POST' }),

  // Proposals
  getProposals: (status?: string) =>
    fetchJson(`/proposals${status ? `?status=${status}` : ''}`),
  getProposal: (id: string) => fetchJson(`/proposals/${id}`),
  updateProposal: async (id: string, body: Record<string, unknown>) => {
    const result = await fetchJson(`/proposals/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
    const status = body.status as string | undefined;
    if (status) {
      addToast(`Proposal ${status} successfully`, 'success');
    }
    return result;
  },
  executeProposals: async () => {
    const result = await fetchJson('/proposals/execute', { method: 'POST' });
    addToast('Proposals executed successfully', 'success');
    return result;
  },

  // Rules
  getProfiles: () => fetchJson('/rules/profiles'),
  getProfile: (id: string) => fetchJson(`/rules/profiles/${id}`),
  createProfile: async (body: Record<string, unknown>) => {
    const result = await fetchJson('/rules/profiles', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    addToast('Profile created successfully', 'success');
    return result;
  },
  deleteProfile: async (id: string) => {
    const result = await fetchJson(`/rules/profiles/${id}`, { method: 'DELETE' });
    addToast('Profile deleted successfully', 'success');
    return result;
  },
  addRule: async (profileId: string, body: Record<string, unknown>) => {
    const result = await fetchJson(`/rules/profiles/${profileId}/rules`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    addToast('Rule added successfully', 'success');
    return result;
  },
  deleteRule: async (profileId: string, ruleId: string) => {
    const result = await fetchJson(`/rules/profiles/${profileId}/rules/${ruleId}`, {
      method: 'DELETE',
    });
    addToast('Rule deleted successfully', 'success');
    return result;
  },

  // Audit
  getAuditLog: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJson(`/audit/log${query}`);
  },

  // Config
  getConfig: () => fetchJson('/config'),

  // Setup (First-Run-Wizard)
  getSetupStatus: () => fetchJson<{
    setup_complete: boolean;
    has_config: boolean;
    has_env: boolean;
    run_mode: 'dev' | 'installer';
    tesseract_available: boolean;
    tesseract_path: string | null;
    ghostscript_available: boolean;
    ghostscript_path: string | null;
  }>('/setup/status'),

  validateSetup: (body: {
    provider: string;
    api_key?: string;
    ollama_base_url?: string;
  }) => fetchJson<{
    provider_ok: boolean;
    provider_error: string | null;
    tesseract_ok: boolean;
    ghostscript_ok: boolean;
  }>('/setup/validate', { method: 'POST', body: JSON.stringify(body) }),

  saveSetup: (body: {
    input_folder: string;
    output_root: string;
    profiles_dir: string;
    language?: string;
    provider?: string;
    model?: string;
    api_key?: string;
    ollama_base_url?: string;
  }) => fetchJson<{ status: string }>('/setup/save', {
    method: 'POST',
    body: JSON.stringify(body),
  }),
};
