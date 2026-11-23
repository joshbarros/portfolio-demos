import test from "node:test";
import assert from "node:assert/strict";

const url = process.env.TEST_DATABASE_URL;
if (!url) {
  test("integration suite skipped without TEST_DATABASE_URL", { skip: true }, () => {});
} else {
  process.env.DATABASE_URL = url;
  const db = await import("../src/db.js");
  const { renderInvoicePdf } = await import("../src/pdf.js");

  await db.pool.query("DROP SCHEMA public CASCADE; CREATE SCHEMA public;");
  await db.init();
  await db.seedDemo();
  await db.pool.query(
    "INSERT INTO orgs (id, name) VALUES ('org_other','Other Org'); INSERT INTO users (id, org_id, name, role) VALUES ('user_other','org_other','Other Reviewer','reviewer');"
  );

  const tech = (await db.getUser("user_tech"))!;
  const reviewer = (await db.getUser("user_review"))!;
  const outsider = (await db.getUser("user_other"))!;

  async function freshTicket() {
    const ticket = await db.createTicket(tech, {
      client_id: "client_harbor",
      notes: "Two thermostats and one diagnostic visit",
      items: [
        { description: "Diagnostic visit", quantity: 1, unit_price_cents: 9000 },
        { description: "Thermostat replacement", quantity: 2, unit_price_cents: 18500 }
      ]
    });
    await db.submitTicket(tech, ticket.id);
    await db.reviewTicket(reviewer, ticket.id, "approve");
    return ticket;
  }

  test("full flow creates one invoice with a real PDF", async () => {
    const ticket = await freshTicket();
    const invoice = await db.issueInvoice(reviewer, ticket.id);
    assert.equal(invoice.total_cents, 46000);
    const row = await db.pool.query("SELECT number, snapshot FROM invoices WHERE id = $1", [invoice.id]);
    assert.equal(row.rows[0].number, invoice.number);
    assert.equal(row.rows[0].snapshot.disclaimer.includes("DEMO INVOICE"), true);
    const pdf = await renderInvoicePdf({ number: invoice.number, snapshot: row.rows[0].snapshot });
    assert.equal(pdf.subarray(0, 4).toString(), "%PDF");
  });

  test("duplicate issuance is rejected", async () => {
    const ticket = await freshTicket();
    await db.issueInvoice(reviewer, ticket.id);
    await assert.rejects(() => db.issueInvoice(reviewer, ticket.id), /already issued/);
  });

  test("technician cannot approve", async () => {
    const ticket = await db.createTicket(tech, {
      client_id: "client_harbor",
      notes: "",
      items: [{ description: "Labor", quantity: 1, unit_price_cents: 12000 }]
    });
    await db.submitTicket(tech, ticket.id);
    await assert.rejects(() => db.reviewTicket(tech, ticket.id, "approve"), /reviewers/);
  });

  test("invalid transition is rejected", async () => {
    const ticket = await db.createTicket(tech, {
      client_id: "client_harbor",
      notes: "",
      items: [{ description: "Labor", quantity: 1, unit_price_cents: 12000 }]
    });
    await assert.rejects(() => db.reviewTicket(reviewer, ticket.id, "approve"), /invalid transition/);
  });

  test("invoice from another organization is not accessible", async () => {
    const ticket = await freshTicket();
    const invoice = await db.issueInvoice(reviewer, ticket.id);
    const wrong = await db.pool.query("SELECT 1 FROM invoices WHERE id = $1 AND org_id = $2", [invoice.id, outsider.org_id]);
    assert.equal(wrong.rowCount, 0);
  });

  test("concurrent issuance produces one invoice and one number", async () => {
    const ticket = await freshTicket();
    const results = await Promise.allSettled([
      db.issueInvoice(reviewer, ticket.id),
      db.issueInvoice(reviewer, ticket.id)
    ]);
    const ok = results.filter((r) => r.status === "fulfilled");
    const failed = results.filter((r) => r.status === "rejected");
    assert.equal(ok.length, 1);
    assert.equal(failed.length, 1);
    const count = await db.pool.query("SELECT COUNT(*)::int AS n FROM invoices WHERE ticket_id = $1", [ticket.id]);
    assert.equal(count.rows[0].n, 1);
    const numbers = await db.pool.query("SELECT number FROM invoices ORDER BY number");
    const unique = new Set(numbers.rows.map((r) => r.number));
    assert.equal(unique.size, numbers.rows.length);
  });
}
