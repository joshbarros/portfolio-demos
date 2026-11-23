import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Detail, type Execution } from "./api";

const SCENARIOS = [
  { mode: "happy", label: "Valid event", hint: "Signature ok, all steps succeed" },
  { mode: "transient", label: "Transient failure", hint: "Service fails twice, retry recovers" },
  { mode: "permanent", label: "Permanent failure", hint: "422 stops the flow, goes to dead" },
  { mode: "timeout", label: "Timeout", hint: "Step times out and is retried" },
  { mode: "duplicate", label: "Duplicate delivery", hint: "Same event twice, one action" }
];

function badge(status: string) {
  return <span className={`pill pill-${status}`}>{status}</span>;
}

function duration(value: number | null) {
  if (value == null) return "—";
  return value < 1000 ? `${Math.round(value)} ms` : `${(value / 1000).toFixed(1)} s`;
}

export default function App() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.list();
      setExecutions(data.executions);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 1500);
    return () => clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    let alive = true;
    const load = async () => {
      try {
        const data = await api.detail(selected);
        if (alive) setDetail(data);
      } catch {
        /* execution may be mid-update */
      }
    };
    void load();
    const timer = setInterval(() => void load(), 1200);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [selected]);

  const send = async (mode: string) => {
    setBusy(mode);
    try {
      const result = await api.demo(mode);
      setSelected(result.execution_id);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const replay = async () => {
    if (!detail) return;
    setBusy("replay");
    try {
      const result = await api.replay(detail.execution.id);
      setSelected(result.execution_id);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const stats = useMemo(() => {
    const total = executions.length;
    const ok = executions.filter((e) => e.status === "succeeded").length;
    const dead = executions.filter((e) => e.status === "dead").length;
    return { total, ok, dead };
  }, [executions]);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <svg viewBox="0 0 24 24" className="mark" aria-hidden="true">
            <path d="M4 12h4l2-6 4 12 2-6h4" />
          </svg>
          <div>
            <h1>Hookline</h1>
            <p>Signed webhooks · durable executions · retries with jitter · audit trail</p>
          </div>
        </div>
        <div className="topbar-right">
          <span className="pill pill-demo">Case 02 · personal demo</span>
          <span className="stats">{stats.total} events · {stats.ok} ok · {stats.dead} dead</span>
        </div>
      </header>

      <aside className="sidebar">
        <h2>Trigger a signed event</h2>
        <div className="scenarios">
          {SCENARIOS.map((scenario) => (
            <button
              key={scenario.mode}
              className="scenario"
              onClick={() => void send(scenario.mode)}
              disabled={busy !== null}
            >
              <span>{scenario.label}</span>
              <small>{scenario.hint}</small>
            </button>
          ))}
        </div>
        <div className="legend">
          <h2>Delivery semantics</h2>
          <p>
            At-least-once. The event is stored before processing, and each step that supports an idempotency key is
            safe to retry. Notifications are deliberately not idempotent — the UI shows the duplicate when it happens.
          </p>
        </div>
      </aside>

      <main className="list">
        <div className="list-head">
          <h2>Executions</h2>
          <button className="ghost" onClick={() => void refresh()}>Refresh</button>
        </div>
        {error && <div className="error">{error}</div>}
        <div className="rows">
          {executions.length === 0 && <p className="muted">No events yet. Trigger one on the left.</p>}
          {executions.map((execution) => (
            <button
              key={execution.id}
              className={execution.id === selected ? "row row-active" : "row"}
              onClick={() => setSelected(execution.id)}
            >
              <div className="row-main">
                <code>{execution.event_external_id ?? execution.event_id.slice(0, 8)}</code>
                <small>{new Date(execution.created_at).toLocaleTimeString()}</small>
              </div>
              <div className="row-meta">
                {badge(execution.status)}
                <small>{execution.attempts} attempt(s) · {duration(execution.duration_ms)}</small>
              </div>
            </button>
          ))}
        </div>
      </main>

      <section className="detail">
        {!detail && <p className="muted">Select an execution to see steps, attempts and the final effect.</p>}
        {detail && (
          <>
            <div className="detail-head">
              <div>
                <h2>{detail.event.external_id}</h2>
                <p>{detail.execution.flow} · created {new Date(detail.execution.created_at).toLocaleTimeString()}</p>
              </div>
              {badge(detail.execution.status)}
            </div>

            <div className="facts">
              <div><span>Attempts</span><strong>{detail.execution.attempts} / {detail.execution.max_attempts}</strong></div>
              <div><span>Duration</span><strong>{duration(detail.execution.duration_ms)}</strong></div>
              <div><span>Replays</span><strong>{detail.execution.replay_count}</strong></div>
            </div>

            {detail.execution.last_error && <div className="error">{detail.execution.last_error}</div>}

            <h3>Steps</h3>
            <div className="steps">
              {detail.steps.map((step) => (
                <div className={`step step-${step.status}`} key={step.id}>
                  <div className="step-head">
                    <strong>{step.name}</strong>
                    {badge(step.status)}
                    <small>{step.attempts} attempt(s)</small>
                  </div>
                  {step.error && <p className="step-error">{step.error}</p>}
                  {step.response != null && <pre>{JSON.stringify(step.response, null, 2)}</pre>}
                </div>
              ))}
            </div>

            <h3>Event payload</h3>
            <pre className="payload">{JSON.stringify(detail.event.payload, null, 2)}</pre>

            <div className="actions">
              <button className="primary" onClick={() => void replay()} disabled={busy !== null || !["dead", "succeeded"].includes(detail.execution.status)}>
                Replay execution
              </button>
              <small>Replay creates a new execution for the same stored event.</small>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
