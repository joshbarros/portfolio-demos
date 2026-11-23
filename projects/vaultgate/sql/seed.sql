insert into orgs (id, name) values ('org_alpha','Alpha Freight'), ('org_beta','Beta Clinic') on conflict do nothing;
insert into users (id, org_id, name, role, password_hash) values
  ('user_alpha_admin','org_alpha','Alice Alpha','admin','x'),
  ('user_beta_user','org_beta','Bob Beta','user','x')
on conflict do nothing;
insert into files (id, org_id, name, content_type, bytes) values
  ('file_alpha_brief','org_alpha','alpha-brief.txt','text/plain', convert_to('Alpha confidential brief','UTF8')),
  ('file_beta_notes','org_beta','beta-notes.txt','text/plain', convert_to('Beta confidential notes','UTF8'))
on conflict do nothing;
