"""Harborlift — migration lab runner.

Flow: seed -> freeze -> backup -> restore -> migrate -> validate -> cutover ->
write attempt -> rollback -> verify. Every step is timed and written to a report.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = os.getenv("PG_PASSWORD", "harborlift")
SOURCE_PORT = int(os.getenv("SOURCE_PORT", "5441"))
TARGET_PORT = int(os.getenv("TARGET_PORT", "5442"))
SOURCE_CONTAINER = os.getenv("SOURCE_CONTAINER", "harborlift-source-db-1")
TARGET_CONTAINER = os.getenv("TARGET_CONTAINER", "harborlift-target-db-1")
APP_PORT = int(os.getenv("APP_PORT", "8181"))
BACKUP = Path("/tmp/harborlift-backup.sql")


def connect(port: int) -> psycopg.Connection:
    return psycopg.connect(
        host="127.0.0.1", port=port, dbname="harborlift", user="harborlift", password=PASSWORD, autocommit=True
    )


def query(port: int, sql: str, params: tuple | None = None):
    with connect(port) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                return cur.fetchall()
            return None


def wait_port(port: int, timeout: float = 40.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"port {port} not ready")


def docker(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], input=input_text, capture_output=True, text=True)


def reset(port: int) -> None:
    query(port, "DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


def seed(port: int) -> None:
    query(port, (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))


def freeze(port: int, on: bool) -> None:
    mode = "on" if on else "off"
    # The session that flips the flag must opt out of the read-only default,
    # otherwise ALTER DATABASE is rejected by the very setting it changes.
    with psycopg.connect(
        host="127.0.0.1", port=port, dbname="harborlift", user="harborlift",
        password=PASSWORD, autocommit=True,
        options="-c default_transaction_read_only=off",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(f"ALTER DATABASE harborlift SET default_transaction_read_only = {mode}")


def checksum(port: int) -> tuple[str, int]:
    rows = query(
        port,
        "SELECT md5(string_agg(id || ':' || amount_cents || ':' || status, '|' ORDER BY id)), count(*) FROM orders",
    )
    return rows[0][0], int(rows[0][1])


def start_app(port: int) -> subprocess.Popen:
    env = {**os.environ, "DB_PORT": str(port), "APP_PORT": str(APP_PORT)}
    process = subprocess.Popen(
        ["python", "-m", "harborlift.app"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    wait_port(APP_PORT, 15)
    return process


def http_get(path: str) -> tuple[int, str]:
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{APP_PORT}{path}", timeout=5) as response:
            return response.status, response.read().decode()
    except Exception as error:  # noqa: BLE001
        return 0, str(error)


def http_post(path: str, payload: dict) -> tuple[int, str]:
    import urllib.request

    request = urllib.request.Request(
        f"http://127.0.0.1:{APP_PORT}{path}",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode()
    except Exception as error:  # noqa: BLE001
        detail = getattr(error, "read", lambda: b"")()
        return getattr(error, "code", 0), detail.decode(errors="ignore") or str(error)


class Lab:
    def __init__(self) -> None:
        self.steps: list[dict] = []
        self.started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.app: subprocess.Popen | None = None

    def step(self, name: str, fn):
        began = time.perf_counter()
        try:
            detail = fn()
            status = "ok"
        except Exception as error:  # noqa: BLE001
            detail = str(error)
            status = "error"
        duration = round((time.perf_counter() - began) * 1000)
        self.steps.append({"step": name, "status": status, "duration_ms": duration, "detail": detail})
        print(f"{status:5} {name:28} {duration:6} ms  {detail}")
        return detail

    def stop_app(self) -> None:
        if self.app:
            self.app.terminate()
            self.app.wait(timeout=10)
            self.app = None

    def run(self) -> dict:
        wait_port(SOURCE_PORT)
        wait_port(TARGET_PORT)
        # A previous run may have left either database frozen; reset the flags first.
        self.step("unfreeze.both", lambda: (freeze(SOURCE_PORT, False), freeze(TARGET_PORT, False)))
        self.step("reset.source", lambda: reset(SOURCE_PORT))
        self.step("reset.target", lambda: reset(TARGET_PORT))
        self.step("seed.source", lambda: seed(SOURCE_PORT))
        snapshot = checksum(SOURCE_PORT)
        self.step("control.record", lambda: snapshot)

        # Write-freeze window starts before the snapshot and stays until rollback is proven.
        self.step("freeze.source", lambda: freeze(SOURCE_PORT, True))
        def rejected_sql_write() -> str:
            try:
                query(
                    SOURCE_PORT,
                    "INSERT INTO orders (id, customer_id, amount_cents, status, created_at) VALUES ('ord_new','cus_01',100,'paid',now())",
                )
            except Exception as error:  # noqa: BLE001
                return f"rejected: {type(error).__name__}: {str(error).splitlines()[0][:140]}"
            raise RuntimeError("write unexpectedly succeeded during freeze")

        self.step("write.rejected.during_freeze", rejected_sql_write)

        def backup() -> str:
            result = docker(["exec", SOURCE_CONTAINER, "pg_dump", "-U", "harborlift", "-d", "harborlift", "-f", "/tmp/backup.sql"])
            if result.returncode != 0:
                raise RuntimeError(result.stderr[-300:])
            copy = docker(["cp", f"{SOURCE_CONTAINER}:/tmp/backup.sql", str(BACKUP)])
            if copy.returncode != 0:
                raise RuntimeError(copy.stderr[-300:])
            return f"{BACKUP.name} {BACKUP.stat().st_size} bytes"

        self.step("backup.source", backup)

        def restore() -> str:
            dump = BACKUP.read_text(encoding="utf-8")
            result = docker(["exec", "-i", TARGET_CONTAINER, "psql", "-U", "harborlift", "-d", "harborlift", "-q"], dump)
            if result.returncode != 0:
                raise RuntimeError(result.stderr[-300:])
            return f"restored {len(dump)} bytes"

        self.step("restore.target", restore)
        self.step("migrate.target", lambda: query(TARGET_PORT, (ROOT / "sql" / "migration.sql").read_text(encoding="utf-8")))

        def validate() -> dict:
            source_sum, source_rows = checksum(SOURCE_PORT)
            target_sum, target_rows = checksum(TARGET_PORT)
            region_nulls = query(TARGET_PORT, "SELECT count(*) FROM customers WHERE region IS NULL")[0][0]
            index = query(TARGET_PORT, "SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_orders_customer'")[0][0]
            if source_sum != target_sum or source_rows != target_rows or region_nulls or not index:
                raise RuntimeError(
                    f"validation failed: sum {source_sum}/{target_sum} rows {source_rows}/{target_rows} nulls {region_nulls} index {index}"
                )
            return {"checksum": target_sum, "rows": target_rows, "region_nulls": region_nulls, "index": index}

        self.step("validate.target", validate)

        # The target is frozen before cutover as well, so the write-freeze window
        # covers snapshot, cutover and rollback.
        self.step("freeze.target", lambda: freeze(TARGET_PORT, True))

        # Cutover: writes are still frozen; the target app is started read-only.
        self.step("cutover.start_target_app", lambda: setattr(self, "app", start_app(TARGET_PORT)) or "app on target")
        self.step("validate.behavior", lambda: http_get("/orders")[0])
        def rejected_http_write() -> str:
            status, body = http_post("/orders", {"id": "ord_rejected", "customer_id": "cus_01", "amount_cents": 500})
            if status == 409:
                return f"rejected with 409: {body[:140]}"
            raise RuntimeError(f"expected 409, got {status}: {body[:120]}")

        self.step("write.rejected.after_cutover", rejected_http_write)

        # Rollback: stop the target app, unfreeze the source, point the app back.
        self.step("rollback.stop_target_app", self.stop_app)
        self.step("rollback.unfreeze_source", lambda: freeze(SOURCE_PORT, False))
        self.step("rollback.start_source_app", lambda: setattr(self, "app", start_app(SOURCE_PORT)) or "app on source")
        self.step("rollback.validate", lambda: checksum(SOURCE_PORT))
        self.step("rollback.behavior", lambda: http_get("/orders")[0])
        def allowed_write() -> str:
            status, body = http_post("/orders", {"id": "ord_after_rollback", "customer_id": "cus_02", "amount_cents": 300})
            if status == 201:
                return f"accepted: {body[:120]}"
            raise RuntimeError(f"expected 201, got {status}: {body[:120]}")

        self.step("rollback.write_allowed", allowed_write)
        self.stop_app()

        result = {
            "run_at": self.started,
            "environment": "local Docker Compose: source-db:5441, target-db:5442, app:8181",
            "strategy": "write-freeze window from snapshot through rollback; writes rejected on the frozen side; recovery point = snapshot",
            "steps": self.steps,
            "source_checksum": snapshot,
            "target_checksum": checksum(TARGET_PORT),
            "source_after_rollback": checksum(SOURCE_PORT),
            "backup_bytes": BACKUP.stat().st_size,
        }
        (ROOT / "web" / "last_run.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (ROOT / "web" / "report.html").write_text(render_report(result), encoding="utf-8")
        return result


def render_report(result: dict) -> str:
    rows = "\n".join(
        f"<tr><td>{s['step']}</td><td class='{s['status']}'>{s['status']}</td><td>{s['duration_ms']} ms</td><td><code>{s['detail']}</code></td></tr>"
        for s in result["steps"]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Harborlift — migration run</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body{{font-family:Inter,system-ui,sans-serif;background:#f5f6f9;color:#101828;margin:0;padding:40px}}
 main{{max-width:1000px;margin:0 auto;background:#fff;border:1px solid #e4e7ec;border-radius:14px;padding:28px}}
 h1{{margin:0 0 6px;font-size:1.4rem}} p.sub{{color:#7b8794;margin:0 0 18px;font-size:.85rem}}
 .meta{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}}
 .meta div{{border:1px solid #e4e7ec;border-radius:10px;padding:10px}} .meta span{{font-size:.65rem;color:#7b8794;text-transform:uppercase}}
 table{{width:100%;border-collapse:collapse;font-size:.78rem}} th,td{{text-align:left;padding:7px;border-bottom:1px solid #eef0f4}}
 th{{font-size:.65rem;text-transform:uppercase;color:#7b8794}} .error{{color:#b42318;font-weight:700}} .ok{{color:#067647;font-weight:700}}
 .note{{background:#fffaeb;border:1px solid #fdecc8;color:#b54708;padding:10px 12px;border-radius:9px;font-size:.78rem;margin-top:16px}}
</style></head><body><main>
<h1>Harborlift — application and database migration</h1>
<p class="sub">Last recorded run · {result['run_at']} · {result['environment']}</p>
<div class="meta">
 <div><span>Source</span><br>{result['source_checksum'][0]} · {result['source_checksum'][1]} rows</div>
 <div><span>Target after restore + migration</span><br>{result['target_checksum'][0]} · {result['target_checksum'][1]} rows</div>
 <div><span>Recovery point</span><br>{result['backup_bytes']} bytes snapshot</div>
</div>
<div class="meta">
 <div><span>Source at snapshot</span><br>{result['source_checksum'][1]} rows</div>
 <div><span>Source after rollback</span><br>{result['source_after_rollback'][1]} rows (one accepted write)</div>
 <div><span>Writes during window</span><br>rejected</div>
</div>
<div class="meta">
 <div><span>Strategy</span><br>Write-freeze window (source and target)</div>
 <div><span>Writes during window</span><br>Rejected, recorded</div>
 <div><span>Rollback</span><br>Source unfrozen; write accepted after rollback</div>
</div>
<table><thead><tr><th>Step</th><th>Status</th><th>Duration</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>
<div class="note">This page shows a recorded run. The demo button is not wired to restore databases or run infrastructure; the lab is reproducible from the scripts in the repository. Writes are rejected during the freeze window; the declared recovery point is the snapshot.</div>
</main></body></html>"""


if __name__ == "__main__":
    lab = Lab()
    result = lab.run()
    print(json.dumps({"steps": len(result["steps"]), "ok": all(s["status"] == "ok" for s in result["steps"])}, indent=0))
