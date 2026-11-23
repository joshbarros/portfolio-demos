from pathlib import Path

import pytest

from riverbend.pipeline import Pipeline

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture()
def pipe():
    return Pipeline(":memory:")


def test_initial_load_quarantines_invalid_rows(pipe):
    run = pipe.run_csv(DATA / "orders_v1.csv")
    assert run.status == "succeeded"
    assert (run.rows_seen, run.rows_valid, run.rows_quarantined) == (8, 4, 4)
    reasons = sorted(q["reason"] for q in run.quarantine)
    assert "missing amount_cents" in reasons
    assert "amount_cents must be positive" in reasons
    assert "unknown status unknown" in reasons
    assert "unsupported currency EUR" in reasons
    assert pipe.metrics()["orders"] == 4


def test_rerun_is_idempotent(pipe):
    pipe.run_csv(DATA / "orders_v1.csv")
    before = pipe.metrics()
    run = pipe.run_csv(DATA / "orders_v1.csv")
    assert run.skipped is True
    assert pipe.metrics() == before


def test_new_records_and_correction_are_applied(pipe):
    pipe.run_csv(DATA / "orders_v1.csv")
    run = pipe.run_csv(DATA / "orders_v2.csv")
    assert run.rows_valid == 3
    assert run.rows_upserted == 3
    metrics = pipe.metrics()
    assert metrics["orders"] == 7
    amount = pipe.conn.execute("SELECT amount_cents FROM analytics.orders WHERE order_id='ord_1004'").fetchone()[0]
    assert amount == 9900  # corrected from a quarantined row


def test_late_older_event_does_not_overwrite(pipe, tmp_path):
    pipe.run_csv(DATA / "orders_v1.csv")
    late = tmp_path / "late.csv"
    late.write_text(
        "order_id,customer_id,order_ts,amount_cents,currency,status,updated_at\n"
        "ord_1001,cus_01,2026-11-01T10:00:00Z,1,USD,paid,2026-10-01T10:05:00Z\n",
        encoding="utf-8",
    )
    run = pipe.run_csv(late)
    amount = pipe.conn.execute("SELECT amount_cents FROM analytics.orders WHERE order_id='ord_1001'").fetchone()[0]
    assert amount == 12500
    assert run.rows_upserted == 0


def test_api_page_adds_and_updates(pipe):
    pipe.run_csv(DATA / "orders_v1.csv")
    run = pipe.run_api(DATA / "api_page_1.json")
    assert run.rows_seen == 2
    assert run.rows_upserted == 2  # ord_1011 new, ord_1006 corrected from quarantine
    status = pipe.conn.execute("SELECT status FROM analytics.orders WHERE order_id='ord_1006'").fetchone()[0]
    assert status == "paid"


def test_reconciliation_matches_manual_sum(pipe):
    pipe.run_csv(DATA / "orders_v1.csv")
    pipe.run_csv(DATA / "orders_v2.csv")
    pipe.run_api(DATA / "api_page_1.json")
    metrics = pipe.metrics()
    manual = pipe.conn.execute(
        "SELECT COALESCE(SUM(amount_cents),0) FROM analytics.orders WHERE status='paid'"
    ).fetchone()[0]
    assert metrics["paid_revenue_cents"] == manual
    assert pipe.reconcile()["paid_revenue_cents"] == manual


def test_run_history_and_failure(pipe, tmp_path):
    pipe.run_csv(DATA / "orders_v1.csv")
    broken = tmp_path / "broken.csv"
    broken.write_text("not,a,valid\ncsv,file,here\n", encoding="utf-8")
    run = pipe.run_csv(broken)
    assert run.status == "succeeded"  # rows are quarantined, not a crash
    assert run.rows_quarantined == 1
    runs = pipe.conn.execute("SELECT COUNT(*) FROM ops.runs").fetchone()[0]
    assert runs == 2
