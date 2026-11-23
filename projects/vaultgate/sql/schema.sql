-- Run as vault_owner.
create table if not exists orgs (
  id text primary key, name text not null
);
create table if not exists users (
  id text primary key, org_id text not null references orgs(id), name text not null,
  role text not null check (role in ('admin','user')), password_hash text not null
);
create table if not exists sessions (
  token_hash text primary key, user_id text not null references users(id), org_id text not null references orgs(id),
  expires_at timestamptz not null, revoked_at timestamptz
);
create table if not exists files (
  id text primary key, org_id text not null references orgs(id), name text not null,
  content_type text not null, bytes bytea not null, created_at timestamptz not null default now()
);
create table if not exists audit (
  id bigserial primary key, org_id text not null, actor_id text not null, action text not null,
  detail jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);

alter table files enable row level security;
alter table files force row level security;
alter table audit enable row level security;
alter table audit force row level security;

drop policy if exists files_tenant on files;
create policy files_tenant on files
  using (org_id = current_setting('app.org_id', true))
  with check (org_id = current_setting('app.org_id', true));

drop policy if exists audit_tenant on audit;
create policy audit_tenant on audit
  using (org_id = current_setting('app.org_id', true))
  with check (org_id = current_setting('app.org_id', true));

grant usage on schema public to vault_app;
grant select on orgs, users, sessions to vault_app;
grant insert, update on sessions to vault_app;
grant select, insert on files to vault_app;
grant select, insert on audit to vault_app;
grant usage, select on sequence audit_id_seq to vault_app;
revoke update, delete on audit from vault_app;
revoke update, delete on files from vault_app;
