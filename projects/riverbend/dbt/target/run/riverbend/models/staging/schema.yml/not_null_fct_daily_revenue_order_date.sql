
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select order_date
from "riverbend"."marts"."fct_daily_revenue"
where order_date is null



  
  
      
    ) dbt_internal_test