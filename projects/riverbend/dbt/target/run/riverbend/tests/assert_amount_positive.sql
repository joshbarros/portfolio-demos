
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  -- Business rule: no order may have a non-positive amount.
select order_id, amount_cents
from "riverbend"."marts"."stg_orders"
where amount_cents <= 0
  
  
      
    ) dbt_internal_test