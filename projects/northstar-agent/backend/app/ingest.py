"""Administrative ingestion CLI (reproducible, tenant-scoped).

Usage:
    python -m app.ingest --tenant demo-electric --title "Refund policy" \
        --source policies/refund.md --content "..."

    python -m app.ingest --tenant demo-electric --file docs.json

`docs.json` is a JSON array of objects with title, source, updated_at and content.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .core import add_chunk, chunk_text, connect, init_db, list_tenants, utcnow


def ingest_document(conn, tenant_id: str, doc: dict[str, Any]) -> tuple[str, int]:
    doc_id = doc.get("id") or f"ingest-{utcnow()}-{doc['title'][:16].replace(' ', '-').lower()}"
    conn.execute(
        "INSERT INTO documents (id, tenant_id, title, source, updated_at, content) VALUES (?, ?, ?, ?, ?, ?)",
        (
            doc_id,
            tenant_id,
            doc["title"],
            doc.get("source", "admin/ingest.md"),
            doc.get("updated_at", utcnow()[:10]),
            doc["content"],
        ),
    )
    chunks = chunk_text(doc["content"])
    for i, piece in enumerate(chunks):
        add_chunk(conn, f"{doc_id}-{i}", tenant_id, doc_id, doc["title"], piece)
    return doc_id, len(chunks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest documents into one tenant's knowledge base.")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--file", help="JSON array of documents")
    parser.add_argument("--title")
    parser.add_argument("--source", default="admin/ingest.md")
    parser.add_argument("--content")
    args = parser.parse_args(argv)

    conn = connect()
    init_db(conn)
    tenants = {row["id"] for row in list_tenants(conn)}
    if args.tenant not in tenants:
        print(f"Unknown tenant '{args.tenant}'. Known: {', '.join(sorted(tenants))}", file=sys.stderr)
        return 1

    if args.file:
        documents = json.loads(open(args.file, encoding="utf-8").read())
        if not isinstance(documents, list):
            print("--file must contain a JSON array of documents", file=sys.stderr)
            return 1
    elif args.title and args.content:
        documents = [{"title": args.title, "source": args.source, "content": args.content}]
    else:
        parser.error("provide --file, or both --title and --content")

    for doc in documents:
        doc_id, chunks = ingest_document(conn, args.tenant, doc)
        print(f"ingested {doc_id}: {chunks} chunk(s)")
    conn.commit()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
