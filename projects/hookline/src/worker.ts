import { backoffMs } from "./signature.js";
import { ORDER_FLOW } from "./types.js";
import {
  claimNext,
  ensureSteps,
  finishExecution,
  getExecution,
  init,
  scheduleRetry,
  stepFinished,
  stepStarted
} from "./db.js";

const FAKES_URL = process.env.FAKES_URL ?? "http://127.0.0.1:4010";
const STEP_TIMEOUT_MS = Number(process.env.STEP_TIMEOUT_MS ?? 2500);
const POLL_MS = Number(process.env.WORKER_POLL_MS ?? 400);

type StepOutcome = { ok: true; response: unknown } | { ok: false; transient: boolean; error: string };

async function callStep(url: string, body: unknown): Promise<StepOutcome> {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(STEP_TIMEOUT_MS)
    });
    const text = await response.text();
    let parsed: unknown = text;
    try {
      parsed = JSON.parse(text);
    } catch {
      /* keep text */
    }
    if (response.ok || response.status === 409) return { ok: true, response: parsed };
    const transient = response.status >= 500 || response.status === 408 || response.status === 429;
    return { ok: false, transient, error: `HTTP ${response.status}: ${text.slice(0, 300)}` };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const timeout = /timeout|aborted/i.test(message);
    return { ok: false, transient: timeout || true, error: timeout ? "step timed out" : message };
  }
}

export async function runOnce(): Promise<boolean> {
  const execution = await claimNext();
  if (!execution) return false;

  await ensureSteps(
    execution.id,
    ORDER_FLOW.steps.map((step, index) => ({ name: step.name, position: index }))
  );

  const detail = await getExecution(execution.id);
  if (!detail) return true;
  const payload = detail.event.payload as Record<string, unknown>;
  const eventId = detail.event.external_id as string;

  for (const [index, config] of ORDER_FLOW.steps.entries()) {
    const step = detail.steps.find((candidate) => candidate.position === index);
    if (!step) continue;
    if (step.status === "succeeded") continue;

    await stepStarted(step.id);
    const idempotencyKey = `${execution.id}:${config.name}`;
    const body = {
      event_id: eventId,
      order_id: (payload.data as Record<string, unknown>)?.order_id,
      items: (payload.data as Record<string, unknown>)?.items,
      failure_mode: (payload.data as Record<string, unknown>)?.failure_mode ?? "happy",
      idempotency_key: config.idempotent ? idempotencyKey : null
    };
    const result = await callStep(`${FAKES_URL}${config.path}`, body);

    if (result.ok) {
      await stepFinished(step.id, "succeeded", result.response, null);
      continue;
    }

    if (!result.transient) {
      await stepFinished(step.id, "failed", null, result.error);
      await finishExecution(execution.id, "dead", `${config.name}: ${result.error}`);
      return true;
    }

    await stepFinished(step.id, "retrying", null, result.error);
    if (execution.attempts >= execution.max_attempts) {
      await finishExecution(
        execution.id,
        "dead",
        `${config.name}: ${result.error} (gave up after ${execution.attempts} attempts)`
      );
      return true;
    }
    await scheduleRetry(execution.id, backoffMs(execution.attempts), `${config.name}: ${result.error}`);
    return true;
  }

  await finishExecution(execution.id, "succeeded");
  return true;
}

async function main(): Promise<void> {
  await init();
  console.log(JSON.stringify({ level: "info", msg: "hookline worker started", fakes: FAKES_URL }));
  let running = true;
  const shutdown = () => {
    running = false;
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
  while (running) {
    try {
      const worked = await runOnce();
      if (!worked) await new Promise((resolve) => setTimeout(resolve, POLL_MS));
    } catch (error) {
      console.error(JSON.stringify({ level: "error", msg: "worker loop failed", error: String(error) }));
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  process.exit(0);
}

if (process.argv[1]?.endsWith("worker.js") || process.argv[1]?.endsWith("worker.ts")) {
  void main();
}
