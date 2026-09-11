from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from reference.credential_registry import CredentialRecord, CredentialRegistry
from reference.recovery_engine import RecoveryEvidence, evaluate_recovery


router = APIRouter()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def recovery_cooling_off() -> timedelta:
    return timedelta(seconds=int(os.getenv("DOLI_RECOVERY_COOLING_OFF_SECONDS", "300")))


def recovery_min_consistent_evidence_classes() -> int:
    value = int(os.getenv("DOLI_RECOVERY_MIN_CONSISTENT_EVIDENCE_CLASSES", "2"))
    if value < 1:
        raise ValueError("DOLI_RECOVERY_MIN_CONSISTENT_EVIDENCE_CLASSES must be at least 1")
    return value


def db() -> sqlite3.Connection:
    path = Path(os.getenv("DOLI_DB_PATH", "reference/doli.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS credentials (
            credential_ref TEXT PRIMARY KEY,
            subject_ref TEXT NOT NULL,
            assurance_level TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'REVOKED')),
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            replaces TEXT,
            FOREIGN KEY(subject_ref) REFERENCES subjects(subject_ref),
            FOREIGN KEY(replaces) REFERENCES credentials(credential_ref)
        );

        CREATE TABLE IF NOT EXISTS recovery_requests (
            request_id TEXT PRIMARY KEY,
            subject_ref TEXT NOT NULL,
            proposed_credential_ref TEXT NOT NULL,
            assurance_level TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            not_before TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('PENDING', 'CANCELLED', 'COMPLETED')),
            decision_json TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY(subject_ref) REFERENCES subjects(subject_ref)
        );
        """
    )
    return conn


def require_subject(conn: sqlite3.Connection, subject_ref: str) -> None:
    if not conn.execute("SELECT 1 FROM subjects WHERE subject_ref=?", (subject_ref,)).fetchone():
        raise HTTPException(status_code=404, detail="Subject not found")


def current_policy(conn: sqlite3.Connection, subject_ref: str) -> str:
    row = conn.execute(
        """SELECT effective_policy FROM policy_events
           WHERE subject_ref=? AND effective_policy IS NOT NULL
             AND effective_at IS NOT NULL AND effective_at<=?
           ORDER BY effective_at DESC, seq DESC LIMIT 1""",
        (subject_ref, iso(now_utc())),
    ).fetchone()
    return row["effective_policy"] if row else "HANDWRITTEN_ALLOWED"


def registry_from_db(conn: sqlite3.Connection, subject_ref: str) -> CredentialRegistry:
    registry = CredentialRegistry()
    rows = conn.execute(
        "SELECT * FROM credentials WHERE subject_ref=? ORDER BY created_at, credential_ref",
        (subject_ref,),
    ).fetchall()
    # Populate internal records directly so historical revoked credentials preserve timestamps.
    for row in rows:
        registry._records[row["credential_ref"]] = CredentialRecord(
            credential_ref=row["credential_ref"],
            subject_ref=row["subject_ref"],
            assurance_level=row["assurance_level"],
            status=row["status"],
            created_at=parse_ts(row["created_at"]),
            revoked_at=parse_ts(row["revoked_at"]) if row["revoked_at"] else None,
            replaces=row["replaces"],
        )
    return registry


def credential_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def decision_payload(decision) -> dict:
    return {
        "route": decision.route,
        "outcome": decision.outcome,
        "material_contradictions": list(decision.material_contradictions),
        "unresolved_mismatches": list(decision.unresolved_mismatches),
        "consistent_evidence_classes": list(decision.consistent_evidence_classes),
        "required_consistent_evidence_classes": decision.required_consistent_evidence_classes,
    }


class CredentialInput(BaseModel):
    credential_ref: str
    assurance_level: str = "HIGH"


class CredentialReplacementInput(BaseModel):
    new_credential_ref: str
    assurance_level: str | None = None


class RecoveryEvidenceInput(BaseModel):
    evidence_class: str
    result: str
    reference: str | None = None


class RecoveryEvaluationInput(BaseModel):
    evidence: list[RecoveryEvidenceInput] = Field(default_factory=list)


class RecoveryRequestInput(BaseModel):
    proposed_credential_ref: str
    assurance_level: str = "HIGH"
    evidence: list[RecoveryEvidenceInput] = Field(default_factory=list)


def evaluate_input(registry: CredentialRegistry, subject_ref: str, evidence):
    return evaluate_recovery(
        registry,
        subject_ref,
        [RecoveryEvidence(**item.model_dump()) for item in evidence],
        min_consistent_evidence_classes=recovery_min_consistent_evidence_classes(),
    )


@router.post("/v1/subjects/{subject_ref}/credentials", status_code=201)
def add_credential(subject_ref: str, body: CredentialInput):
    with db() as conn:
        require_subject(conn, subject_ref)
        if conn.execute(
            "SELECT 1 FROM credentials WHERE credential_ref=?", (body.credential_ref,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="Credential already exists")
        created_at = iso(now_utc())
        conn.execute(
            """INSERT INTO credentials
               (credential_ref, subject_ref, assurance_level, status, created_at)
               VALUES (?, ?, ?, 'ACTIVE', ?)""",
            (body.credential_ref, subject_ref, body.assurance_level, created_at),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM credentials WHERE credential_ref=?", (body.credential_ref,)
        ).fetchone()
        return credential_dict(row)


@router.get("/v1/subjects/{subject_ref}/credentials")
def list_credentials(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        return [
            credential_dict(row)
            for row in conn.execute(
                "SELECT * FROM credentials WHERE subject_ref=? ORDER BY created_at, credential_ref",
                (subject_ref,),
            ).fetchall()
        ]


@router.post("/v1/subjects/{subject_ref}/credentials/{credential_ref}/revoke")
def revoke_credential(subject_ref: str, credential_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        row = conn.execute(
            "SELECT * FROM credentials WHERE credential_ref=? AND subject_ref=?",
            (credential_ref, subject_ref),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Credential not found")
        if row["status"] == "ACTIVE":
            conn.execute(
                "UPDATE credentials SET status='REVOKED', revoked_at=? WHERE credential_ref=?",
                (iso(now_utc()), credential_ref),
            )
            conn.commit()
        return credential_dict(
            conn.execute(
                "SELECT * FROM credentials WHERE credential_ref=?", (credential_ref,)
            ).fetchone()
        )


@router.post("/v1/subjects/{subject_ref}/credentials/{credential_ref}/replace", status_code=201)
def replace_credential(subject_ref: str, credential_ref: str, body: CredentialReplacementInput):
    with db() as conn:
        require_subject(conn, subject_ref)
        old = conn.execute(
            "SELECT * FROM credentials WHERE credential_ref=? AND subject_ref=?",
            (credential_ref, subject_ref),
        ).fetchone()
        if not old:
            raise HTTPException(status_code=404, detail="Credential not found")
        if old["status"] != "ACTIVE":
            raise HTTPException(status_code=409, detail="Only an ACTIVE credential can be replaced")
        if conn.execute(
            "SELECT 1 FROM credentials WHERE credential_ref=?", (body.new_credential_ref,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="Replacement credential already exists")
        when = iso(now_utc())
        conn.execute(
            "UPDATE credentials SET status='REVOKED', revoked_at=? WHERE credential_ref=?",
            (when, credential_ref),
        )
        conn.execute(
            """INSERT INTO credentials
               (credential_ref, subject_ref, assurance_level, status, created_at, replaces)
               VALUES (?, ?, ?, 'ACTIVE', ?, ?)""",
            (
                body.new_credential_ref,
                subject_ref,
                body.assurance_level or old["assurance_level"],
                when,
                credential_ref,
            ),
        )
        conn.commit()
        return credential_dict(
            conn.execute(
                "SELECT * FROM credentials WHERE credential_ref=?", (body.new_credential_ref,)
            ).fetchone()
        )


@router.post("/v1/subjects/{subject_ref}/recovery/evaluate")
def evaluate_subject_recovery(subject_ref: str, body: RecoveryEvaluationInput):
    with db() as conn:
        require_subject(conn, subject_ref)
        registry = registry_from_db(conn, subject_ref)
        decision = evaluate_input(registry, subject_ref, body.evidence)
        return {
            "subject_ref": subject_ref,
            **decision_payload(decision),
            "may_enter_cooling_off": decision.may_enter_cooling_off,
            "effective_policy_unchanged": True,
        }


@router.post("/v1/subjects/{subject_ref}/recovery/request", status_code=201)
def request_enhanced_recovery(subject_ref: str, body: RecoveryRequestInput):
    with db() as conn:
        require_subject(conn, subject_ref)
        if current_policy(conn, subject_ref) != "DIGITAL_ONLY":
            raise HTTPException(status_code=409, detail="Enhanced recovery requires DIGITAL_ONLY")
        if conn.execute(
            "SELECT 1 FROM recovery_requests WHERE subject_ref=? AND status='PENDING'",
            (subject_ref,),
        ).fetchone():
            raise HTTPException(status_code=409, detail="Recovery request already pending")
        if conn.execute(
            "SELECT 1 FROM credentials WHERE credential_ref=?", (body.proposed_credential_ref,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="Proposed credential already exists")

        registry = registry_from_db(conn, subject_ref)
        decision = evaluate_input(registry, subject_ref, body.evidence)
        payload = decision_payload(decision)
        if not decision.may_enter_cooling_off:
            raise HTTPException(status_code=409, detail=payload)

        requested_at = now_utc()
        request_id = str(uuid4())
        not_before = requested_at + recovery_cooling_off()
        conn.execute(
            """INSERT INTO recovery_requests
               (request_id, subject_ref, proposed_credential_ref, assurance_level,
                requested_at, not_before, status, decision_json)
               VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)""",
            (
                request_id,
                subject_ref,
                body.proposed_credential_ref,
                body.assurance_level,
                iso(requested_at),
                iso(not_before),
                json.dumps(payload, sort_keys=True),
            ),
        )
        conn.commit()
        return {
            "request_id": request_id,
            "subject_ref": subject_ref,
            "proposed_credential_ref": body.proposed_credential_ref,
            "status": "PENDING",
            "requested_at": iso(requested_at),
            "not_before": iso(not_before),
            "decision": payload,
            "effective_policy_unchanged": True,
        }


@router.post("/v1/subjects/{subject_ref}/recovery/{request_id}/cancel")
def cancel_recovery(subject_ref: str, request_id: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        row = conn.execute(
            "SELECT * FROM recovery_requests WHERE request_id=? AND subject_ref=?",
            (request_id, subject_ref),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recovery request not found")
        if row["status"] != "PENDING":
            raise HTTPException(status_code=409, detail="Recovery request is not pending")
        conn.execute(
            "UPDATE recovery_requests SET status='CANCELLED' WHERE request_id=?", (request_id,)
        )
        conn.commit()
        return {"request_id": request_id, "status": "CANCELLED", "effective_policy_unchanged": True}


@router.post("/v1/subjects/{subject_ref}/recovery/{request_id}/complete", status_code=201)
def complete_recovery(subject_ref: str, request_id: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        row = conn.execute(
            "SELECT * FROM recovery_requests WHERE request_id=? AND subject_ref=?",
            (request_id, subject_ref),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recovery request not found")
        if row["status"] != "PENDING":
            raise HTTPException(status_code=409, detail="Recovery request is not pending")
        if now_utc() < parse_ts(row["not_before"]):
            raise HTTPException(status_code=409, detail="Recovery cooling-off period is still active")
        if current_policy(conn, subject_ref) != "DIGITAL_ONLY":
            raise HTTPException(status_code=409, detail="Effective policy changed during recovery")
        if conn.execute(
            "SELECT 1 FROM credentials WHERE credential_ref=?", (row["proposed_credential_ref"],)
        ).fetchone():
            raise HTTPException(status_code=409, detail="Proposed credential already exists")

        completed_at = iso(now_utc())
        conn.execute(
            """INSERT INTO credentials
               (credential_ref, subject_ref, assurance_level, status, created_at)
               VALUES (?, ?, ?, 'ACTIVE', ?)""",
            (
                row["proposed_credential_ref"],
                subject_ref,
                row["assurance_level"],
                completed_at,
            ),
        )
        conn.execute(
            "UPDATE recovery_requests SET status='COMPLETED', completed_at=? WHERE request_id=?",
            (completed_at, request_id),
        )
        conn.commit()
        return {
            "request_id": request_id,
            "status": "COMPLETED",
            "credential_ref": row["proposed_credential_ref"],
            "effective_policy_unchanged": True,
        }


@router.get("/v1/subjects/{subject_ref}/recovery")
def list_recovery_requests(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = conn.execute(
            "SELECT * FROM recovery_requests WHERE subject_ref=? ORDER BY requested_at, request_id",
            (subject_ref,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["decision"] = json.loads(item.pop("decision_json"))
            result.append(item)
        return result
