import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type AuditEntry, type ChatResponse, type Ticket, type Tenant } from "./api";

type Turn = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  response?: ChatResponse;
};

const SCENARIOS = [
  {
    id: "answer",
    label: "Answer with source",
    prompt: "How do I reset the thermostat?"
  },
  {
    id: "abstain",
    label: "Abstain honestly",
    prompt: "Do you accept cryptocurrency payments?"
  },
  {
    id: "tool",
    label: "Auditable action",
    prompt: "Please open a ticket about a broken thermostat"
  },
  {
    id: "isolation",
    label: "Tenant isolation",
    prompt: "How long does shipping take?"
  }
];

function Compass() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="brand-mark">
      <circle cx="12" cy="12" r="9.25" />
      <path d="M15.4 8.6l-2.1 4.8-4.8 2.1 2.1-4.8z" />
    </svg>
  );
}

function Icon({ name }: { name: "send" | "doc" | "ticket" | "shield" | "spark" | "check" }) {
  const paths: Record<string, JSX.Element> = {
    send: <path d="M4 12l16-7-7 16-2.2-6.8z" />,
    doc: (
      <>
        <path d="M7 3.5h6l4 4v13H7z" />
        <path d="M13 3.5v4h4" />
      </>
    ),
    ticket: (
      <>
        <path d="M4 8.5a2 2 0 012-2h12a2 2 0 012 2 2 2 0 000 4 2 2 0 000 4 2 2 0 01-2 2H6a2 2 0 01-2-2 2 2 0 000-4 2 2 0 000-4z" />
        <path d="M14 6.5v11" strokeDasharray="2 2.5" />
      </>
    ),
    shield: <path d="M12 3.5l7 2.5v6c0 4.2-2.9 7.4-7 8.5-4.1-1.1-7-4.3-7-8.5v-6z" />,
    spark: <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" />,
    check: <path d="M5 12.5l4.5 4.5L19 7.5" />
  };
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="icon">
      {paths[name]}
    </svg>
  );
}

