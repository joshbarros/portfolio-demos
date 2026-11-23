import hashlib
import os
from pathlib import Path

import psycopg
import pytest

from vaultgate import core

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.getenv("VAULT_ADMIN_DSN", "postgresql://postgres:vaultgate@127.0.0.1:5443/vaultgate")


@pytest.fixture(scope="session", autouse=True)
def database():
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute((ROOT / "sql" / "roles.sql").read_text())
    with psycopg.connect(core.OWNER_DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute((ROOT / "sql" / "schema.sql").read_text())
    password = hashlib.sha256(b"demo").hexdigest()
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("truncate audit, sessions, files, users, orgs cascade")
            cur.execute("insert into orgs (id, name) values ('org_alpha','Alpha Freight'), ('org_beta','Beta Clinic')")
            cur.execute(
                """insert into users (id, org_id, name, role, password_hash) values
                   ('user_alpha_admin','org_alpha','Alice Alpha','admin',%s),
                   ('user_beta_user','org_beta','Bob Beta','user',%s)""",
                [password, password],
            )
            cur.execute(
                """insert into files (id, org_id, name, content_type, bytes) values
                   ('file_alpha_brief','org_alpha','alpha-brief.txt','text/plain',convert_to('Alpha confidential brief','UTF8')),
                   ('file_beta_notes','org_beta','beta-notes.txt','text/plain',convert_to('Beta confidential notes','UTF8'))"""
            )
    yield
