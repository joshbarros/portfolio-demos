
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select amount_cents
from "riverbend"."marts"."stg_orders"
where amount_cents is null



  
  
      
    ) dbt_internal_test