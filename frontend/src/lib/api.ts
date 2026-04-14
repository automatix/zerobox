import { addToast } from './toast.svelte';

const BASE_URL = 'http://127.0.0.1:8000';

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
};
