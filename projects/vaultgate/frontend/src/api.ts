export type Session = { token: string; org_id: string; user_id: string };
export type FileRow = { id: string; name: string; content_type: string; size: number };
export type AuditRow = { id: number; actor_id: string; action: string; detail: Record<string, unknown>; created_at: string };

async function request<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string>) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init?.body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) throw new Error(`${response.status}: ${(await response.text()).slice(0, 160)}`);
  return (await response.json()) as T;
}

export const api = {
  login: (user_id: string, password: string) =>
    request<Session>("/api/login", undefined, { method: "POST", body: JSON.stringify({ user_id, password }) }),
  files: (token: string) => request<{ files: FileRow[] }>("/api/files", token),
  audit: (token: string) => request<{ audit: AuditRow[] }>("/api/audit", token),
  file: (token: string, id: string) => request<FileRow>(`/api/files/${id}`, token),
  sign: (token: string, id: string) =>
    request<{ file_id: string; exp: number; sig: string }>(`/api/files/${id}/sign`, token, { method: "POST" }),
  logout: (token: string) => request<{ ok: boolean }>("/api/logout", token, { method: "POST" })
};

export async function downloadFile(token: string, id: string) {
  const signed = await api.sign(token, id);
  const response = await fetch(`/api/download?file_id=${signed.file_id}&exp=${signed.exp}&sig=${signed.sig}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
}
