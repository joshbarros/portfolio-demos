import { randomUUID } from "node:crypto";
import pg from "pg";
import { invoiceTotal } from "./money.js";
import { assertTransition, type Role, type TicketStatus } from "./state.js";

const { Pool } = pg;
export const pool = new Pool({
  connectionString: process.env.DATABASE_URL ?? "postgresql://ticketline:ticketline@127.0.0.1:5435/ticketline"
});

export type User = { id: string; org_id: string; name: string; role: Role };
export type Ticket = {
  id: string;
  org_id: string;
  number: number;
  technician_id: string;
  client_id: string;
  status: TicketStatus;
  notes: string;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
};

export async function init(): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS orgs (id text PRIMARY KEY, name text NOT NULL);
    CREATE TABLE IF NOT EXISTS users (
      id text PRIMARY KEY, org_id text NOT NULL REFERENCES orgs(id), name text NOT NULL, role text NOT NULL
    );
    CREATE TABLE IF NOT EXISTS clients (
      id text PRIMARY KEY, org_id text NOT NULL REFERENCES orgs(id), name text NOT NULL, address text NOT NULL
    );
    CREATE TABLE IF NOT EXISTS services (
      id text PRIMARY KEY, org_id text NOT NULL REFERENCES orgs(id), name text NOT NULL,
      unit_price_cents integer NOT NULL CHECK (unit_price_cents >= 0)
    );
    CREATE TABLE IF NOT EXISTS tickets (
      id text PRIMARY KEY,
      org_id text NOT NULL REFERENCES orgs(id),
      number integer NOT NULL,
      technician_id text NOT NULL REFERENCES users(id),
      client_id text NOT NULL REFERENCES clients(id),
      status text NOT NULL,
      notes text NOT NULL DEFAULT '',
      created_at timestamptz NOT NULL DEFAULT now(),
      approved_by text REFERENCES users(id),
      approved_at timestamptz,
      rejection_reason text,
      UNIQUE (org_id, number)
    );
    CREATE TABLE IF NOT EXISTS ticket_items (
      id text PRIMARY KEY,
      ticket_id text NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
      position integer NOT NULL,
      description text NOT NULL,
      quantity integer NOT NULL CHECK (quantity > 0),
      unit_price_cents integer NOT NULL CHECK (unit_price_cents >= 0)
    );
    CREATE TABLE IF NOT EXISTS invoice_counters (org_id text PRIMARY KEY REFERENCES orgs(id), next_number integer NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS invoices (
      id text PRIMARY KEY,
      org_id text NOT NULL REFERENCES orgs(id),
      ticket_id text NOT NULL UNIQUE REFERENCES tickets(id),
      number integer NOT NULL,
      currency text NOT NULL,
      total_cents integer NOT NULL,
      snapshot jsonb NOT NULL,
      issued_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE (org_id, number)
    );
    CREATE TABLE IF NOT EXISTS audit (
      id bigserial PRIMARY KEY,
      org_id text NOT NULL,
      ticket_id text,
      actor_id text NOT NULL,
      action text NOT NULL,
      detail jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_tickets_org_status ON tickets(org_id, status);
  `);
}

export async function seedDemo(): Promise<void> {
  const existing = await pool.query("SELECT 1 FROM orgs LIMIT 1");
  if (existing.rowCount) return;
  const org = "org_demo_electric";
  await pool.query("INSERT INTO orgs (id, name) VALUES ($1, $2)", [org, "Demo Electric Co."]);
  await pool.query(
    "INSERT INTO users (id, org_id, name, role) VALUES ('user_tech','org_demo_electric','Tina Technician','technician'), ('user_review','org_demo_electric','Ravi Reviewer','reviewer')"
  );
  await pool.query(
    "INSERT INTO clients (id, org_id, name, address) VALUES ('client_harbor','org_demo_electric','Harbor Cafe','12 Dock Street, Portland, OR')"
  );
  await pool.query(
    `INSERT INTO services (id, org_id, name, unit_price_cents) VALUES
     ('svc_diag','org_demo_electric','Diagnostic visit', 9000),
     ('svc_thermostat','org_demo_electric','Thermostat replacement', 18500),
     ('svc_labor','org_demo_electric','Labor (hour)', 12000)`
  );
  await pool.query("INSERT INTO invoice_counters (org_id, next_number) VALUES ($1, 1)", [org]);
}

async function audit(client: pg.PoolClient | pg.Pool, orgId: string, ticketId: string | null, actorId: string, action: string, detail: unknown) {
  await client.query(
    "INSERT INTO audit (org_id, ticket_id, actor_id, action, detail) VALUES ($1,$2,$3,$4,$5)",
    [orgId, ticketId, actorId, action, detail]
  );
}

export async function getUser(id: string): Promise<User | null> {
  const result = await pool.query<User>("SELECT id, org_id, name, role FROM users WHERE id = $1", [id]);
  return result.rows[0] ?? null;
}

export async function createTicket(
  actor: User,
  payload: { client_id: string; notes: string; items: { description: string; quantity: number; unit_price_cents: number }[] }
): Promise<Ticket> {
  if (!payload.items.length) throw Object.assign(new Error("ticket needs at least one item"), { statusCode: 422 });
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const clientRow = await client.query("SELECT id FROM clients WHERE id = $1 AND org_id = $2", [payload.client_id, actor.org_id]);
    if (!clientRow.rowCount) throw Object.assign(new Error("client not found in organization"), { statusCode: 404 });
    const numberRow = await client.query(
      "SELECT COALESCE(MAX(number), 0) + 1 AS next FROM tickets WHERE org_id = $1",
      [actor.org_id]
    );
    const id = randomUUID();
    const ticket = await client.query<Ticket>(
      `INSERT INTO tickets (id, org_id, number, technician_id, client_id, status, notes)
       VALUES ($1,$2,$3,$4,$5,'draft',$6) RETURNING *`,
      [id, actor.org_id, Number(numberRow.rows[0].next), actor.id, payload.client_id, payload.notes]
    );
    for (const [index, item] of payload.items.entries()) {
      await client.query(
        "INSERT INTO ticket_items (id, ticket_id, position, description, quantity, unit_price_cents) VALUES ($1,$2,$3,$4,$5,$6)",
        [randomUUID(), id, index, item.description, item.quantity, item.unit_price_cents]
      );
    }
    await audit(client, actor.org_id, id, actor.id, "ticket.created", { number: ticket.rows[0].number });
    await client.query("COMMIT");
    return ticket.rows[0];
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function submitTicket(actor: User, ticketId: string): Promise<Ticket> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const row = await client.query<Ticket>("SELECT * FROM tickets WHERE id = $1 AND org_id = $2 FOR UPDATE", [ticketId, actor.org_id]);
    if (!row.rowCount) throw Object.assign(new Error("ticket not found"), { statusCode: 404 });
    assertTransition(row.rows[0].status, "submitted");
    const updated = await client.query<Ticket>("UPDATE tickets SET status = 'submitted' WHERE id = $1 RETURNING *", [ticketId]);
    await audit(client, actor.org_id, ticketId, actor.id, "ticket.submitted", {});
    await client.query("COMMIT");
    return updated.rows[0];
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function reviewTicket(actor: User, ticketId: string, decision: "approve" | "reject", reason = ""): Promise<Ticket> {
  if (actor.role !== "reviewer") throw Object.assign(new Error("only reviewers can decide"), { statusCode: 403 });
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const row = await client.query<Ticket>("SELECT * FROM tickets WHERE id = $1 AND org_id = $2 FOR UPDATE", [ticketId, actor.org_id]);
    if (!row.rowCount) throw Object.assign(new Error("ticket not found"), { statusCode: 404 });
    const target: TicketStatus = decision === "approve" ? "approved" : "rejected";
    assertTransition(row.rows[0].status, target);
    const updated = await client.query<Ticket>(
      `UPDATE tickets SET status = $2, approved_by = CASE WHEN $2 = 'approved' THEN $3 ELSE NULL END,
       approved_at = CASE WHEN $2 = 'approved' THEN now() ELSE NULL END,
       rejection_reason = CASE WHEN $2 = 'rejected' THEN $4 ELSE NULL END
       WHERE id = $1 RETURNING *`,
      [ticketId, target, actor.id, reason]
    );
    await audit(client, actor.org_id, ticketId, actor.id, `ticket.${decision}d`, { reason });
    await client.query("COMMIT");
    return updated.rows[0];
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function issueInvoice(actor: User, ticketId: string): Promise<{ id: string; number: number; total_cents: number }> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const ticketRow = await client.query<Ticket>("SELECT * FROM tickets WHERE id = $1 AND org_id = $2 FOR UPDATE", [ticketId, actor.org_id]);
    if (!ticketRow.rowCount) throw Object.assign(new Error("ticket not found"), { statusCode: 404 });
    const ticket = ticketRow.rows[0];
    if (ticket.status === "invoiced") throw Object.assign(new Error("invoice already issued"), { statusCode: 409 });
    assertTransition(ticket.status, "invoiced");

    const existing = await client.query("SELECT id, number, total_cents FROM invoices WHERE ticket_id = $1", [ticketId]);
    if (existing.rowCount) throw Object.assign(new Error("invoice already issued"), { statusCode: 409 });

    const items = await client.query(
      "SELECT description, quantity, unit_price_cents FROM ticket_items WHERE ticket_id = $1 ORDER BY position",
      [ticketId]
    );
    const clientRow = await client.query("SELECT name, address FROM clients WHERE id = $1", [ticket.client_id]);
    const total = invoiceTotal(items.rows);
    const counter = await client.query(
      "UPDATE invoice_counters SET next_number = next_number + 1 WHERE org_id = $1 RETURNING next_number - 1 AS number",
      [actor.org_id]
    );
    const number = Number(counter.rows[0].number);
    const snapshot = {
      ticket: { id: ticket.id, number: ticket.number, notes: ticket.notes, approved_by: ticket.approved_by, approved_at: ticket.approved_at },
      client: clientRow.rows[0],
      items: items.rows,
      total_cents: total,
      currency: "USD",
      issued_at: new Date().toISOString(),
      disclaimer: "DEMO INVOICE — not a tax document. Fictional data."
    };
    const id = randomUUID();
    await client.query(
      "INSERT INTO invoices (id, org_id, ticket_id, number, currency, total_cents, snapshot) VALUES ($1,$2,$3,$4,'USD',$5,$6)",
      [id, actor.org_id, ticketId, number, total, snapshot]
    );
    await client.query("UPDATE tickets SET status = 'invoiced' WHERE id = $1", [ticketId]);
    await audit(client, actor.org_id, ticketId, actor.id, "invoice.issued", { invoice_number: number, total_cents: total });
    await client.query("COMMIT");
    return { id, number, total_cents: total };
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function dashboard(orgId: string) {
  const byStatus = await pool.query(
    "SELECT status, COUNT(*)::int AS count FROM tickets WHERE org_id = $1 GROUP BY status",
    [orgId]
  );
  const invoiced = await pool.query(
    "SELECT COUNT(*)::int AS invoices, COALESCE(SUM(total_cents),0)::int AS total_cents FROM invoices WHERE org_id = $1",
    [orgId]
  );
  return { by_status: byStatus.rows, invoices: invoiced.rows[0] };
}
