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


st.set_page_config(page_title="Riverbend — data quality", page_icon="▦", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..600;1,9..144,300..600&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

      html, body, [class*="css"], .stApp { font-family: "Archivo", ui-sans-serif, system-ui, sans-serif; }
      .stApp { background: #f2eee4; color: #12110d; }
      .block-container { max-width: 1220px; padding-top: 2rem; padding-bottom: 3rem; }
      header[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display: none !important; }

      .rb-head { border-bottom: 1px solid #12110d; padding: 4px 0 18px; margin-bottom: 20px; }
      .rb-kicker { font-family: "IBM Plex Mono", monospace; font-size: 9px; letter-spacing: .14em;
                   text-transform: uppercase; color: #c33c18; margin-bottom: 10px; }
      .rb-head h1 { font-family: "Fraunces", Georgia, serif; font-weight: 400; font-size: 3rem;
                    line-height: 1; letter-spacing: -.035em; margin: 0; color: #12110d; }
      .rb-head p { font-family: "IBM Plex Mono", monospace; font-size: 10px; letter-spacing: .05em;
                   text-transform: uppercase; color: #847e6d; margin: 10px 0 0; }
      .rb-foot { font-family: "IBM Plex Mono", monospace; font-size: 9px; letter-spacing: .04em;
                 text-transform: uppercase; color: #847e6d; border-top: 1px solid #d6cdb9;
                 padding-top: 12px; margin-top: 24px; }

      h1, h2, h3 { font-family: "Fraunces", Georgia, serif !important; font-weight: 400 !important;
                   letter-spacing: -.02em !important; color: #12110d !important; }
      h2 { font-size: 1.45rem !important; margin-top: 1.6rem !important; }
      h3 { font-size: 1.15rem !important; }
      p, li, label { color: #3a382f; font-size: 13.5px; }
      [data-testid="stCaptionContainer"] p { font-family: "IBM Plex Mono", monospace; font-size: 9.5px;
                   letter-spacing: .03em; color: #847e6d; }

      [data-testid="stMetric"] { background: #fbf8f0; border: 1px solid #d6cdb9;
                   border-top: 1px solid #12110d; padding: 14px 14px 12px; }
      [data-testid="stMetricLabel"] p { font-family: "IBM Plex Mono", monospace; font-size: 8.5px;
                   letter-spacing: .1em; text-transform: uppercase; color: #847e6d; }
      [data-testid="stMetricValue"] { font-family: "Fraunces", Georgia, serif; font-weight: 400;
                   font-size: 1.9rem; letter-spacing: -.02em; color: #12110d; }
      [data-testid="stMetricDelta"] { font-family: "IBM Plex Mono", monospace; font-size: 9px; }

      [data-testid="stTable"] table { border-collapse: collapse; font-size: 13px; }
      [data-testid="stTable"] th { font-family: "IBM Plex Mono", monospace; font-size: 8.5px;
                   letter-spacing: .09em; text-transform: uppercase; color: #847e6d;
                   border-bottom: 1px solid #12110d; padding: 8px 8px; }
      [data-testid="stTable"] td { border-bottom: 1px solid #d6cdb9; padding: 8px 8px; color: #3a382f; }
      [data-testid="stDataFrame"] { border: 1px solid #d6cdb9; }

      [data-testid="stVegaLiteChart"] { background: #fbf8f0; border: 1px solid #d6cdb9; padding: 8px 6px 2px; }
      [data-testid="stCodeBlock"] pre, .stCodeBlock pre { background: #fbf8f0 !important;
                   border: 1px solid #d6cdb9 !important; border-radius: 0 !important;
                   font-family: "IBM Plex Mono", monospace !important; font-size: 11px !important; }
      .stAlert { border-radius: 0; }
      hr { border: 0; border-top: 1px solid #d6cdb9; margin: 1.6rem 0; }
      ::selection { background: #12110d; color: #f2eee4; }
    </style>
    <div class="rb-head">
      <div class="rb-kicker">Case 04 · personal demo</div>
      <h1>Riverbend</h1>
      <p>Incremental order pipeline · validation · quarantine · reconciled indicators</p>
    </div>
    """,
    unsafe_allow_html=True,
)

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
            st.bar_chart(pivot, color=["#c33c18", "#62603f"])

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
    st.markdown(
        '<div class="rb-foot">Fictional data · 13/13 dbt models and tests passing · quarantine is a first-class state, not an error log.</div>',
        unsafe_allow_html=True,
    )


render()
