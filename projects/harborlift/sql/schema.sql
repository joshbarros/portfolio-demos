create table if not exists customers (
  id text primary key, name text not null, email text not null
);
create table if not exists orders (
  id text primary key, customer_id text not null references customers(id),
  amount_cents integer not null check (amount_cents > 0),
  status text not null, created_at timestamptz not null
);
create table if not exists control (
  id text primary key, checksum text not null, row_count integer not null, created_at timestamptz not null default now()
);
insert into customers (id, name, email) values
  ('cus_01','Ada Lovelace','ada@example.com'),
  ('cus_02','Grace Hopper','grace@example.com'),
  ('cus_03','Alan Turing','alan@example.com');
insert into orders (id, customer_id, amount_cents, status, created_at) values
  ('ord_1001','cus_01',12500,'paid','2026-11-01T10:00:00Z'),
  ('ord_1002','cus_02',8900,'paid','2026-11-01T11:00:00Z'),
  ('ord_1003','cus_03',15900,'paid','2026-11-02T09:30:00Z'),
  ('ord_1004','cus_01',9900,'refunded','2026-11-02T14:00:00Z'),
  ('ord_1005','cus_02',4200,'paid','2026-11-03T12:00:00Z'),
  ('ord_1006','cus_03',21000,'cancelled','2026-11-04T18:00:00Z');
insert into control (id, checksum, row_count)
select 'orders_v1',
       md5(string_agg(id || ':' || amount_cents || ':' || status, '|' order by id)),
       count(*)
from orders;
