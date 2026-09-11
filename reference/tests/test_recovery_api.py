import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient


def load_app(
    tmp_path: Path,
    recovery_cooling_seconds: int = 0,
    min_consistent_evidence_classes: int = 2,
):
    os.environ["DOLI_DB_PATH"] = str(tmp_path / "doli.sqlite3")
    os.environ["DOLI_SIGNING_KEY_PATH"] = str(tmp_path / "signing.pem")
    os.environ["DOLI_RECOVERY_COOLING_OFF_SECONDS"] = str(recovery_cooling_seconds)
    os.environ["DOLI_RECOVERY_MIN_CONSISTENT_EVIDENCE_CLASSES"] = str(
        min_consistent_evidence_classes
    )
    import reference.main as main

    importlib.reload(main)
    return main


def create_digital_only_subject(client: TestClient) -> str:
    subject = client.post("/v1/subjects").json()["subject_ref"]
    assert client.post(f"/v1/subjects/{subject}/activate-digital-only").status_code == 200
    return subject


def test_persisted_credentials_drive_credential_first_then_enhanced_recovery(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = create_digital_only_subject(client)

    for credential_ref in ("phone:1", "hardware:1"):
        response = client.post(
            f"/v1/subjects/{subject}/credentials",
            json={"credential_ref": credential_ref, "assurance_level": "HIGH"},
        )
        assert response.status_code == 201

    client.post(f"/v1/subjects/{subject}/credentials/phone:1/revoke")
    credential_first = client.post(
        f"/v1/subjects/{subject}/recovery/evaluate",
        json={"evidence": []},
    ).json()
    assert credential_first["route"] == "CREDENTIAL_FIRST"
    assert credential_first["outcome"] == "USE_EXISTING_CREDENTIAL"

    client.post(f"/v1/subjects/{subject}/credentials/hardware:1/revoke")
    enhanced = client.post(
        f"/v1/subjects/{subject}/recovery/evaluate",
        json={
            "evidence": [
                {"evidence_class": "continuity", "result": "CONSISTENT"},
                {"evidence_class": "authoritative_identity", "result": "CONSISTENT"},
            ]
        },
    ).json()
    assert enhanced["route"] == "ENHANCED_RECOVERY"
    assert enhanced["outcome"] == "READY_FOR_COOLING_OFF"
    assert enhanced["required_consistent_evidence_classes"] == 2
    assert enhanced["may_enter_cooling_off"] is True
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"


def test_reference_assurance_threshold_is_configurable(tmp_path):
    main = load_app(tmp_path, min_consistent_evidence_classes=1)
    client = TestClient(main.app)
    subject = create_digital_only_subject(client)

    evaluated = client.post(
        f"/v1/subjects/{subject}/recovery/evaluate",
        json={"evidence": [{"evidence_class": "continuity", "result": "CONSISTENT"}]},
    ).json()

    assert evaluated["outcome"] == "READY_FOR_COOLING_OFF"
    assert evaluated["required_consistent_evidence_classes"] == 1


def test_material_contradiction_blocks_recovery_without_policy_change(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = create_digital_only_subject(client)

    response = client.post(
        f"/v1/subjects/{subject}/recovery/request",
        json={
            "proposed_credential_ref": "replacement:1",
            "evidence": [
                {"evidence_class": "authoritative_identity", "result": "MATERIAL_CONTRADICTION"}
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["outcome"] == "BLOCKED_CONTRADICTION"
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"
    assert client.get(f"/v1/subjects/{subject}/recovery").json() == []


def test_benign_mismatch_requires_reconciliation_before_cooling_off(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = create_digital_only_subject(client)

    evaluated = client.post(
        f"/v1/subjects/{subject}/recovery/evaluate",
        json={
            "evidence": [
                {"evidence_class": "historical_record", "result": "BENIGN_MISMATCH"},
                {"evidence_class": "live_interview", "result": "CONSISTENT"},
            ]
        },
    ).json()

    assert evaluated["outcome"] == "REQUIRES_RECONCILIATION"
    assert evaluated["may_enter_cooling_off"] is False
    assert evaluated["unresolved_mismatches"] == ["historical_record"]
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"


def test_recovery_cooling_off_completion_creates_credential_not_policy_transition(tmp_path):
    main = load_app(tmp_path, recovery_cooling_seconds=0)
    client = TestClient(main.app)
    subject = create_digital_only_subject(client)
    events_before = len(client.get(f"/v1/subjects/{subject}/events").json())

    requested = client.post(
        f"/v1/subjects/{subject}/recovery/request",
        json={
            "proposed_credential_ref": "replacement:1",
            "assurance_level": "HIGH",
            "evidence": [
                {"evidence_class": "live_interview", "result": "CONSISTENT"},
                {"evidence_class": "continuity_history", "result": "CONSISTENT"},
            ],
        },
    )
    assert requested.status_code == 201
    request_id = requested.json()["request_id"]
    assert requested.json()["status"] == "PENDING"
    assert requested.json()["effective_policy_unchanged"] is True

    completed = client.post(f"/v1/subjects/{subject}/recovery/{request_id}/complete")
    assert completed.status_code == 201
    assert completed.json()["credential_ref"] == "replacement:1"
    assert completed.json()["effective_policy_unchanged"] is True

    credentials = client.get(f"/v1/subjects/{subject}/credentials").json()
    assert [(item["credential_ref"], item["status"]) for item in credentials] == [
        ("replacement:1", "ACTIVE")
    ]
    assert len(client.get(f"/v1/subjects/{subject}/events").json()) == events_before
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"


def test_active_sufficient_credential_blocks_enhanced_recovery_request(tmp_path):
    main = load_app(tmp_path)
    client = TestClient(main.app)
    subject = create_digital_only_subject(client)
    client.post(
        f"/v1/subjects/{subject}/credentials",
        json={"credential_ref": "hardware:1", "assurance_level": "HIGH"},
    )

    response = client.post(
        f"/v1/subjects/{subject}/recovery/request",
        json={
            "proposed_credential_ref": "replacement:1",
            "evidence": [{"evidence_class": "live_interview", "result": "CONSISTENT"}],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["outcome"] == "USE_EXISTING_CREDENTIAL"
    assert client.get(f"/v1/signature-policy/{subject}").json()["policy"] == "DIGITAL_ONLY"
