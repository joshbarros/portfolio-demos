import { useEffect, useState } from "react";
import { api, downloadFile, type AuditRow, type FileRow, type Session } from "./api";

const USERS = [
  { id: "user_alpha_admin", label: "Alice Alpha — Alpha Freight (admin)" },
  { id: "user_beta_user", label: "Bob Beta — Beta Clinic (user)" }
];

const ORG_NAMES: Record<string, string> = { org_alpha: "Alpha Freight", org_beta: "Beta Clinic" };
const OTHER_FILE: Record<string, string> = { org_alpha: "file_beta_notes", org_beta: "file_alpha_brief" };

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState(USERS[0].id);
  const [files, setFiles] = useState<FileRow[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = async (active: Session) => {
    const [f, a] = await Promise.all([api.files(active.token), api.audit(active.token)]);
    setFiles(f.files);
    setAudit(a.audit);
  };

  useEffect(() => {
    if (session) {
      void refresh(session).catch((err: Error) => setError(err.message));
    }
  }, [session]);

  const login = async () => {
    setBusy(true);
    setError(null);
    try {
      const active = await api.login(user, "demo");
      setSession(active);
      setNotice(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const logout = async () => {
    if (!session) return;
    await api.logout(session.token).catch(() => {});
    setSession(null);
    setFiles([]);
    setAudit([]);
  };

  const attemptCrossTenant = async () => {
    if (!session) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.file(session.token, OTHER_FILE[session.org_id]);
      setNotice("Unexpected: the other organization's file was returned.");
    } catch (err) {
      setNotice(`Blocked as expected → ${(err as Error).message}`);
    } finally {
      await refresh(session).catch(() => {});
      setBusy(false);
    }
  };

  const download = async (id: string) => {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      await downloadFile(session.token, id);
      await refresh(session);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!session) {
    return (
      <div className="login">
        <div className="card">
          <h1>Vaultgate</h1>
          <p>Multi-tenant client portal · row-level security · audit logs</p>
          <span className="pill">Personal demo project</span>
          <label>
            Sign in as
            <select value={user} onChange={(event) => setUser(event.target.value)}>
              {USERS.map((u) => (
                <option key={u.id} value={u.id}>{u.label}</option>
              ))}
            </select>
          </label>
          <p className="hint">Demo password: <code>demo</code>. Two fictional organizations share one database.</p>
          <button className="primary" onClick={() => void login()} disabled={busy}>
            Sign in
          </button>
          {error && <div className="error">{error}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <svg viewBox="0 0 24 24" className="mark" aria-hidden="true">
            <path d="M12 3l7 3v6c0 4-2.8 7.2-7 8-4.2-.8-7-4-7-8V6z" />
          </svg>
          <div>
            <h1>Vaultgate</h1>
            <p>{ORG_NAMES[session.org_id] ?? session.org_id} · signed in as {session.user_id}</p>
          </div>
        </div>
        <div className="topbar-right">
          <span className="pill">Personal demo project</span>
          <button className="ghost" onClick={() => void attemptCrossTenant()} disabled={busy}>
            Attempt cross-tenant access
          </button>
          <button className="ghost" onClick={() => void logout()}>Sign out</button>
        </div>
      </header>

      <main>
        {notice && <div className={`notice ${notice.startsWith("Blocked") ? "ok" : "bad"}`}>{notice}</div>}
        {error && <div className="error">{error}</div>}

        <section>
          <h2>Authorized files</h2>
          <table>
            <thead><tr><th>Name</th><th>Type</th><th>Size</th><th></th></tr></thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.id}>
                  <td>{file.name}<small>{file.id}</small></td>
                  <td>{file.content_type}</td>
                  <td>{file.size} B</td>
                  <td><button className="ghost" onClick={() => void download(file.id)} disabled={busy}>Download</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h2>Audit trail</h2>
          <p className="hint">The application role can insert events but cannot update or delete them.</p>
          <table>
            <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Detail</th></tr></thead>
            <tbody>
              {audit.map((row) => (
                <tr key={row.id}>
                  <td>{new Date(row.created_at).toLocaleTimeString()}</td>
                  <td>{row.actor_id}</td>
                  <td><code>{row.action}</code></td>
                  <td><small>{JSON.stringify(row.detail)}</small></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}
