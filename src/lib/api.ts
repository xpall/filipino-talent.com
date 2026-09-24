const API_BASE = (import.meta.env.PUBLIC_API_BASE ?? 'https://api.filipino-talent.com').replace(/\/$/, '');

export interface Domain {
  subdomain: string;
  portfolio_url: string | null;
  github_username: string | null;
  record_type: string;
  record_value: string;
  status: string;
  created_at: string;
}

export async function fetchDomains(): Promise<Domain[]> {
  try {
    const res = await fetch(`${API_BASE}/domains`);
    if (!res.ok) return [];
    const data = (await res.json()) as { domains?: Domain[] };
    return data.domains ?? [];
  } catch {
    return [];
  }
}

export async function submitRequest(payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data } as {
    ok: boolean;
    status: number;
    data: Record<string, unknown>;
  };
}

export { API_BASE };
