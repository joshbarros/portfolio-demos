import psycopg
import pytest

from vaultgate import core


def alpha_session():
    return core.session(core.login("user_alpha_admin", "demo")["token"])


def beta_session():
    return core.session(core.login("user_beta_user", "demo")["token"])


def test_login_and_list_scoped():
    sess = alpha_session()
    names = [f["name"] for f in core.list_files(sess)]
    assert names == ["alpha-brief.txt"]


def test_cross_tenant_read_is_empty():
    sess = alpha_session()
    assert core.get_file(sess, "file_beta_notes") is None


def test_cross_tenant_write_blocked_by_rls():
    with core.connect_app() as conn:
        with core.tenant(conn, "org_alpha") as cur:
            with pytest.raises(psycopg.errors.Error):
                cur.execute(
                    "insert into files (id, org_id, name, content_type, bytes) values ('x','org_beta','x','text/plain',convert_to('x','UTF8'))"
                )


def test_direct_sql_is_tenant_scoped():
    with core.connect_app() as conn:
        with core.tenant(conn, "org_alpha") as cur:
            cur.execute("select count(*) as n from files")
            assert cur.fetchone()["n"] == 1
            cur.execute("select count(*) as n from files where org_id = 'org_beta'")
            assert cur.fetchone()["n"] == 0


def test_connection_reuse_does_not_leak_tenant():
    with core.connect_app() as conn:
        with core.tenant(conn, "org_alpha") as cur:
            cur.execute("select id from files")
            ids_a = [r["id"] for r in cur.fetchall()]
        with core.tenant(conn, "org_beta") as cur:
            cur.execute("select id from files")
            ids_b = [r["id"] for r in cur.fetchall()]
    assert ids_a == ["file_alpha_brief"]
    assert ids_b == ["file_beta_notes"]


def test_expired_session_rejected():
    token = core.login("user_alpha_admin", "demo")["token"]
    with core.connect_app() as conn:
        with conn.cursor() as cur:
            cur.execute("update sessions set expires_at = now() - interval '1 minute' where token_hash = %s", [core.sha256(token)])
    with pytest.raises(PermissionError, match="expired"):
        core.session(token)


def test_revoked_session_rejected():
    token = core.login("user_alpha_admin", "demo")["token"]
    core.logout(token)
    with pytest.raises(PermissionError, match="revoked"):
        core.session(token)


def test_signed_url_happy_and_expired():
    sess = alpha_session()
    signed = core.sign_download(sess, "file_alpha_brief")
    assert core.verify_download(sess, signed["file_id"], signed["exp"], signed["sig"])["name"] == "alpha-brief.txt"
    expired = core.sign_download(sess, "file_alpha_brief", ttl_seconds=-1)
    assert core.verify_download(sess, expired["file_id"], expired["exp"], expired["sig"]) is None


def test_signed_url_tampered_and_cross_tenant():
    sess = alpha_session()
    signed = core.sign_download(sess, "file_alpha_brief")
    assert core.verify_download(sess, signed["file_id"], signed["exp"], "bad") is None
    with pytest.raises(PermissionError):
        core.sign_download(sess, "file_beta_notes")


def test_audit_records_denials():
    sess = alpha_session()
    signed = core.sign_download(sess, "file_alpha_brief", ttl_seconds=-1)
    core.verify_download(sess, signed["file_id"], signed["exp"], signed["sig"])
    actions = [row["action"] for row in core.list_audit(sess)]
    assert "download.denied" in actions
    assert "file.sign" in actions
