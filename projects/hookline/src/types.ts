export type StepName = "reservations" | "catalog" | "notifications";

export type StepConfig = {
  name: StepName;
  path: string;
  idempotent: boolean;
};

export type Flow = {
  name: string;
  version: number;
  steps: StepConfig[];
};

/**
 * One explicit flow. The UI may trigger only these targets; it never accepts a
 * destination URL from the caller.
 */
export const ORDER_FLOW: Flow = {
  name: "order-confirmed",
  version: 1,
  steps: [
    { name: "reservations", path: "/reservations", idempotent: true },
    { name: "catalog", path: "/catalog/check", idempotent: true },
    { name: "notifications", path: "/notifications", idempotent: false }
  ]
};

export type EventPayload = {
  order_id: string;
  customer: { email: string; name: string };
  items: { sku: string; quantity: number }[];
  /** Demo control for the fake services: happy | transient | permanent | timeout */
  failure_mode?: "happy" | "transient" | "permanent" | "timeout";
};

export type WebhookEvent = {
  id: string;
  type: string;
  created_at: string;
  data: EventPayload;
};

export function validateEvent(raw: unknown): { ok: true; event: WebhookEvent } | { ok: false; error: string } {
  if (!raw || typeof raw !== "object") return { ok: false, error: "body must be a JSON object" };
  const value = raw as Record<string, unknown>;
  if (typeof value.id !== "string" || value.id.length < 6) return { ok: false, error: "id is required" };
  if (value.type !== "order.confirmed") return { ok: false, error: "unsupported event type" };
  if (typeof value.created_at !== "string") return { ok: false, error: "created_at is required" };
  const data = value.data as Record<string, unknown> | undefined;
  if (!data || typeof data !== "object") return { ok: false, error: "data is required" };
  if (typeof data.order_id !== "string" || !data.order_id) return { ok: false, error: "data.order_id is required" };
  if (!Array.isArray(data.items) || data.items.length === 0) return { ok: false, error: "data.items must be a non-empty array" };
  for (const item of data.items as Record<string, unknown>[]) {
    if (typeof item.sku !== "string" || typeof item.quantity !== "number" || item.quantity < 1) {
      return { ok: false, error: "each item needs sku and quantity >= 1" };
    }
  }
  const mode = data.failure_mode;
  if (mode && !["happy", "transient", "permanent", "timeout"].includes(String(mode))) {
    return { ok: false, error: "invalid failure_mode" };
  }
  return { ok: true, event: value as unknown as WebhookEvent };
}
