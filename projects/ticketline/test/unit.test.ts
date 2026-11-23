import test from "node:test";
import assert from "node:assert/strict";
import { invoiceTotal, lineTotal } from "../src/money.js";
import { canTransition, canEditTicket, canReview } from "../src/state.js";

test("money is integer cents", () => {
  assert.equal(lineTotal(3, 18500), 55500);
  assert.equal(invoiceTotal([{ quantity: 2, unit_price_cents: 9000 }, { quantity: 1, unit_price_cents: 12000 }]), 30000);
  assert.throws(() => lineTotal(0, 100));
  assert.throws(() => lineTotal(2, -1));
  assert.throws(() => lineTotal(1.5, 100));
});

test("state machine allows only declared transitions", () => {
  assert.equal(canTransition("draft", "submitted"), true);
  assert.equal(canTransition("submitted", "approved"), true);
  assert.equal(canTransition("submitted", "rejected"), true);
  assert.equal(canTransition("approved", "invoiced"), true);
  assert.equal(canTransition("draft", "approved"), false);
  assert.equal(canTransition("invoiced", "approved"), false);
  assert.equal(canTransition("rejected", "draft"), true);
});

test("only reviewers decide", () => {
  assert.equal(canReview("reviewer"), true);
  assert.equal(canReview("technician"), false);
});

test("technicians edit only their own drafts", () => {
  const ticket = { status: "draft" as const, technician_id: "tech_1" };
  assert.equal(canEditTicket("technician", "tech_1", ticket), true);
  assert.equal(canEditTicket("technician", "tech_2", ticket), false);
  assert.equal(canEditTicket("technician", "tech_1", { ...ticket, status: "submitted" as never }), false);
});
