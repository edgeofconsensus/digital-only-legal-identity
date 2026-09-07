import base64
import importlib
import json
import os
from datetime import timedelta
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi.testclient import TestClient


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_app(tmp_path: Path, cooling_seconds: int = 300):
    os.environ["DOLI_DB_PATH"] = str(tmp_path / "doli.sqlite3")
    os.environ["DOLI_SIGNING_KEY_PATH"] = str(tmp_path / "signing.pem")
    os.environ["DOLI_DOWNGRADE_COOLING_OFF_SECONDS"] = str(cooling_seconds)
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
    assert activated["event_type"] == "ACTIVATION_EFFECTIVE"
    assert activated["effective_policy"] == "DIGITAL_ONLY"

    after = client.get(f"/v1/signature-policy/{subject}").json()
    assert after["policy"] == "DIGITAL_ONLY"
    assert after["issuer"] == main.REGISTRY_ISSUER
    assert main.parse_ts(after["assertion_expires_at"]) > main.parse_ts(after["assertion_issued_at"])

    historical = client.get(
        f"/v1/signature-policy/{subject}", params={"at": before["queried_at"]}
    ).json()
    assert historical["policy"] == "HANDWRITTEN_ALLOWED"

    trusted = client.get("/v1/registry/public-key").json()
    signature = after.pop("signature")
    assert signature["key_id"] == trusted["key_id"] == after["key_id"]
    public_key = Ed25519PublicKey.from_public_bytes(b64url_decode(trusted["public_key"]))
    public_key.verify(b64url_decode(signature["value"]), canonical_json(after))

    tampered = {**after, "policy": "HANDWRITTEN_ALLOWED"}
    try:
        public_key.verify(b64url_decode(signature["value"]), canonical_json(tampered))
    except InvalidSignature:
        pass
    else:
        raise AssertionError("tampered assertion unexpectedly verified")


