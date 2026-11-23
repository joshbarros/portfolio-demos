import { randomUUID } from "node:crypto";
import pg from "pg";
import type { WebhookEvent } from "./types.js";

const { Pool } = pg;

export const pool = new Pool({
  connectionString: process.env.DATABASE_URL ?? "postgresql://hookline:hookline@127.0.0.1:5433/hookline"
});

export type ExecutionRow = {
  id: string;
  event_id: string;
  flow: string;
  status: "queued" | "running" | "retrying" | "succeeded" | "dead";
  attempts: number;
  max_attempts: number;
  next_run_at: Date;
  last_error: string | null;
  replay_count: number;
  created_at: Date;
  finished_at: Date | null;
  duration_ms: number | null;
};

export type StepRow = {
  id: string;
  execution_id: string;
  name: string;
  position: number;
  status: "pending" | "running" | "succeeded" | "retrying" | "failed" | "skipped";
  attempts: number;
  started_at: Date | null;
  finished_at: Date | null;
  request: unknown;
  response: unknown;
  error: string | null;
};

export async function init(): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS events (
      id text PRIMARY KEY,
      source text NOT NULL,
      external_id text NOT NULL,
      type text NOT NULL,
      payload jsonb NOT NULL,
      signature_ok boolean NOT NULL,
      received_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE (source, external_id)
    );
    CREATE TABLE IF NOT EXISTS executions (
      id text PRIMARY KEY,
      event_id text NOT NULL REFERENCES events(id),
      flow text NOT NULL,
      status text NOT NULL,
      attempts integer NOT NULL DEFAULT 0,
      max_attempts integer NOT NULL DEFAULT 5,
      next_run_at timestamptz NOT NULL DEFAULT now(),
      last_error text,
      replay_count integer NOT NULL DEFAULT 0,
      created_at timestamptz NOT NULL DEFAULT now(),
      finished_at timestamptz,
      duration_ms integer
    );
    CREATE TABLE IF NOT EXISTS steps (
      id text PRIMARY KEY,
      execution_id text NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
      name text NOT NULL,
      position integer NOT NULL,
      status text NOT NULL DEFAULT 'pending',
      attempts integer NOT NULL DEFAULT 0,
      started_at timestamptz,
      finished_at timestamptz,
      request jsonb,
      response jsonb,
      error text,
      UNIQUE (execution_id, position)
    );
    CREATE INDEX IF NOT EXISTS idx_exec_status ON executions(status, next_run_at);
    CREATE INDEX IF NOT EXISTS idx_steps_exec ON steps(execution_id, position);
  `);
}

export async function ingestEvent(
  source: string,
  event: WebhookEvent,
  raw: unknown,
  signatureOk: boolean
): Promise<{ executionId: string; duplicate: boolean }> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const eventId = randomUUID();
    const inserted = await client.query(
      `INSERT INTO events (id, source, external_id, type, payload, signature_ok)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (source, external_id) DO NOTHING
       RETURNING id`,
      [eventId, source, event.id, event.type, raw, signatureOk]
    );
    if (!inserted.rowCount) {
      // Duplicate delivery: same source + external_id. Return the execution that
      // already exists instead of creating a second business action.
      const existing = await client.query(
        `SELECT e.id, x.id AS execution_id
         FROM events e JOIN executions x ON x.event_id = e.id
         WHERE e.source = $1 AND e.external_id = $2
         ORDER BY x.created_at LIMIT 1`,
        [source, event.id]
      );
      await client.query("COMMIT");
      return { executionId: existing.rows[0]?.execution_id ?? "", duplicate: true };
    }
    const executionId = randomUUID();
    await client.query(
      `INSERT INTO executions (id, event_id, flow, status, max_attempts)
       VALUES ($1, $2, $3, 'queued', $4)`,
      [executionId, eventId, "order-confirmed", Number(process.env.MAX_ATTEMPTS ?? 5)]
    );
    await client.query("COMMIT");
    return { executionId, duplicate: false };
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function claimNext(): Promise<ExecutionRow | null> {
  const result = await pool.query<ExecutionRow>(
    `UPDATE executions
     SET status = 'running', attempts = attempts + 1
     WHERE id = (
       SELECT id FROM executions
       WHERE status IN ('queued', 'retrying') AND next_run_at <= now()
       ORDER BY next_run_at
       LIMIT 1
       FOR UPDATE SKIP LOCKED
     )
     RETURNING *`
  );
  return result.rows[0] ?? null;
}

export async function finishExecution(
  id: string,
  status: "succeeded" | "dead",
  error: string | null = null
): Promise<void> {
  await pool.query(
    `UPDATE executions
     SET status = $2, last_error = $3, finished_at = now(),
         duration_ms = EXTRACT(EPOCH FROM (now() - created_at)) * 1000
     WHERE id = $1`,
    [id, status, error]
  );
}

export async function scheduleRetry(id: string, delayMs: number, error: string): Promise<void> {
  await pool.query(
    `UPDATE executions
     SET status = 'retrying', next_run_at = now() + ($3 || ' milliseconds')::interval, last_error = $2
     WHERE id = $1`,
    [id, error, String(delayMs)]
  );
}

export async function replay(id: string): Promise<{ ok: boolean; executionId?: string; reason?: string }> {
  const client = await pool.connect();
  try {
    const current = await client.query<ExecutionRow>("SELECT * FROM executions WHERE id = $1", [id]);
    if (!current.rowCount) return { ok: false, reason: "not_found" };
    const row = current.rows[0];
    if (row.status !== "dead" && row.status !== "succeeded") return { ok: false, reason: "not_finished" };
    const newId = randomUUID();
    await client.query("BEGIN");
    await client.query(
      `INSERT INTO executions (id, event_id, flow, status, max_attempts, replay_count)
       VALUES ($1, $2, $3, 'queued', $4, $5)`,
      [newId, row.event_id, row.flow, row.max_attempts, row.replay_count + 1]
    );
    await client.query(
      `INSERT INTO steps (id, execution_id, name, position, status)
       SELECT gen_random_uuid()::text, $1, name, position, 'pending'
       FROM steps WHERE execution_id = $2 ORDER BY position`,
      [newId, id]
    );
    await client.query("COMMIT");
    return { ok: true, executionId: newId };
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function getExecution(id: string) {
  const execution = await pool.query("SELECT * FROM executions WHERE id = $1", [id]);
  if (!execution.rowCount) return null;
  const steps = await pool.query("SELECT * FROM steps WHERE execution_id = $1 ORDER BY position", [id]);
  const event = await pool.query("SELECT * FROM events WHERE id = $1", [execution.rows[0].event_id]);
  return { execution: execution.rows[0], steps: steps.rows, event: event.rows[0] };
}

export async function listExecutions(limit = 50) {
  const result = await pool.query(
    `SELECT x.*, e.external_id AS event_external_id, e.type AS event_type
     FROM executions x JOIN events e ON e.id = x.event_id
     ORDER BY x.created_at DESC LIMIT $1`,
    [limit]
  );
  return result.rows;
}

export async function ensureSteps(executionId: string, names: { name: string; position: number }[]): Promise<void> {
  for (const step of names) {
    await pool.query(
      `INSERT INTO steps (id, execution_id, name, position, status)
       VALUES ($1, $2, $3, $4, 'pending')
       ON CONFLICT (execution_id, position) DO NOTHING`,
      [randomUUID(), executionId, step.name, step.position]
    );
  }
}

export async function stepStarted(id: string): Promise<void> {
  await pool.query(
    `UPDATE steps SET status = 'running', attempts = attempts + 1, started_at = now() WHERE id = $1`,
    [id]
  );
}

export async function stepFinished(
  id: string,
  status: "succeeded" | "failed" | "retrying",
  response: unknown,
  error: string | null
): Promise<void> {
  await pool.query(
    `UPDATE steps SET status = $2, response = $3, error = $4, finished_at = now() WHERE id = $1`,
    [id, status, response, error]
  );
}
