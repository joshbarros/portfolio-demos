import { createHmac, timingSafeEqual } from "node:crypto";

export const MAX_SKEW_SECONDS = 300;

export function sign(secret: string, timestamp: string, rawBody: string): string {
  const digest = createHmac("sha256", secret).update(`${timestamp}.${rawBody}`).digest("hex");
  return `v1=${digest}`;
}

export type VerifyResult =
  | { ok: true }
  | { ok: false; reason: "missing_signature" | "bad_timestamp" | "stale" | "bad_signature" };

export function verify(
  secret: string,
  headers: { signature?: string; timestamp?: string },
  rawBody: string,
  nowSeconds = Math.floor(Date.now() / 1000)
): VerifyResult {
  if (!headers.signature || !headers.timestamp) return { ok: false, reason: "missing_signature" };
  const timestamp = Number(headers.timestamp);
  if (!Number.isFinite(timestamp)) return { ok: false, reason: "bad_timestamp" };
  // Replaying an old signed request is rejected, so a captured payload has a
  // short useful life even if the signature is valid.
  if (Math.abs(nowSeconds - timestamp) > MAX_SKEW_SECONDS) return { ok: false, reason: "stale" };
  const expected = sign(secret, headers.timestamp, rawBody);
  const a = Buffer.from(expected);
  const b = Buffer.from(headers.signature);
  if (a.length !== b.length) return { ok: false, reason: "bad_signature" };
  return timingSafeEqual(a, b) ? { ok: true } : { ok: false, reason: "bad_signature" };
}

/** Exponential backoff with full jitter, capped at 30 seconds. */
export function backoffMs(attempt: number, baseMs = 400, capMs = 30_000, random = Math.random): number {
  const exp = Math.min(capMs, baseMs * 2 ** Math.max(0, attempt - 1));
  return Math.floor(exp * (0.5 + random() * 0.5));
}
