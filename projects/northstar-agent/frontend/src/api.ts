export type Tenant = { id: string; name: string };

export type Citation = {
  document_id: string;
  title: string;
  source: string;
  updated_at: string;
  excerpt: string;
  score: number;
};

export type ToolCall = {
  name: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
};

export type ChatResponse = {
  answer: string;
  citations: Citation[];
  abstained: boolean;
  escalate: boolean;
  tool_calls: ToolCall[];
  mode: string;
};

export type Ticket = {
  id: string;
  tenant_id: string;
  session_id: string;
  subject: string;
  description: string;
  priority: string;
  status: string;
  created_at: string;
};

export type AuditEntry = {
  id: number;
  tenant_id: string;
  session_id: string;
  action: string;
  args: string;
  result: string;
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${detail.slice(0, 160)}`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<{ ok: boolean; mode: string }>("/api/health"),
  tenants: () => request<Tenant[]>("/api/tenants"),
  chat: (tenant_id: string, session_id: string, message: string) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ tenant_id, session_id, message })
    }),
  tickets: (tenant_id: string) =>
    request<Ticket[]>(`/api/tickets?tenant_id=${encodeURIComponent(tenant_id)}`),
  audit: (tenant_id: string) =>
    request<AuditEntry[]>(`/api/audit?tenant_id=${encodeURIComponent(tenant_id)}`)
};
