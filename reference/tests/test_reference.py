import base64
import importlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi.testclient import TestClient


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_app(tmp_path: Path):
    os.environ["DOLI_DB_PATH"] = str(tmp_path / "doli.sqlite3")
    os.environ["DOLI_SIGNING_KEY_PATH"] = str(tmp_path / "signing.pem")
    import reference.main as main

    importlib.reload(main)
    return main


def test_activation_historical_query_and_signature(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)

    subject = client.post("/v1/subjects").json()["subject_ref"]
    before = client.get(f"/v1/signature-policy/{subject}").json()
    assert before["policy"] == "HANDWRITTEN_ALLOWED"

    activated = client.post(f"/v1/subjects/{subject}/activate-digital-only").json()
    after = client.get(f"/v1/signature-policy/{subject}").json()
    assert after["policy"] == "DIGITAL_ONLY"

    historical = client.get(
        f"/v1/signature-policy/{subject}", params={"at": before["queried_at"]}
    ).json()
    assert historical["policy"] == "HANDWRITTEN_ALLOWED"

    signature = after.pop("signature")
    public_key = Ed25519PublicKey.from_public_bytes(b64url_decode(signature["public_key"]))
    public_key.verify(b64url_decode(signature["value"]), canonical_json(after))

    events = client.get(f"/v1/subjects/{subject}/events").json()
    assert len(events) == 1
    assert events[0]["transition_id"] == activated["transition_id"]
    assert events[0]["event_hash"] == activated["event_hash"]


def test_downgrade_pending_never_restores_handwriting(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)

    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")
    pending = client.post(f"/v1/subjects/{subject}/request-downgrade")
    assert pending.status_code == 200

    policy = client.get(f"/v1/signature-policy/{subject}").json()
    assert policy["policy"] == "DIGITAL_ONLY"

    cancelled = client.post(f"/v1/subjects/{subject}/cancel-downgrade")
    assert cancelled.status_code == 200
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"


def test_outage_is_indeterminate_not_handwritten_allowed(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)

    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")
    client.post("/v1/admin/simulate-outage")

    result = client.get(f"/v1/signature-policy/{subject}").json()
    assert result["policy"] == "INDETERMINATE"


def test_event_table_rejects_update_and_delete(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)

    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")

    conn = main.db()
    try:
        row = conn.execute(
            "SELECT transition_id FROM policy_events WHERE subject_ref = ?", (subject,)
        ).fetchone()
        for sql in (
            "UPDATE policy_events SET state='HANDWRITTEN_ALLOWED' WHERE transition_id=?",
            "DELETE FROM policy_events WHERE transition_id=?",
        ):
            try:
                conn.execute(sql, (row["transition_id"],))
            except Exception as exc:
                assert "append-only" in str(exc)
            else:
                raise AssertionError("append-only protection failed")
    finally:
        conn.close()