def test_parallel_integration_is_subject_local(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    participant = client.post("/v1/subjects").json()["subject_ref"]
    nonparticipant = client.post("/v1/subjects").json()["subject_ref"]

    client.post(f"/v1/subjects/{participant}/activate-digital-only")

    assert client.get(f"/v1/signature-policy/{participant}").json()["policy"] == "DIGITAL_ONLY"
    assert client.get(f"/v1/signature-policy/{nonparticipant}").json()["policy"] == "HANDWRITTEN_ALLOWED"


def test_workflow_event_never_becomes_effective_policy(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")

    with main.db() as conn:
        main.append_event(
            conn,
            subject,
            "DOWNGRADE_REQUESTED",
            effective_at=main.now_utc() - timedelta(days=1),
        )

    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"
    events = client.get(f"/v1/subjects/{subject}/events").json()
    assert events[-1]["event_type"] == "DOWNGRADE_REQUESTED"
    assert events[-1]["effective_policy"] is None


def test_downgrade_cooling_off_and_cancel_preserve_digital_only(tmp_path):
    main = load_app(tmp_path, cooling_seconds=300)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")

    requested = client.post(f"/v1/subjects/{subject}/request-downgrade")
    assert requested.status_code == 200
    assert requested.json()["event_type"] == "DOWNGRADE_REQUESTED"
    assert requested.json()["effective_policy"] is None
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"

    blocked = client.post(f"/v1/subjects/{subject}/complete-downgrade")
    assert blocked.status_code == 409
    assert "cooling-off" in blocked.json()["detail"]

    cancelled = client.post(f"/v1/subjects/{subject}/cancel-downgrade")
    assert cancelled.status_code == 200
    assert cancelled.json()["event_type"] == "DOWNGRADE_CANCELLED"
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"
    assert client.post(f"/v1/subjects/{subject}/complete-downgrade").status_code == 409


def test_completed_downgrade_changes_only_future_policy(tmp_path):
    main = load_app(tmp_path, cooling_seconds=0)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    activation = client.post(f"/v1/subjects/{subject}/activate-digital-only").json()
    during_digital = main.now_utc()
    client.post(f"/v1/subjects/{subject}/request-downgrade")
    completed = client.post(f"/v1/subjects/{subject}/complete-downgrade")

    assert completed.status_code == 200
    assert completed.json()["event_type"] == "DOWNGRADE_EFFECTIVE"
    assert completed.json()["effective_policy"] == "HANDWRITTEN_ALLOWED"
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "HANDWRITTEN_ALLOWED"

    before_activation = main.parse_ts(activation["effective_at"]) - timedelta(microseconds=1)
    assert client.get(
        f"/v1/signature-policy/{subject}", params={"at": main.iso(before_activation)}
    ).json()["policy"] == "HANDWRITTEN_ALLOWED"
    assert client.get(
        f"/v1/signature-policy/{subject}", params={"at": main.iso(during_digital)}
    ).json()["policy"] == "DIGITAL_ONLY"


def test_recovery_does_not_downgrade_policy(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")

    entered = client.post(f"/v1/subjects/{subject}/enter-recovery")
    assert entered.status_code == 200
    assert entered.json()["effective_policy"] is None
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"

    exited = client.post(f"/v1/subjects/{subject}/exit-recovery")
    assert exited.status_code == 200
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"


def test_outage_is_indeterminate_without_state_change(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")
    count_before = len(client.get(f"/v1/subjects/{subject}/events").json())

    client.post("/v1/admin/simulate-outage")
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "INDETERMINATE"
    assert len(client.get(f"/v1/subjects/{subject}/events").json()) == count_before

    client.post("/v1/admin/simulate-outage")
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"


def test_resolution_uses_effective_timestamp_not_append_order(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    base = main.now_utc()

    with main.db() as conn:
        main.append_event(
            conn,
            subject,
            "ACTIVATION_EFFECTIVE",
            effective_policy="DIGITAL_ONLY",
            effective_at=base + timedelta(days=2),
        )
        main.append_event(
            conn,
            subject,
            "DOWNGRADE_EFFECTIVE",
            effective_policy="HANDWRITTEN_ALLOWED",
            effective_at=base + timedelta(days=1),
        )

    result = client.get(
        f"/v1/signature-policy/{subject}", params={"at": main.iso(base + timedelta(days=3))}
    ).json()
    assert result["policy"] == "DIGITAL_ONLY"


def test_event_chain_tamper_fails_closed(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")

    with main.db() as conn:
        conn.execute("DROP TRIGGER policy_events_no_update")
        conn.execute(
            "UPDATE policy_events SET effective_policy='HANDWRITTEN_ALLOWED' WHERE subject_ref=?",
            (subject,),
        )
        conn.commit()

    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "INDETERMINATE"


def test_event_table_rejects_update_and_delete(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    client.post(f"/v1/subjects/{subject}/activate-digital-only")

    conn = main.db()
    try:
        transition_id = conn.execute(
            "SELECT transition_id FROM policy_events WHERE subject_ref=?", (subject,)
        ).fetchone()["transition_id"]
        for sql in (
            "UPDATE policy_events SET event_type='DOWNGRADE_EFFECTIVE' WHERE transition_id=?",
            "DELETE FROM policy_events WHERE transition_id=?",
        ):
            try:
                conn.execute(sql, (transition_id,))
            except Exception as exc:
                assert "append-only" in str(exc)
            else:
                raise AssertionError("append-only protection failed")
    finally:
        conn.close()


def test_signing_evidence_stores_commitment_not_document_and_is_tamper_evident(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    document = b"synthetic agreement contents"
    digest = __import__("hashlib").sha256(document).hexdigest()

    created = client.post(
        f"/v1/subjects/{subject}/signing-evidence",
        json={"document_hash": digest, "credential_ref": "demo-key:1"},
    )
    assert created.status_code == 201
    assert created.json()["document_hash"] == digest
    assert "document" not in created.json()

    rows = client.get(f"/v1/subjects/{subject}/signing-evidence")
    assert rows.status_code == 200
    assert len(rows.json()) == 1
    assert rows.json()[0]["credential_ref"] == "demo-key:1"

    with main.db() as conn:
        conn.execute("DROP TRIGGER signing_evidence_no_update")
        conn.execute(
            "UPDATE signing_evidence SET credential_ref='attacker' WHERE subject_ref=?", (subject,)
        )
        conn.commit()

    assert client.get(f"/v1/subjects/{subject}/signing-evidence").status_code == 503


def test_signing_evidence_rejects_non_sha256_commitment(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = client.post("/v1/subjects").json()["subject_ref"]
    response = client.post(
        f"/v1/subjects/{subject}/signing-evidence",
        json={"document_hash": "not-a-hash", "credential_ref": "demo-key:1"},
    )
    assert response.status_code == 400
