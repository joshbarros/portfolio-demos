import Fastify from "fastify";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fastifyStatic from "@fastify/static";
import { createTicket, dashboard, getUser, init, issueInvoice, pool, reviewTicket, seedDemo, submitTicket } from "./db.js";
import { renderInvoicePdf, type InvoiceSnapshot } from "./pdf.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(here, "..", "frontend", "dist");
const app = Fastify({ logger: false });

app.setErrorHandler((error, _request, reply) => {
  const status = (error as { statusCode?: number }).statusCode ?? 400;
  reply.code(status).send({ error: error instanceof Error ? error.message : "bad request" });
});

async function actor(request: { headers: Record<string, unknown> }) {
  const id = String(request.headers["x-user-id"] ?? "");
  const user = id ? await getUser(id) : null;
  if (!user) throw Object.assign(new Error("authenticate with x-user-id (demo users: user_tech, user_review)"), { statusCode: 401 });
  return user;
}

app.get("/api/health", async () => ({ ok: true, service: "ticketline" }));

app.get("/api/users", async () => {
  const result = await pool.query("SELECT id, name, role FROM users ORDER BY role DESC");
  return { users: result.rows };
});

app.post("/api/tickets", async (request, reply) => {
  const user = await actor(request);
  const body = (request.body ?? {}) as {
    client_id?: string;
    notes?: string;
    items?: { description: string; quantity: number; unit_price_cents: number }[];
  };
  if (!body.client_id || !Array.isArray(body.items)) throw Object.assign(new Error("client_id and items are required"), { statusCode: 422 });
  const ticket = await createTicket(user, { client_id: body.client_id, notes: body.notes ?? "", items: body.items });
  return reply.code(201).send(ticket);
});

app.post("/api/tickets/:id/submit", async (request) => {
  const user = await actor(request);
  const { id } = request.params as { id: string };
  return submitTicket(user, id);
});

app.post("/api/tickets/:id/review", async (request) => {
  const user = await actor(request);
  const { id } = request.params as { id: string };
  const body = (request.body ?? {}) as { decision?: "approve" | "reject"; reason?: string };
  if (body.decision !== "approve" && body.decision !== "reject") {
    throw Object.assign(new Error("decision must be approve or reject"), { statusCode: 422 });
  }
  return reviewTicket(user, id, body.decision, body.reason ?? "");
});

app.post("/api/tickets/:id/invoice", async (request, reply) => {
  const user = await actor(request); // reviewers issue in this demo
  if (user.role !== "reviewer") throw Object.assign(new Error("only reviewers can issue invoices"), { statusCode: 403 });
  const { id } = request.params as { id: string };
  const invoice = await issueInvoice(user, id);
  return reply.code(201).send(invoice);
});

app.get("/api/tickets", async (request) => {
  const user = await actor(request);
  const { status } = request.query as { status?: string };
  const result = await pool.query(
    `SELECT t.*, c.name AS client_name, u.name AS technician_name,
            (SELECT COALESCE(SUM(quantity * unit_price_cents), 0)::int FROM ticket_items WHERE ticket_id = t.id) AS total_cents
     FROM tickets t JOIN clients c ON c.id = t.client_id JOIN users u ON u.id = t.technician_id
     WHERE t.org_id = $1 AND ($2::text IS NULL OR t.status = $2)
     ORDER BY t.created_at DESC`,
    [user.org_id, status ?? null]
  );
  return { tickets: result.rows };
});

app.get("/api/tickets/:id", async (request, reply) => {
  const user = await actor(request);
  const { id } = request.params as { id: string };
  const ticket = await pool.query(
    "SELECT t.*, c.name AS client_name, c.address AS client_address FROM tickets t JOIN clients c ON c.id = t.client_id WHERE t.id = $1 AND t.org_id = $2",
    [id, user.org_id]
  );
  if (!ticket.rowCount) return reply.code(404).send({ error: "ticket not found" });
  const items = await pool.query("SELECT * FROM ticket_items WHERE ticket_id = $1 ORDER BY position", [id]);
  const audit = await pool.query(
    "SELECT a.*, u.name AS actor_name FROM audit a JOIN users u ON u.id = a.actor_id WHERE a.ticket_id = $1 ORDER BY a.created_at",
    [id]
  );
  const invoice = await pool.query("SELECT id, number, total_cents, issued_at FROM invoices WHERE ticket_id = $1", [id]);
  return { ticket: ticket.rows[0], items: items.rows, audit: audit.rows, invoice: invoice.rows[0] ?? null };
});

app.get("/api/invoices", async (request) => {
  const user = await actor(request);
  const result = await pool.query(
    `SELECT i.id, i.number, i.total_cents, i.currency, i.issued_at, i.ticket_id, t.number AS ticket_number
     FROM invoices i JOIN tickets t ON t.id = i.ticket_id WHERE i.org_id = $1 ORDER BY i.number DESC`,
    [user.org_id]
  );
  return { invoices: result.rows };
});

app.get("/api/invoices/:id/pdf", async (request, reply) => {
  const user = await actor(request);
  const { id } = request.params as { id: string };
  // Org check happens in SQL: a document from another organization is simply not found.
  const result = await pool.query(
    "SELECT number, snapshot FROM invoices WHERE id = $1 AND org_id = $2",
    [id, user.org_id]
  );
  if (!result.rowCount) return reply.code(404).send({ error: "invoice not found" });
  const pdf = await renderInvoicePdf({
    number: result.rows[0].number,
    snapshot: result.rows[0].snapshot as InvoiceSnapshot
  });
  reply
    .header("content-type", "application/pdf")
    .header("content-disposition", `inline; filename="demo-invoice-${result.rows[0].number}.pdf"`);
  return reply.send(pdf);
});

app.get("/api/dashboard", async (request) => {
  const user = await actor(request);
  return dashboard(user.org_id);
});

if (existsSync(dist)) {
  await app.register(fastifyStatic, { root: dist });
  app.setNotFoundHandler((request, reply) => {
    if (request.url.startsWith("/api")) return reply.code(404).send({ error: "not found" });
    return reply.sendFile("index.html");
  });
}

const port = Number(process.env.PORT ?? 8095);
await init();
await seedDemo();
app
  .listen({ port, host: "0.0.0.0" })
  .then(() => console.log(JSON.stringify({ level: "info", msg: "ticketline listening", port })))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
