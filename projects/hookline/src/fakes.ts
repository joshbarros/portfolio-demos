import Fastify from "fastify";

type Mode = "happy" | "transient" | "permanent" | "timeout";

type State = {
  reservations: number;
  catalog: number;
  notifications: number;
  calls: Record<string, number>;
  seen: Record<string, true>;
};

const state: State = { reservations: 0, catalog: 0, notifications: 0, calls: {}, seen: {} };

const app = Fastify({ logger: false });

app.get("/health", async () => ({ ok: true, service: "hookline-fakes" }));

app.get("/_state", async () => state);

app.post("/_reset", async () => {
  state.reservations = 0;
  state.catalog = 0;
  state.notifications = 0;
  state.calls = {};
  state.seen = {};
  return { ok: true };
});

function behaviour(body: Record<string, unknown>): { mode: Mode; key: string } {
  const mode = (body.failure_mode as Mode) ?? "happy";
  const key = String(body.idempotency_key ?? body.event_id ?? "anonymous");
  return { mode, key };
}

app.post("/reservations", async (request, reply) => {
  const body = (request.body ?? {}) as Record<string, unknown>;
  const { mode, key } = behaviour(body);
  state.calls[key] = (state.calls[key] ?? 0) + 1;

  if (mode === "permanent") return reply.code(422).send({ error: "reservation rejected", reason: "out_of_stock" });
  if (mode === "timeout") {
    await new Promise((resolve) => setTimeout(resolve, 5000));
    return reply.code(201).send({ reservation_id: `res_${key}`, duplicate: false });
  }
  if (mode === "transient" && state.calls[key] <= 2) {
    return reply.code(503).send({ error: "reservation service temporarily unavailable", attempt: state.calls[key] });
  }
  // Idempotent destination: the same key never creates a second reservation.
  if (state.seen[key]) {
    return reply.code(409).send({ reservation_id: `res_${key}`, duplicate: true });
  }
  state.seen[key] = true;
  state.reservations += 1;
  return reply.code(201).send({ reservation_id: `res_${key}`, duplicate: false });
});

app.post("/catalog/check", async (request, reply) => {
  const body = (request.body ?? {}) as Record<string, unknown>;
  const { mode, key } = behaviour(body);
  const callKey = `catalog:${key}`;
  state.calls[callKey] = (state.calls[callKey] ?? 0) + 1;
  if (mode === "permanent") return reply.code(422).send({ error: "catalog mismatch" });
  if (mode === "timeout") {
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
  if (mode === "transient" && state.calls[callKey] <= 1) {
    return reply.code(503).send({ error: "catalog service unavailable" });
  }
  state.catalog += 1;
  return reply.code(200).send({ ok: true, items_checked: Array.isArray(body.items) ? body.items.length : 0 });
});

app.post("/notifications", async (request, reply) => {
  const body = (request.body ?? {}) as Record<string, unknown>;
  const { mode, key } = behaviour(body);
  const callKey = `notify:${key}`;
  state.calls[callKey] = (state.calls[callKey] ?? 0) + 1;
  if (mode === "permanent") return reply.code(422).send({ error: "recipient rejected" });
  if (mode === "timeout") {
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
  if (mode === "transient" && state.calls[callKey] <= 1) {
    return reply.code(503).send({ error: "notification provider unavailable" });
  }
  // Deliberately NOT idempotent: this is the documented limit of the flow.
  state.notifications += 1;
  return reply.code(202).send({ accepted: true, delivered_count: state.notifications });
});

const port = Number(process.env.FAKES_PORT ?? 4010);
app
  .listen({ port, host: "0.0.0.0" })
  .then(() => console.log(JSON.stringify({ level: "info", msg: "fake services listening", port })))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
