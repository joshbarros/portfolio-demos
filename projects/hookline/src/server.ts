import { randomUUID } from "node:crypto";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Fastify from "fastify";
import fastifyStatic from "@fastify/static";
import { init, ingestEvent, listExecutions, getExecution, replay, pool } from "./db.js";
import { sign, verify } from "./signature.js";
import { validateEvent, type WebhookEvent } from "./types.js";

const SECRET = process.env.HOOKLINE_SECRET ?? "dev-secret-change-me";
const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(here, "..", "frontend", "dist");

const app = Fastify({ logger: false });

app.addContentTypeParser("application/json", { parseAs: "string" }, (request, body, done) => {
  (request as unknown as { rawBody: string }).rawBody = body as string;
  try {
    done(null, JSON.parse(body as string));
  } catch (error) {
    done(error as Error, undefined);
  }
});

app.setErrorHandler((error, _request, reply) => {
  const status = (error as { statusCode?: number }).statusCode ?? 400;
  const message = error instanceof Error ? error.message : "bad request";
  reply.code(status).send({ error: message });
});

app.get("/api/health", async () => ({ ok: true, service: "hookline" }));

app.post("/webhooks/:source", async (request, reply) => {
  const { source } = request.params as { source: string };
  if (source !== "demo-shop") {
    return reply.code(404).send({ error: "unknown source" });
  }
  const headers = request.headers as Record<string, string | undefined>;
  const raw = (request as unknown as { rawBody?: string }).rawBody ?? "";
  const verdict = verify(
    SECRET,
    { signature: headers["x-hookline-signature"], timestamp: headers["x-hookline-timestamp"] },
    raw
  );
  if (!verdict.ok) {
    return reply.code(401).send({ error: "invalid signature", reason: verdict.reason });
  }
  const parsed = validateEvent(request.body);
  if (!parsed.ok) return reply.code(422).send({ error: parsed.error });
  const result = await ingestEvent(source, parsed.event, request.body, true);
  return reply.code(result.duplicate ? 200 : 202).send({
    execution_id: result.executionId,
    duplicate: result.duplicate
  });
});

app.post("/api/demo", async (request, reply) => {
  const body = (request.body ?? {}) as { mode?: string };
  const mode = body.mode ?? "happy";
  if (!["happy", "transient", "permanent", "timeout", "duplicate"].includes(mode)) {
    return reply.code(400).send({ error: "unknown demo mode" });
  }
  const event: WebhookEvent = {
    id: `evt_${randomUUID()}`,
    type: "order.confirmed",
    created_at: new Date().toISOString(),
    data: {
      order_id: `ord_${Math.floor(Math.random() * 9000 + 1000)}`,
      customer: { email: "demo@example.com", name: "Demo Customer" },
      items: [
        { sku: "lamp-01", quantity: 1 },
        { sku: "bulb-02", quantity: 2 }
      ],
      failure_mode: mode === "duplicate" ? "happy" : (mode as "happy" | "transient" | "permanent" | "timeout")
    }
  };
  const first = await ingestEvent("demo-shop", event, event, true);
  if (mode === "duplicate") {
    const second = await ingestEvent("demo-shop", event, event, true);
    return reply.code(202).send({
      execution_id: first.executionId,
      duplicate_execution_id: second.executionId,
      duplicate: second.duplicate,
      event_id: event.id
    });
  }
  return reply.code(202).send({ execution_id: first.executionId, event_id: event.id });
});

app.get("/api/executions", async () => ({ executions: await listExecutions() }));

app.get("/api/executions/:id", async (request, reply) => {
  const { id } = request.params as { id: string };
  const detail = await getExecution(id);
  if (!detail) return reply.code(404).send({ error: "execution not found" });
  return detail;
});

app.post("/api/executions/:id/replay", async (request, reply) => {
  const { id } = request.params as { id: string };
  const body = (request.body ?? {}) as { failure_mode?: string };
  if (body.failure_mode) {
    // "Fix the cause, then replay": the stored event is corrected before the
    // new execution starts, so the replay can succeed.
    await pool.query(
      `UPDATE events SET payload = jsonb_set(payload, '{data,failure_mode}', to_jsonb($2::text))
       WHERE id = (SELECT event_id FROM executions WHERE id = $1)`,
      [id, body.failure_mode]
    );
  }
  const result = await replay(id);
  if (!result.ok) return reply.code(409).send({ error: result.reason });
  return reply.code(202).send({ execution_id: result.executionId });
});

/** Signs a request the same way an external caller would. Useful for the demo docs. */
app.get("/api/sign-example", async () => {
  const event: WebhookEvent = {
    id: "evt_example_001",
    type: "order.confirmed",
    created_at: new Date().toISOString(),
    data: { order_id: "ord_1001", customer: { email: "a@b.c", name: "A" }, items: [{ sku: "lamp-01", quantity: 1 }] }
  };
  const raw = JSON.stringify(event);
  const timestamp = String(Math.floor(Date.now() / 1000));
  return { timestamp, signature: sign(SECRET, timestamp, raw), body: event };
});

if (existsSync(dist)) {
  await app.register(fastifyStatic, { root: dist });
  app.setNotFoundHandler((request, reply) => {
    if (request.url.startsWith("/api") || request.url.startsWith("/webhooks")) {
      return reply.code(404).send({ error: "not found" });
    }
    return reply.sendFile("index.html");
  });
}

const port = Number(process.env.PORT ?? 8097);
await init();
app
  .listen({ port, host: "0.0.0.0" })
  .then(() => console.log(JSON.stringify({ level: "info", msg: "hookline api listening", port })))
  .catch(async (error) => {
    // Useful when the SPA has not been built yet.
    if (!existsSync(dist)) {
      console.error("frontend/dist missing; run npm run build in frontend/");
    }
    console.error(error);
    process.exit(1);
  });
