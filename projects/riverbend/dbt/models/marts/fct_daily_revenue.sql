select
  order_date,
  currency,
  count(*) as orders,
  sum(paid_amount_cents) as paid_revenue_cents,
  round(avg(paid_amount_cents) filter (where status = 'paid'), 0) as avg_paid_order_cents
from {{ ref('stg_orders') }}
group by 1, 2
order by 1, 2
