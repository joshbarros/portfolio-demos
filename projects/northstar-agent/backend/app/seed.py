"""Reproducible seed CLI for the fictional demo knowledge base."""
from .core import connect, init_db, seed


def main() -> None:
    conn = connect()
    init_db(conn)
    seed(conn)
    tenants = conn.execute("SELECT id, name FROM tenants ORDER BY name").fetchall()
    print("Seeded tenants:")
    for tenant in tenants:
        docs = conn.execute("SELECT COUNT(*) AS n FROM documents WHERE tenant_id = ?", (tenant["id"],)).fetchone()["n"]
        chunks = conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE tenant_id = ?", (tenant["id"],)).fetchone()["n"]
        print(f"  - {tenant['id']}: {tenant['name']} ({docs} documents, {chunks} chunks)")


if __name__ == "__main__":
    main()
