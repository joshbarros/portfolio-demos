export type Execution = {
  id: string;
  event_id: string;
  event_external_id?: string;
  event_type?: string;
  flow: string;
  status: "queued" | "running" | "retrying" | "succeeded" | "dead";
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  replay_count: number;
  created_at: string;
  finished_at: string | null;
  duration_ms: number | null;
};

export type Step = {
  id: string;
  name: string;
  position: number;
  status: "pending" | "running" | "succeeded" | "retrying" | "failed" | "skipped";
  attempts: number;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  response: unknown;
};

export type Detail = {
  execution: Execution;
  steps: Step[];
  event: { external_id: string; type: string; payload: unknown; received_at: string };
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) throw new Error(`${response.status} ${(await response.text()).slice(0, 160)}`);
  return (await response.json()) as T;
}

export const api = {
  list: () => request<{ executions: Execution[] }>("/api/executions"),
  detail: (id: string) => request<Detail>(`/api/executions/${id}`),
  demo: (mode: string) => request<{ execution_id: string }>("/api/demo", { method: "POST", body: JSON.stringify({ mode }) }),
  replay: (id: string) => request<{ execution_id: string }>(`/api/executions/${id}/replay`, { method: "POST" })
};
