import test from "node:test";
import assert from "node:assert/strict";
import { backoffMs, sign, verify } from "../src/signature.js";
import { validateEvent } from "../src/types.js";

const SECRET = "test-secret";
const body = JSON.stringify({ id: "evt_123456", type: "order.confirmed" });

test("accepts a valid signature", () => {
  const ts = String(Math.floor(Date.now() / 1000));
  const signature = sign(SECRET, ts, body);
  assert.deepEqual(verify(SECRET, { signature, timestamp: ts }, body), { ok: true });
});

test("rejects a tampered body", () => {
  const ts = String(Math.floor(Date.now() / 1000));
  const signature = sign(SECRET, ts, body);
  const result = verify(SECRET, { signature, timestamp: ts }, body + " ");
  assert.equal(result.ok, false);
  assert.equal(result.reason, "bad_signature");
});

test("rejects a stale signed request, preventing replay", () => {
  const old = String(Math.floor(Date.now() / 1000) - 600);
  const signature = sign(SECRET, old, body);
  const result = verify(SECRET, { signature, timestamp: old }, body);
  assert.equal(result.ok, false);
  assert.equal(result.reason, "stale");
});

test("rejects missing headers", () => {
  assert.equal(verify(SECRET, {}, body).ok, false);
});

test("backoff grows and stays under the cap", () => {
  const values = [1, 2, 3, 4, 5].map((attempt) => backoffMs(attempt, 400, 30_000, () => 1));
  assert.deepEqual(values, [400, 800, 1600, 3200, 6400]);
  for (let i = 0; i < 100; i += 1) assert.ok(backoffMs(10, 400, 30_000) <= 30_000);
});

test("validates a well-formed order event", () => {
  const result = validateEvent({
    id: "evt_abc123",
    type: "order.confirmed",
    created_at: new Date().toISOString(),
    data: { order_id: "ord_1", customer: { email: "a@b.c", name: "A" }, items: [{ sku: "lamp", quantity: 1 }] }
  });
  assert.equal(result.ok, true);
});

test("rejects an event without items", () => {
  const result = validateEvent({
    id: "evt_abc123",
    type: "order.confirmed",
    created_at: new Date().toISOString(),
    data: { order_id: "ord_1", customer: { email: "a@b.c", name: "A" }, items: [] }
  });
  assert.equal(result.ok, false);
});

test("rejects unsupported event types and failure modes", () => {
  const base = {
    id: "evt_abc123",
    created_at: new Date().toISOString(),
    data: { order_id: "ord_1", customer: { email: "a@b.c", name: "A" }, items: [{ sku: "lamp", quantity: 1 }] }
  };
  assert.equal(validateEvent({ ...base, type: "order.cancelled" }).ok, false);
  assert.equal(
    validateEvent({ ...base, type: "order.confirmed", data: { ...base.data, failure_mode: "explode" } }).ok,
    false
  );
});
