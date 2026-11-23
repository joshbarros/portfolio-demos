"""Minimal legacy application: reads and writes orders from Postgres."""
from __future__ import annotations

import os

import psycopg
from flask import Flask, jsonify, request

app = Flask(__name__)
PORT = int(os.getenv("DB_PORT", "5441"))


def conn() -> psycopg.Connection:
    return psycopg.connect(
        host="127.0.0.1", port=PORT, dbname="harborlift", user="harborlift",
        password=os.getenv("PG_PASSWORD", "harborlift"), autocommit=True,
    )


@app.get("/health")
def health():
    return {"ok": True, "db_port": PORT}


@app.get("/orders")
def orders():
    with conn() as c, c.cursor() as cur:
        cur.execute("select id, customer_id, amount_cents, status from orders order by id")
        rows = [{"id": r[0], "customer_id": r[1], "amount_cents": r[2], "status": r[3]} for r in cur.fetchall()]
    return jsonify(orders=rows, count=len(rows))


@app.post("/orders")
def create_order():
    body = request.get_json(force=True)
    try:
        with conn() as c, c.cursor() as cur:
            cur.execute(
                "insert into orders (id, customer_id, amount_cents, status, created_at) values (%s,%s,%s,'paid',now()) returning id",
                (body["id"], body["customer_id"], int(body["amount_cents"])),
            )
            new_id = cur.fetchone()[0]
        return {"ok": True, "id": new_id}, 201
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "error": str(error)}, 409


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("APP_PORT", "8181")), debug=False)
