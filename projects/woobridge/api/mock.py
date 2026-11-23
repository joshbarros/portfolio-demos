"""Fictional catalog API with pagination and controllable failures."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

PRODUCTS = [
    {"external_id": "ext_1001", "name": "Harbor Lamp", "sku": "HL-1001", "price": "49.90", "description": "Warm desk lamp", "stock": 12},
    {"external_id": "ext_1002", "name": "Dock Stool", "sku": "DS-1002", "price": "89.00", "description": "Oak stool", "stock": 5},
    {"external_id": "ext_1003", "name": "Tide Clock", "sku": "TC-1003", "price": "129.00", "description": "Tide clock", "stock": 3},
]

STATE = {"fail": False, "invalid": False, "corrupt_page": 0}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/_control":
            return self._send(200, STATE)
        if parsed.path != "/products":
            return self._send(404, {"error": "not found"})
        if STATE["fail"]:
            return self._send(503, {"error": "temporarily unavailable"})
        query = parse_qs(parsed.query)
        page = int(query.get("page", ["1"])[0])
        per_page = int(query.get("per_page", ["2"])[0])
        start = (page - 1) * per_page
        chunk = PRODUCTS[start : start + per_page]
        if STATE["invalid"] and page == 1:
            chunk = [{"external_id": "", "name": "", "sku": "", "price": "not-a-price"}]
        if STATE["corrupt_page"] == page:
            return self._send(500, {"error": "page corrupted"})
        next_page = page + 1 if start + per_page < len(PRODUCTS) else None
        return self._send(200, {"page": page, "per_page": per_page, "next_page": next_page, "data": chunk})

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/_control":
            for key in ("fail", "invalid", "corrupt_page"):
                if key in payload:
                    STATE[key] = payload[key]
            update = payload.get("update")
            if update:
                for product in PRODUCTS:
                    if product["external_id"] == update.get("external_id"):
                        product.update({k: v for k, v in update.items() if k != "external_id"})
            return self._send(200, {"state": STATE, "products": PRODUCTS})
        return self._send(404, {"error": "not found"})

    def log_message(self, *args) -> None:  # silence
        return


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 4011), Handler).serve_forever()
