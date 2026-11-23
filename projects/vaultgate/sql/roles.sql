-- Run as the postgres superuser, once.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'vault_owner') then
    create role vault_owner login password 'vault_owner';
  end if;
  if not exists (select 1 from pg_roles where rolname = 'vault_app') then
    create role vault_app login password 'vault_app';
  end if;
end $$;

alter schema public owner to vault_owner;