export default function App() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState("demo-electric");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"sources" | "tickets" | "audit">("sources");
  const [mode, setMode] = useState("demo");
  const sessionId = useMemo(() => `web-${Math.random().toString(36).slice(2, 8)}`, []);
  const scroller = useRef<HTMLDivElement>(null);

  const tenant = tenants.find((t) => t.id === tenantId);

  const refresh = useCallback(
    async (id: string) => {
      const [nextTickets, nextAudit] = await Promise.all([api.tickets(id), api.audit(id)]);
      setTickets(nextTickets);
      setAudit(nextAudit);
    },
    []
  );

  useEffect(() => {
    Promise.all([api.tenants(), api.health()])
      .then(([list, health]) => {
        setTenants(list);
        setMode(health.mode);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    refresh(tenantId).catch((err: Error) => setError(err.message));
  }, [tenantId, refresh]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || busy) return;
    setError(null);
    setBusy(true);
    setInput("");
    const turn: Turn = { id: crypto.randomUUID(), role: "user", text: message };
    setTurns((prev) => [...prev, turn]);
    try {
      const response = await api.chat(tenantId, sessionId, message);
      setTurns((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", text: response.answer, response }
      ]);
      if (response.citations.length) setTab("sources");
      await refresh(tenantId);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const lastCitations = useMemo(() => {
    for (let i = turns.length - 1; i >= 0; i -= 1) {
      const response = turns[i].response;
      if (response) return response.citations;
    }
    return [];
  }, [turns]);

  const switchTenant = (id: string) => {
    const name = tenants.find((item) => item.id === id)?.name ?? id;
    setTenantId(id);
    setTab("sources");
    setTurns([
      {
        id: crypto.randomUUID(),
        role: "system",
        text: `Switched to ${name}. History is scoped to this tenant.`
      }
    ]);
  };

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <Compass />
          <div>
            <h1>Northstar Agent</h1>
            <p>Support agent · citations · abstention · auditable actions</p>
          </div>
        </div>
        <div className="topbar-right">
          <span className="pill pill-demo">Personal demo project</span>
          <span className="status">
            <i className={error ? "dot dot-bad" : "dot"} />
            {error ? "offline" : `online · ${mode}`}
          </span>
        </div>
      </header>

      <aside className="sidebar">
        <section>
          <h2>Workspace</h2>
          <div className="tenant-list">
            {tenants.map((item) => (
              <button
                key={item.id}
                className={item.id === tenantId ? "tenant tenant-active" : "tenant"}
                onClick={() => switchTenant(item.id)}
                type="button"
              >
                <span className="tenant-avatar">{item.name.slice(0, 1)}</span>
                <span className="tenant-meta">
                  <strong>{item.name}</strong>
                  <small>{item.id}</small>
                </span>
              </button>
            ))}
          </div>
        </section>

        <section>
          <h2>Demo scenarios</h2>
          <div className="scenario-list">
            {SCENARIOS.map((scenario) => (
              <button
                key={scenario.id}
                type="button"
                className="scenario"
                onClick={() => send(scenario.prompt)}
                disabled={busy}
              >
                <span>{scenario.label}</span>
                <small>{scenario.prompt}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="sidebar-foot">
          <h2>Guarantees</h2>
          <ul>
            <li>
              <Icon name="check" /> Answer only from indexed documents
            </li>
            <li>
              <Icon name="check" /> Cite document, source and update date
            </li>
            <li>
              <Icon name="check" /> Abstain when evidence is missing
            </li>
            <li>
              <Icon name="check" /> Tenant filter enforced in the query
            </li>
            <li>
              <Icon name="check" /> Every tool call written to the audit log
            </li>
          </ul>
        </section>
      </aside>

      <main className="chat">
        <div className="chat-head">
          <div>
            <h2>{tenant?.name ?? "Loading workspace"}</h2>
            <p>Session {sessionId} · answers grounded in this tenant&apos;s documents only</p>
          </div>
          <span className="pill">{tickets.length} tickets</span>
        </div>

        <div className="transcript" ref={scroller}>
          {turns.length === 0 && (
            <div className="empty">
              <Icon name="spark" />
              <h3>Ask a support question</h3>
              <p>
                Pick a demo scenario or type a question below. The agent answers only from the demo
                knowledge base, cites what it used, and says so when it does not know.
              </p>
            </div>
          )}

          {turns.map((turn) =>
            turn.role === "system" ? (
              <div className="divider" key={turn.id}>
                {turn.text}
              </div>
            ) : turn.role === "user" ? (
              <div className="bubble bubble-user" key={turn.id}>
                {turn.text}
              </div>
            ) : (
              <article className="bubble bubble-assistant" key={turn.id}>
                {turn.response?.abstained && (
                  <div className="flag flag-abstain">
                    <Icon name="shield" />
                    No supporting evidence — the agent abstained instead of guessing.
                  </div>
                )}
                {turn.response?.tool_calls.some((call) => call.name === "create_ticket") && (
                  <div className="flag flag-tool">
                    <Icon name="ticket" />
                    Tool <code>create_ticket</code> executed and written to the audit log.
                  </div>
                )}
                <p>{turn.text}</p>
                {!!turn.response?.citations.length && (
                  <div className="citations">
                    {turn.response.citations.map((citation) => (
                      <details key={`${turn.id}-${citation.document_id}`} className="citation">
                        <summary>
                          <Icon name="doc" />
                          <span>{citation.title}</span>
                          <small>
                            {citation.source} · updated {citation.updated_at}
                          </small>
                        </summary>
                        <p>{citation.excerpt}</p>
                        <footer>
                          <code>{citation.document_id}</code>
                          <span>relevance {citation.score.toFixed(3)}</span>
                        </footer>
                      </details>
                    ))}
                  </div>
                )}
              </article>
            )
          )}

          {busy && (
            <div className="bubble bubble-assistant typing">
              <span />
              <span />
              <span />
            </div>
          )}
        </div>

        {error && <div className="error">{error}</div>}

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            void send(input);
          }}
        >
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about reset, warranty, refunds, shipping…"
            aria-label="Message"
          />
          <button type="submit" disabled={busy || !input.trim()}>
            <Icon name="send" />
            Send
          </button>
        </form>
      </main>

      <aside className="evidence">
        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "sources"}
            className={tab === "sources" ? "tab tab-active" : "tab"}
            onClick={() => setTab("sources")}
          >
            Sources
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "tickets"}
            className={tab === "tickets" ? "tab tab-active" : "tab"}
            onClick={() => setTab("tickets")}
          >
            Tickets
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "audit"}
            className={tab === "audit" ? "tab tab-active" : "tab"}
            onClick={() => setTab("audit")}
          >
            Audit
          </button>
        </div>

        <div className="evidence-body">
          {tab === "sources" &&
            (lastCitations.length === 0 ? (
              <p className="muted">Citations appear here after an answer with evidence.</p>
            ) : (
              lastCitations.map((citation) => (
                <div className="card" key={citation.document_id}>
                  <h3>{citation.title}</h3>
                  <p>{citation.excerpt}</p>
                  <footer>
                    <code>{citation.source}</code>
                    <span>{citation.updated_at}</span>
                  </footer>
                </div>
              ))
            ))}

          {tab === "tickets" &&
            (tickets.length === 0 ? (
              <p className="muted">No tickets yet. Run the auditable action scenario.</p>
            ) : (
              tickets.map((ticket) => (
                <div className="card" key={ticket.id}>
                  <h3>
                    <code>{ticket.id}</code>
                    <span className={`badge badge-${ticket.priority}`}>{ticket.priority}</span>
                  </h3>
                  <p>{ticket.subject}</p>
                  <footer>
                    <span>{ticket.status}</span>
                    <span>{ticket.created_at.replace("T", " ").slice(0, 19)}</span>
                  </footer>
                </div>
              ))
            ))}

          {tab === "audit" &&
            (audit.length === 0 ? (
              <p className="muted">Tool calls and their results are recorded here.</p>
            ) : (
              audit.map((entry) => (
                <div className="card card-audit" key={entry.id}>
                  <h3>
                    <code>{entry.action}</code>
                    <span className="muted">{entry.created_at.replace("T", " ").slice(11, 19)}</span>
                  </h3>
                  <pre>{entry.args}</pre>
                  <footer>
                    <span>{entry.result}</span>
                  </footer>
                </div>
              ))
            ))}
        </div>
      </aside>
    </div>
  );
}
