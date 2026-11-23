"""Run the reproducible Northstar evaluation set.

Usage (from backend/):
    PYTHONPATH=. python ../scripts/run_evals.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import core  # noqa: E402


def main() -> int:
    cases = json.loads((ROOT / "evals" / "questions.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        conn = core.connect(Path(tmp) / "eval.sqlite")
        core.init_db(conn)
        core.seed(conn)
        passed = 0
        for case in cases:
            expect = case.get("expect", {})
            if case.get("direct") == "create_ticket":
                result = core.create_ticket(conn, case["tenant"], "eval", case.get("args", {}))
                ok = result.get("ok") is False and "error" in result
                print(f"{'PASS' if ok else 'FAIL'} {case['id']}: {result}")
                passed += 1 if ok else 0
                continue
            response = core.answer(conn, case["tenant"], "eval", case["question"])
            checks = []
            if "abstained" in expect:
                checks.append(response["abstained"] is expect["abstained"])
            if "citations_empty" in expect:
                checks.append((len(response["citations"]) == 0) is expect["citations_empty"])
            if "citation_title" in expect:
                checks.append(any(expect["citation_title"].lower() in c["title"].lower() for c in response["citations"]))
            if "answer_contains" in expect:
                checks.append(all(term.lower() in response["answer"].lower() for term in expect["answer_contains"]))
            if "not_contains" in expect:
                checks.append(all(term.lower() not in response["answer"].lower() for term in expect["not_contains"]))
            if "escalate" in expect:
                checks.append(response["escalate"] is expect["escalate"])
            if "tool" in expect:
                checks.append(any(call["name"] == expect["tool"] for call in response["tool_calls"]))
            if "ticket_created" in expect:
                calls = [call for call in response["tool_calls"] if call["name"] == "create_ticket"]
                checks.append(bool(calls) and calls[0]["result"].get("ok") is expect["ticket_created"])
            ok = all(checks)
            passed += 1 if ok else 0
            print(f"{'PASS' if ok else 'FAIL'} {case['id']}: abstained={response['abstained']} citations={len(response['citations'])} mode={response['mode']}")
            if not ok:
                print(f"     answer: {response['answer'][:240]}")
                print(f"     citations: {[c['title'] for c in response['citations']]}")
        total = len(cases)
        print(f"\n{passed}/{total} passed")
        return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
