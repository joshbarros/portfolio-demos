export type User = { id: string; name: string; role: "technician" | "reviewer" };
export type Client = { id: string; name: string; address: string };
export type Service = { id: string; name: string; unit_price_cents: number };
export type Ticket = {
  id: string;
  number: number;
  status: "draft" | "submitted" | "approved" | "rejected" | "invoiced";
  notes: string;
  client_name: string;
  technician_name: string;
  total_cents: number;
  created_at: string;
};
export type TicketDetail = {
  ticket: Ticket & { client_address: string; approved_by: string | null; approved_at: string | null };
  items: { id: string; description: string; quantity: number; unit_price_cents: number }[];
  audit: { id: number; action: string; actor_name: string; created_at: string; detail: unknown }[];
  invoice: { id: string; number: number; total_cents: number; issued_at: string } | null;
};
export type Invoice = {
  id: string;
  number: number;
  total_cents: number;
  currency: string;
  issued_at: string;
  ticket_id: string;
  ticket_number: number;
};

async function request<T>(path: string, userId: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "x-user-id": userId, ...((init?.headers as Record<string, string>) ?? {}) };
  if (init?.body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) throw new Error(`${response.status} ${(await response.text()).slice(0, 160)}`);
  return (await response.json()) as T;
}

export const api = {
  users: () => fetch("/api/users").then((r) => r.json() as Promise<{ users: User[] }>),
  clients: (id: string) => request<{ clients: Client[] }>("/api/clients", id),
  services: (id: string) => request<{ services: Service[] }>("/api/services", id),
  tickets: (id: string) => request<{ tickets: Ticket[] }>("/api/tickets", id),
  ticket: (id: string, ticketId: string) => request<TicketDetail>(`/api/tickets/${ticketId}`, id),
  create: (id: string, body: unknown) =>
    request<Ticket>("/api/tickets", id, { method: "POST", body: JSON.stringify(body) }),
  submit: (id: string, ticketId: string) =>
    request<Ticket>(`/api/tickets/${ticketId}/submit`, id, { method: "POST" }),
  review: (id: string, ticketId: string, decision: "approve" | "reject") =>
    request<Ticket>(`/api/tickets/${ticketId}/review`, id, {
      method: "POST",
      body: JSON.stringify({ decision })
    }),
  invoice: (id: string, ticketId: string) =>
    request<{ id: string; number: number; total_cents: number }>(`/api/tickets/${ticketId}/invoice`, id, {
      method: "POST"
    }),
  invoices: (id: string) => request<{ invoices: Invoice[] }>("/api/invoices", id),
  dashboard: (id: string) =>
    request<{ by_status: { status: string; count: number }[]; invoices: { invoices: number; total_cents: number } }>(
      "/api/dashboard",
      id
    )
};

export function money(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
}
