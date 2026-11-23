"""Riverbend dashboard — read-only view of the pipeline output."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB = Path(__file__).resolve().parents[1] / "data" / "riverbend.duckdb"


@st.cache_data(ttl=5)
def query(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(DB), read_only=True) as conn:
        return conn.execute(sql).df()


st.set_page_config(page_title="Riverbend — data quality", page_icon="🌊", layout="wide")
st.title("Riverbend")
st.caption("Incremental order pipeline · validation · quarantine · reconciled indicators")

if not DB.exists():
    st.error("Database not found. Run `python -m riverbend.cli seed` first.")
    st.stop()

@st.fragment
def render() -> None:

    metrics = query(
        """
        select
          count(*) as orders,
          coalesce(sum(amount_cents) filter (where status='paid'), 0) as paid_revenue_cents,
          coalesce(round(avg(amount_cents) filter (where status='paid')), 0) as avg_paid_cents,
          count(*) filter (where status='cancelled') as cancelled,
          count(*) filter (where status='refunded') as refunded
        from analytics.orders
        """
    ).iloc[0]
    quarantine = query(
        """
        select count(*) as n from raw.quarantine q
        where not exists (select 1 from analytics.orders o where o.order_id = q.order_id)
        """
    ).iloc[0]["n"]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Orders", f"{int(metrics['orders']):,}")
    col2.metric("Paid revenue", f"${metrics['paid_revenue_cents'] / 100:,.2f}")
    col3.metric("Avg paid order", f"${metrics['avg_paid_cents'] / 100:,.2f}")
    col4.metric("Cancellation rate", f"{(metrics['cancelled'] / metrics['orders']):.1%}" if metrics["orders"] else "0%")
    col5.metric("Open quarantine", f"{int(quarantine):,}")

    st.divider()

    left, right = st.columns((2, 1))
    with left:
        st.subheader("Paid revenue by day and currency")
        revenue = query(
            """
            select order_date, currency, sum(paid_revenue_cents) / 100.0 as revenue
            from marts.fct_daily_revenue
            group by 1, 2 order by 1
            """
        )
        if revenue.empty:
            st.info("Run dbt to populate the marts.")
        else:
            pivot = revenue.pivot(index="order_date", columns="currency", values="revenue").fillna(0)
            st.bar_chart(pivot)

        st.subheader("Orders by status")
        status = query("select status, count(*) as orders from analytics.orders group by 1 order by 2 desc")
        st.table(status)

    with right:
        st.subheader("Latest runs")
        runs = query(
            """
            select source, status, rows_seen, rows_valid, rows_quarantined, rows_upserted,
                   substr(started_at, 1, 19) as started_at
            from ops.runs order by started_at desc limit 8
            """
        )
        st.table(runs)

        st.subheader("Quarantine reasons (historical)")
        reasons = query(
            """
            select reason, count(*) as rows
            from raw.quarantine group by 1 order by 2 desc
            """
        )
        st.table(reasons)

    st.divider()
    st.subheader("Quarantine detail")
    st.table(
        query(
            """
            select order_id, reason, substr(quarantined_at, 1, 19) as quarantined_at
            from raw.quarantine order by quarantined_at desc limit 8
            """
        )
    )

    st.subheader("Reconciliation")
    st.caption("The indicator above is recomputed directly from analytics.orders; dbt marts read the same rows.")
    st.code(
        "select sum(amount_cents) from analytics.orders where status = 'paid'",
        language="sql",
    )
    st.caption(
        f"Watermark (newest updated_at processed): {query('select max(last_updated_at) as w from ops.watermarks').iloc[0]['w']}"
    )


render()
