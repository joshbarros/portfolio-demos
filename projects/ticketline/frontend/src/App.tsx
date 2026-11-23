import { useCallback, useEffect, useMemo, useState } from "react";
import { api, money, type Client, type Invoice, type Service, type Ticket, type TicketDetail, type User } from "./api";

type Tab = "tickets" | "invoices" | "dashboard";

export default function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState("user_tech");
  const [clients, setClients] = useState<Client[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [dashboard, setDashboard] = useState<{ by_status: { status: string; count: number }[]; invoices: { invoices: number; total_cents: number } } | null>(null);
  const [tab, setTab] = useState<Tab>("tickets");
  const [notes, setNotes] = useState("Replaced two thermostats and ran a diagnostic visit.");
  const [clientId, setClientId] = useState("client_harbor");
  const [lines, setLines] = useState<{ serviceId: string; quantity: number }[]>([{ serviceId: "svc_thermostat", quantity: 2 }]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const user = users.find((u) => u.id === userId);
  const isReviewer = user?.role === "reviewer";

  const refresh = useCallback(async () => {
    try {
      const [list, inv, dash] = await Promise.all([api.tickets(userId), api.invoices(userId), api.dashboard(userId)]);
      setTickets(list.tickets);
      setInvoices(inv.invoices);
      setDashboard(dash);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [userId]);

  useEffect(() => {
    api.users().then((data) => setUsers(data.users)).catch(() => {});
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 4000);
    return () => clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!userId) return;
    api.clients(userId).then((data) => setClients(data.clients)).catch(() => {});
    api.services(userId).then((data) => setServices(data.services)).catch(() => {});
  }, [userId]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    api.ticket(userId, selected).then(setDetail).catch((err) => setError((err as Error).message));
  }, [selected, userId, tickets]);

  const total = useMemo(
    () =>
      lines.reduce((sum, line) => {
        const service = services.find((s) => s.id === line.serviceId);
        return sum + (service ? service.unit_price_cents * line.quantity : 0);
      }, 0),
    [lines, services]
  );

  const act = async (fn: () => Promise<unknown>, after?: (result: unknown) => void) => {
    setBusy(true);
    try {
      const result = await fn();
      after?.(result);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const create = () =>
    act(
      () =>
        api.create(userId, {
          client_id: clientId,
          notes,
          items: lines
            .map((line) => {
              const service = services.find((s) => s.id === line.serviceId);
              return service
                ? { description: service.name, quantity: line.quantity, unit_price_cents: service.unit_price_cents }
                : null;
            })
            .filter(Boolean)
        }),
      (result) => setSelected((result as Ticket).id)
    );

  const openPdf = async (invoiceId: string) => {
    try {
      const response = await fetch(`/api/invoices/${invoiceId}/pdf`, { headers: { "x-user-id": userId } });
      if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
      const blob = await response.blob();
      window.open(URL.createObjectURL(blob), "_blank");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <svg viewBox="0 0 24 24" className="mark" aria-hidden="true">
            <path d="M4 7h16M4 12h10M4 17h7" />
          </svg>
          <div>
            <h1>Ticketline</h1>
            <p>Field jobs · approvals · demo invoice PDF</p>
          </div>
        </div>
        <div className="topbar-right">
          <span className="pill demo">Case 03 · personal demo</span>
          <label className="role">
            Acting as
            <select value={userId} onChange={(event) => { setUserId(event.target.value); setSelected(null); }}>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.name} — {u.role}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <aside className="sidebar">
        <h2>New job ticket</h2>
        <label>Client
          <select value={clientId} onChange={(event) => setClientId(event.target.value)}>
            {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
          </select>
        </label>
        <label>Work notes
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
        </label>
        <h2>Items</h2>
        {lines.map((line, index) => (
          <div className="line" key={index}>
            <select
              value={line.serviceId}
              onChange={(event) => setLines(lines.map((l, i) => (i === index ? { ...l, serviceId: event.target.value } : l)))}
            >
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name} — {money(service.unit_price_cents)}
                </option>
              ))}
            </select>
            <input
              type="number"
              min={1}
              value={line.quantity}
              onChange={(event) => setLines(lines.map((l, i) => (i === index ? { ...l, quantity: Number(event.target.value) } : l)))}
            />
            <button className="ghost" onClick={() => setLines(lines.filter((_, i) => i !== index))} aria-label="Remove line">×</button>
          </div>
        ))}
        <button className="ghost wide" onClick={() => setLines([...lines, { serviceId: services[0]?.id ?? "", quantity: 1 }])}>
          + Add item
        </button>
        <div className="total">Total <strong>{money(total)}</strong></div>
        <button className="primary" disabled={busy || !user} onClick={() => void create()}>
          Create draft ticket
        </button>
        <p className="hint">Only the technician creates and submits. The reviewer approves and issues the invoice.</p>
      </aside>

      <main className="main">
        <div className="tabs">
          {(["tickets", "invoices", "dashboard"] as Tab[]).map((item) => (
            <button key={item} className={tab === item ? "tab active" : "tab"} onClick={() => setTab(item)}>
              {item[0].toUpperCase() + item.slice(1)}
            </button>
          ))}
        </div>

        {error && <div className="error">{error}</div>}

        {tab === "tickets" && (
          <div className="list">
            {tickets.length === 0 && <p className="muted">No tickets yet.</p>}
            {tickets.map((ticket) => (
              <button key={ticket.id} className={selected === ticket.id ? "row active" : "row"} onClick={() => setSelected(ticket.id)}>
                <div className="row-top">
                  <strong>#{String(ticket.number).padStart(4, "0")} · {ticket.client_name}</strong>
                  <span className={`pill ${ticket.status}`}>{ticket.status}</span>
                </div>
                <div className="row-bottom">
                  <small>{ticket.technician_name} · {new Date(ticket.created_at).toLocaleString()}</small>
                  <strong>{money(ticket.total_cents)}</strong>
                </div>
              </button>
            ))}
          </div>
        )}

        {tab === "invoices" && (
          <div className="list">
            {invoices.length === 0 && <p className="muted">No invoices issued yet.</p>}
            {invoices.map((invoice) => (
              <div className="row" key={invoice.id}>
                <div className="row-top">
                  <strong>Invoice #{String(invoice.number).padStart(4, "0")}</strong>
                  <span className="pill invoiced">{money(invoice.total_cents)}</span>
                </div>
                <div className="row-bottom">
                  <small>Ticket #{String(invoice.ticket_number).padStart(4, "0")} · {new Date(invoice.issued_at).toLocaleString()}</small>
                  <button className="ghost" onClick={() => void openPdf(invoice.id)}>Open PDF</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "dashboard" && dashboard && (
          <div className="dashboard">
            <div className="kpi"><span>Invoices</span><strong>{dashboard.invoices.invoices}</strong></div>
            <div className="kpi"><span>Invoiced total</span><strong>{money(dashboard.invoices.total_cents)}</strong></div>
            {dashboard.by_status.map((row) => (
              <div className="kpi" key={row.status}><span>{row.status}</span><strong>{row.count}</strong></div>
            ))}
          </div>
        )}
      </main>

      <section className="detail">
        {!detail && <p className="muted">Select a ticket to see items, history and available actions.</p>}
        {detail && (
          <>
            <div className="detail-head">
              <div>
                <h2>Ticket #{String(detail.ticket.number).padStart(4, "0")}</h2>
                <p>{detail.ticket.client_name} · {detail.ticket.client_address}</p>
              </div>
              <span className={`pill ${detail.ticket.status}`}>{detail.ticket.status}</span>
            </div>

            <table className="items">
              <thead><tr><th>Description</th><th>Qty</th><th>Unit</th><th>Total</th></tr></thead>
              <tbody>
                {detail.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.description}</td>
                    <td>{item.quantity}</td>
                    <td>{money(item.unit_price_cents)}</td>
                    <td>{money(item.quantity * item.unit_price_cents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="grand"><span>Total</span><strong>{money(detail.items.reduce((sum, item) => sum + item.quantity * item.unit_price_cents, 0))}</strong></div>

            <h3>History</h3>
            <ul className="history">
              {detail.audit.map((entry) => (
                <li key={entry.id}>
                  <strong>{entry.action}</strong>
                  <span>{entry.actor_name} · {new Date(entry.created_at).toLocaleString()}</span>
                </li>
              ))}
            </ul>

            <div className="actions">
              {detail.ticket.status === "draft" && !isReviewer && (
                <button className="primary" disabled={busy} onClick={() => void act(() => api.submit(userId, detail.ticket.id))}>
                  Submit for review
                </button>
              )}
              {detail.ticket.status === "submitted" && isReviewer && (
                <>
                  <button className="primary" disabled={busy} onClick={() => void act(() => api.review(userId, detail.ticket.id, "approve"))}>
                    Approve
                  </button>
                  <button className="danger" disabled={busy} onClick={() => void act(() => api.review(userId, detail.ticket.id, "reject"))}>
                    Reject
                  </button>
                </>
              )}
              {detail.ticket.status === "approved" && isReviewer && (
                <button className="primary" disabled={busy} onClick={() => void act(() => api.invoice(userId, detail.ticket.id))}>
                  Issue demo invoice
                </button>
              )}
              {detail.invoice && (
                <button className="ghost" onClick={() => void openPdf(detail.invoice!.id)}>
                  Open invoice #{String(detail.invoice.number).padStart(4, "0")} PDF
                </button>
              )}
            </div>
            {detail.ticket.status === "approved" && !isReviewer && (
              <p className="hint">Waiting for a reviewer to issue the invoice.</p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
