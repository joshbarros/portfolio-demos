-- Target-only changes applied after restore.
alter table customers add column if not exists region text;
update customers set region = case
  when id = 'cus_01' then 'EU'
  when id = 'cus_02' then 'US'
  else 'US'
end where region is null;
alter table customers alter column region set not null;
create index if not exists idx_orders_customer on orders(customer_id);
