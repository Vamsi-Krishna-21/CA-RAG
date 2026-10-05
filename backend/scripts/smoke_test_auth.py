"""
End-to-end auth + user-isolation smoke test against a RUNNING backend.

    cd backend
    python scripts/smoke_test_auth.py                 # uses http://localhost:8000
    python scripts/smoke_test_auth.py --with-chat     # also runs a real chat query (needs your LLM up)

Needs: the backend running, MongoDB reachable with the same .env, httpx and PyMuPDF
(both already in requirements.txt). It creates two throwaway users (smoke_*@example.test)
and removes everything it created.

Password-reset *email delivery* is not tested (no inbox). Instead the script plants a
known reset-token hash in the database and exercises the real reset endpoint.
Without --with-chat, a synthetic assistant message is inserted so the feedback checks
can still run.
"""
import argparse
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # noqa: E402  (PyMuPDF)
import httpx  # noqa: E402
from bson import ObjectId  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from app.auth.security_utils import hash_reset_token, utcnow  # noqa: E402
from app.config import settings  # noqa: E402
from datetime import timedelta  # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS  " if cond else "FAIL  ") + name + (f"   [{detail}]" if detail and not cond else ""))


def make_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Smoke test document. The capital of France is Paris. " * 8)
    data = doc.tobytes()
    doc.close()
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--with-chat", action="store_true")
    args = ap.parse_args()

    http = httpx.Client(base_url=args.base, timeout=300)
    db = MongoClient(settings.mongodb_uri)[settings.mongodb_db]
    tag = uuid.uuid4().hex[:8]
    a_email, a_user, a_pw = f"smoke_a_{tag}@example.test", f"smoke_a_{tag}", "SmokePass-A1"
    b_email, b_pw = f"smoke_b_{tag}@example.test", "SmokePass-B1"
    auth = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
    created_users, doc_id = [], None

    try:
        r = http.get("/api/health")
        check("backend reachable", r.status_code == 200, r.text)

        # ---- 1. register ----
        r = http.post("/api/auth/register", json={"name": "Smoke A", "email": a_email, "username": a_user, "password": a_pw})
        check("1. register user A", r.status_code == 200 and "access_token" in r.json(), r.text)
        a = r.json()
        a_id, a_token = a["user"]["id"], a["access_token"]
        created_users.append(a_id)
        check("   register returns username", a["user"].get("username") == a_user)
        r = http.post("/api/auth/register", json={"name": "X", "email": f"weak_{tag}@example.test", "password": "short"})
        check("   weak password rejected (400, string detail)", r.status_code == 400 and isinstance(r.json()["detail"], str), r.text)
        r = http.post("/api/auth/register", json={"name": "X", "email": a_email.upper(), "password": "Another-Pass1"})
        check("   duplicate email (any case) rejected", r.status_code == 400, r.text)
        r = http.post("/api/auth/register", json={"name": "X", "email": f"dup_{tag}@example.test", "username": a_user.upper(), "password": "Another-Pass1"})
        check("   duplicate username rejected", r.status_code == 400, r.text)

        # ---- 2. login ----
        r = http.post("/api/auth/login", json={"identifier": a_email, "password": a_pw})
        check("2. login with email", r.status_code == 200, r.text)
        r = http.post("/api/auth/login", json={"identifier": a_user, "password": a_pw})
        check("   login with username", r.status_code == 200, r.text)
        r = http.post("/api/auth/login", json={"email": a_email, "password": a_pw})
        check("   login with legacy 'email' field (current UI)", r.status_code == 200, r.text)
        r = http.post("/api/auth/login", json={"identifier": a_email, "password": "wrong-password"})
        check("   wrong password -> 400 (not 401)", r.status_code == 400 and isinstance(r.json()["detail"], str), r.text)
        a_token = r.json().get("access_token", a_token) if r.status_code == 200 else a_token

        # ---- 3/5. persistence + current user ----
        r = http.get("/api/auth/me", headers=auth(a_token))
        check("3/5. /me returns the logged-in user", r.status_code == 200 and r.json()["email"] == a_email, r.text)

        # ---- 4. protected routes ----
        check("4. no token -> 401 on /api/documents", http.get("/api/documents").status_code == 401)
        check("   no token -> 401 on /api/auth/me", http.get("/api/auth/me").status_code == 401)
        check("   garbage token -> 401", http.get("/api/documents", headers=auth("garbage")).status_code == 401)

        # ---- 6/7. upload + ownership ----
        r = http.post("/api/documents/upload", headers=auth(a_token), files={"file": ("smoke.pdf", make_pdf(), "application/pdf")})
        check("6. upload document", r.status_code == 200, r.text)
        doc_id = r.json().get("id")
        status = "processing"
        for _ in range(120):
            docs = http.get("/api/documents", headers=auth(a_token)).json()
            status = next((d["status"] for d in docs if d["id"] == doc_id), "missing")
            if status in ("ready", "failed"):
                break
            time.sleep(2)
        check("   document reaches 'ready'", status == "ready", f"status={status}")
        row = db.documents.find_one({"_id": ObjectId(doc_id)})
        check("7. document belongs to user A (DB)", row and row["user_id"] == a_id)

        # ---- 8/9. chat + history + feedback ----
        message_id, chunk_id = None, "c_smoke0001"
        if args.with_chat:
            r = http.post("/api/chat", headers=auth(a_token), json={"document_id": doc_id, "query": "What is the capital of France?", "mode": "carag"})
            check("8. chat query answered", r.status_code == 200 and "message_id" in r.json(), r.text[:200])
            if r.status_code == 200:
                message_id = r.json()["message_id"]
                ev = r.json().get("evidence") or []
                chunk_id = ev[0]["chunk_id"] if ev else None
        else:
            db.messages.insert_one({"user_id": a_id, "document_id": doc_id, "role": "user", "content": {"query": "q"}, "created_at": utcnow()})
            m = db.messages.insert_one({
                "user_id": a_id, "document_id": doc_id, "role": "assistant", "created_at": utcnow(),
                "content": {"answer": "Paris", "confidence": 90, "status": "SUPPORTED", "hallucination_risk": 0.1,
                            "citations": [{"document_name": "smoke.pdf", "page": 1, "section": None, "chunk_id": chunk_id, "snippet": "..."}],
                            "evidence": [{"chunk_id": chunk_id, "similarity": 0.9}]},
            })
            message_id = str(m.inserted_id)
            print("SKIP  8. real chat query (run with --with-chat); synthetic message inserted instead")

        hist = http.get("/api/chat/history", headers=auth(a_token), params={"document_id": doc_id}).json()
        check("9. chat history for A is not empty", isinstance(hist, list) and len(hist) >= 1)
        check("   all history rows belong to A (DB)", all(db.messages.find_one({"_id": ObjectId(h["id"])})["user_id"] == a_id for h in hist))

        if message_id and chunk_id:
            r = http.post("/api/feedback", headers=auth(a_token), json={"message_id": message_id, "rating": "positive", "used_chunks": [chunk_id]})
            check("10. feedback accepted for own message", r.status_code == 200, r.text)
            r = http.post("/api/feedback", headers=auth(a_token), json={"message_id": message_id, "rating": "positive", "used_chunks": ["c_not_in_answer"]})
            check("    feedback with foreign chunk id rejected", r.status_code == 400, r.text)
            r = http.post("/api/feedback", headers=auth(a_token), json={"message_id": "not-an-id", "rating": "positive", "used_chunks": []})
            check("    feedback with malformed message id -> 404 (not 500)", r.status_code == 404, r.text)

        # ---- 11/12. logout ----
        r = http.post("/api/auth/logout", headers=auth(a_token))
        check("11. logout endpoint", r.status_code == 200, r.text)
        check("12. after logout (token discarded) protected API -> 401", http.get("/api/documents").status_code == 401)
        print("NOTE  JWTs are stateless: a token someone copied before logout stays valid until it expires.")

        # ---- 13/14. second user isolation ----
        r = http.post("/api/auth/register", json={"name": "Smoke B", "email": b_email, "password": b_pw})
        check("13. register + login user B", r.status_code == 200, r.text)
        b_token = r.json()["access_token"]
        created_users.append(r.json()["user"]["id"])
        r = http.post("/api/auth/login", json={"identifier": b_email, "password": b_pw})
        check("    B can log in", r.status_code == 200, r.text)
        check("14. B's /me is B", http.get("/api/auth/me", headers=auth(b_token)).json()["email"] == b_email)
        docs_b = http.get("/api/documents", headers=auth(b_token)).json()
        check("    B cannot list A's documents", all(d["id"] != doc_id for d in docs_b))
        hist_b = http.get("/api/chat/history", headers=auth(b_token), params={"document_id": doc_id}).json()
        check("    B cannot read A's chat history", hist_b == [], str(hist_b)[:100])
        r = http.post("/api/chat", headers=auth(b_token), json={"document_id": doc_id, "query": "hi", "mode": "traditional"})
        check("    B cannot chat with A's document (404)", r.status_code == 404, r.text[:100])
        r = http.delete(f"/api/documents/{doc_id}", headers=auth(b_token))
        check("    B cannot delete A's document (404)", r.status_code == 404, r.text[:100])
        if message_id:
            r = http.post("/api/feedback", headers=auth(b_token), json={"message_id": message_id, "rating": "negative", "used_chunks": [chunk_id]})
            check("    B cannot submit feedback on A's message (404)", r.status_code == 404, r.text[:100])
        check("    malformed document id -> 404 (not 500)", http.delete("/api/documents/xyz", headers=auth(b_token)).status_code == 404)

        # ---- forgot / reset password ----
        r_known = http.post("/api/auth/forgot-password", json={"email": a_email})
        r_unknown = http.post("/api/auth/forgot-password", json={"email": f"nobody_{tag}@example.test"})
        check("forgot-password: same response for known and unknown email", r_known.status_code == 200 and r_known.json() == r_unknown.json(), f"{r_known.text} | {r_unknown.text}")
        u = db.users.find_one({"_id": ObjectId(a_id)})
        check("forgot-password: token stored hashed with expiry", bool(u.get("reset_token_hash")) and bool(u.get("reset_token_expiry")))

        raw = "smoke-known-token-" + tag
        db.users.update_one({"_id": ObjectId(a_id)}, {"$set": {"reset_token_hash": hash_reset_token(raw), "reset_token_expiry": utcnow() + timedelta(minutes=10)}})
        old_token = http.post("/api/auth/login", json={"identifier": a_email, "password": a_pw}).json()["access_token"]
        r = http.post(f"/api/auth/reset-password/{raw}", json={"password": "short"})
        check("reset: weak password rejected", r.status_code == 400, r.text)
        r = http.post("/api/auth/reset-password/not-the-token", json={"password": "NewSmoke-Pass1"})
        check("reset: wrong token rejected", r.status_code == 400, r.text)
        time.sleep(1.2)
        r = http.post(f"/api/auth/reset-password/{raw}", json={"password": "NewSmoke-Pass1"})
        check("reset: valid token accepted", r.status_code == 200, r.text)
        r = http.post(f"/api/auth/reset-password/{raw}", json={"password": "Another-New-Pass1"})
        check("reset: token is single-use", r.status_code == 400, r.text)
        check("reset: token issued before the reset is rejected", http.get("/api/auth/me", headers=auth(old_token)).status_code == 401)
        check("reset: old password no longer works", http.post("/api/auth/login", json={"identifier": a_email, "password": a_pw}).status_code == 400)
        r = http.post("/api/auth/login", json={"identifier": a_email, "password": "NewSmoke-Pass1"})
        check("reset: new password works", r.status_code == 200, r.text)
        new_token = r.json().get("access_token")
        expired = "smoke-expired-token-" + tag
        db.users.update_one({"_id": ObjectId(a_id)}, {"$set": {"reset_token_hash": hash_reset_token(expired), "reset_token_expiry": utcnow() - timedelta(minutes=1)}})
        r = http.post(f"/api/auth/reset-password/{expired}", json={"password": "Expired-Pass1"})
        check("reset: expired token rejected", r.status_code == 400, r.text)

        # ---- cleanup + cascade ----
        r = http.delete(f"/api/documents/{doc_id}", headers=auth(new_token))
        check("cleanup: owner can delete own document", r.status_code == 200, r.text)
        check("cleanup: messages + feedback removed with the document (cascade)",
              db.messages.count_documents({"document_id": doc_id}) == 0
              and db.feedback.count_documents({"message_id": message_id}) == 0)
        doc_id = None
    finally:
        for uid in created_users:
            db.users.delete_one({"_id": ObjectId(uid)})
            db.documents.delete_many({"user_id": uid})
            db.messages.delete_many({"user_id": uid})
            db.feedback.delete_many({"user_id": uid})

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
