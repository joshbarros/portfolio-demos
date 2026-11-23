
  
  create view "riverbend"."marts"."stg_orders__dbt_tmp" as (
    select
  order_id,
  customer_id,
  cast(order_ts as date) as order_date,
  amount_cents,
  currency,
  status,
  updated_at,
  cast(updated_at as date) as updated_date,
  case when status = 'paid' then amount_cents else 0 end as paid_amount_cents
from "riverbend"."analytics"."orders"
  );
