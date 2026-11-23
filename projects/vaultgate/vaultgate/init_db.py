"""Idempotent database bootstrap for the demo."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
ADMIN = os.getenv("VAULT_ADMIN_DSN", "postgresql://postgres:vaultgate@127.0.0.1:5443/vaultgate")
OWNER = os.getenv("VAULT_OWNER_DSN", "postgresql://vault_owner:vault_owner@127.0.0.1:5443/vaultgate")


def main() -> None:
    with psycopg.connect(ADMIN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute((ROOT / "sql" / "roles.sql").read_text())
    with psycopg.connect(OWNER, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute((ROOT / "sql" / "schema.sql").read_text())
    password = hashlib.sha256(b"demo").hexdigest()
    with psycopg.connect(ADMIN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("insert into orgs (id,name) values ('org_alpha','Alpha Freight'),('org_beta','Beta Clinic') on conflict do nothing")
            cur.execute(
                """insert into users (id,org_id,name,role,password_hash) values
                   ('user_alpha_admin','org_alpha','Alice Alpha','admin',%s),
                   ('user_beta_user','org_beta','Bob Beta','user',%s)
                   on conflict do nothing""",
                [password, password],
            )
            cur.execute(
                """insert into files (id,org_id,name,content_type,bytes) values
                   ('file_alpha_brief','org_alpha','alpha-brief.txt','text/plain',convert_to('Alpha confidential brief\nDemo data only.','UTF8')),
                   ('file_alpha_rates','org_alpha','alpha-rates.csv','text/csv',convert_to('lane,rate\nBR-US,4200\n','UTF8')),
                   ('file_beta_notes','org_beta','beta-notes.txt','text/plain',convert_to('Beta confidential notes\nDemo data only.','UTF8'))
                   on conflict do nothing"""
            )
    print("vaultgate database ready")


if __name__ == "__main__":
    main()
