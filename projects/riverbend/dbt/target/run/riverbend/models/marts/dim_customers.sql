
    

    create  table
      "riverbend"."marts"."dim_customers__dbt_tmp"
  
    
    as (
      select
  customer_id,
  count(*) as orders,
  sum(paid_amount_cents) as lifetime_paid_cents,
  min(order_date) as first_order_date,
  max(order_date) as last_order_date
from "riverbend"."marts"."stg_orders"
group by 1
order by lifetime_paid_cents desc
    );
    
  