const BASE_URL = 'http://127.0.0.1:8000';

export async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  // Pipeline
  runPipeline: () => fetchJson('/pipeline/run', { method: 'POST' }),
  runAndExecute: (autoApprove = false) =>
    fetchJson(`/pipeline/run-and-execute?auto_approve=${autoApprove}`, { method: 'POST' }),

  // Proposals
  getProposals: (status?: string) =>
    fetchJson(`/proposals${status ? `?status=${status}` : ''}`),
  getProposal: (id: string) => fetchJson(`/proposals/${id}`),
  updateProposal: (id: string, body: Record<string, unknown>) =>
    fetchJson(`/proposals/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  executeProposals: () => fetchJson('/proposals/execute', { method: 'POST' }),

  // Rules
  getProfiles: () => fetchJson('/rules/profiles'),
  getProfile: (id: string) => fetchJson(`/rules/profiles/${id}`),
  createProfile: (body: Record<string, unknown>) =>
    fetchJson('/rules/profiles', { method: 'POST', body: JSON.stringify(body) }),
  deleteProfile: (id: string) => fetchJson(`/rules/profiles/${id}`, { method: 'DELETE' }),
  addRule: (profileId: string, body: Record<string, unknown>) =>
    fetchJson(`/rules/profiles/${profileId}/rules`, { method: 'POST', body: JSON.stringify(body) }),
  deleteRule: (profileId: string, ruleId: string) =>
    fetchJson(`/rules/profiles/${profileId}/rules/${ruleId}`, { method: 'DELETE' }),

  // Audit
  getAuditLog: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJson(`/audit/log${query}`);
  },

  // Config
  getConfig: () => fetchJson('/config'),
};
