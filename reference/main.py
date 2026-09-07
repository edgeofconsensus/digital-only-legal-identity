from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

APP_VERSION = "0.4.0"
SCHEMA_VERSION = "0.4"
JURISDICTION = "demo"
REGISTRY_ISSUER = "doli-reference-registry"
ASSERTION_TTL = timedelta(minutes=5)
DOWNGRADE_COOLING_OFF = timedelta(
    seconds=int(os.getenv("DOLI_DOWNGRADE_COOLING_OFF_SECONDS", "300"))
)
DB_PATH = Path(os.getenv("DOLI_DB_PATH", "reference/doli.sqlite3"))
KEY_PATH = Path(os.getenv("DOLI_SIGNING_KEY_PATH", "reference/dev-signing-key.pem"))

app = FastAPI(title="Digital-Only Legal Identity Reference API", version=APP_VERSION)
simulated_outage = False


class SigningEvidenceInput(BaseModel):
    document_hash: str
    credential_ref: str
    signed_at: str | None = None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_ts(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid ISO-8601 timestamp") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            subject_ref TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS policy_events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            transition_id TEXT NOT NULL UNIQUE,
            subject_ref TEXT NOT NULL,
            event_type TEXT NOT NULL,
            effective_policy TEXT,
            requested_at TEXT NOT NULL,
            effective_at TEXT,
            previous_event_hash TEXT,
            event_hash TEXT NOT NULL UNIQUE,
            FOREIGN KEY(subject_ref) REFERENCES subjects(subject_ref),
            CHECK (effective_policy IS NULL OR effective_policy IN ('HANDWRITTEN_ALLOWED', 'DIGITAL_ONLY'))
        );

        CREATE TABLE IF NOT EXISTS signing_evidence (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id TEXT NOT NULL UNIQUE,
            subject_ref TEXT NOT NULL,
            document_hash TEXT NOT NULL,
            credential_ref TEXT NOT NULL,
            signed_at TEXT NOT NULL,
            previous_evidence_hash TEXT,
            evidence_hash TEXT NOT NULL UNIQUE,
            FOREIGN KEY(subject_ref) REFERENCES subjects(subject_ref)
        );

        CREATE TRIGGER IF NOT EXISTS policy_events_no_update
        BEFORE UPDATE ON policy_events
        BEGIN SELECT RAISE(ABORT, 'policy_events is append-only'); END;

        CREATE TRIGGER IF NOT EXISTS policy_events_no_delete
        BEFORE DELETE ON policy_events
        BEGIN SELECT RAISE(ABORT, 'policy_events is append-only'); END;

        CREATE TRIGGER IF NOT EXISTS signing_evidence_no_update
        BEFORE UPDATE ON signing_evidence
        BEGIN SELECT RAISE(ABORT, 'signing_evidence is append-only'); END;

        CREATE TRIGGER IF NOT EXISTS signing_evidence_no_delete
        BEFORE DELETE ON signing_evidence
        BEGIN SELECT RAISE(ABORT, 'signing_evidence is append-only'); END;
        """
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(policy_events)")}
    if "event_type" not in columns:
        conn.close()
        raise RuntimeError(
            "Draft 0.4 uses a new synthetic database schema. Remove the local demo SQLite file and restart."
        )
    return conn


def canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_or_create_signing_key() -> Ed25519PrivateKey:
    if KEY_PATH.exists():
        return serialization.load_pem_private_key(KEY_PATH.read_bytes(), password=None)
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    KEY_PATH.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    try:
        KEY_PATH.chmod(0o600)
    except OSError:
        pass
    return key


def public_key_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def key_id(key: Ed25519PrivateKey) -> str:
    return "ed25519:" + hashlib.sha256(public_key_b64(key).encode("ascii")).hexdigest()[:24]


def sign_payload(payload: dict, key: Ed25519PrivateKey) -> str:
    return base64.urlsafe_b64encode(key.sign(canonical_json(payload))).decode("ascii").rstrip("=")


def hash_record(record: dict) -> str:
    return hashlib.sha256(canonical_json(record)).hexdigest()


def require_subject(conn: sqlite3.Connection, subject_ref: str) -> None:
    if not conn.execute("SELECT 1 FROM subjects WHERE subject_ref = ?", (subject_ref,)).fetchone():
        raise HTTPException(status_code=404, detail="Subject not found")


def events_for(conn: sqlite3.Connection, subject_ref: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM policy_events WHERE subject_ref = ? ORDER BY seq ASC", (subject_ref,)
    ).fetchall()


def evidence_for(conn: sqlite3.Connection, subject_ref: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM signing_evidence WHERE subject_ref = ? ORDER BY seq ASC", (subject_ref,)
    ).fetchall()


def latest_effective_event(events: Iterable[sqlite3.Row], at: datetime) -> sqlite3.Row | None:
    effective = [
        row
        for row in events
        if row["effective_policy"] is not None
        and row["effective_at"] is not None
        and parse_ts(row["effective_at"]) <= at
    ]
    if not effective:
        return None
    return max(effective, key=lambda row: (parse_ts(row["effective_at"]), row["seq"]))


def resolve_policy(events: Iterable[sqlite3.Row], at: datetime) -> str:
    latest = latest_effective_event(events, at)
    return latest["effective_policy"] if latest else "HANDWRITTEN_ALLOWED"


def verify_event_chain(events: Iterable[sqlite3.Row]) -> bool:
    previous_hash = None
    for row in events:
        record = {
            "transition_id": row["transition_id"],
            "subject_ref": row["subject_ref"],
            "event_type": row["event_type"],
            "effective_policy": row["effective_policy"],
            "requested_at": row["requested_at"],
            "effective_at": row["effective_at"],
            "previous_event_hash": row["previous_event_hash"],
        }
        if row["previous_event_hash"] != previous_hash or hash_record(record) != row["event_hash"]:
            return False
        previous_hash = row["event_hash"]
    return True


def verify_evidence_chain(rows: Iterable[sqlite3.Row]) -> bool:
    previous_hash = None
    for row in rows:
        record = {
            "evidence_id": row["evidence_id"],
            "subject_ref": row["subject_ref"],
            "document_hash": row["document_hash"],
            "credential_ref": row["credential_ref"],
            "signed_at": row["signed_at"],
            "previous_evidence_hash": row["previous_evidence_hash"],
        }
        if row["previous_evidence_hash"] != previous_hash or hash_record(record) != row["evidence_hash"]:
            return False
        previous_hash = row["evidence_hash"]
    return True


def append_event(
    conn: sqlite3.Connection,
    subject_ref: str,
    event_type: str,
    *,
    effective_policy: str | None = None,
    requested_at: datetime | None = None,
    effective_at: datetime | None = None,
) -> dict:
    requested_at = requested_at or now_utc()
    previous = conn.execute(
        "SELECT event_hash FROM policy_events WHERE subject_ref = ? ORDER BY seq DESC LIMIT 1",
        (subject_ref,),
    ).fetchone()
    record = {
        "transition_id": str(uuid4()),
        "subject_ref": subject_ref,
        "event_type": event_type,
        "effective_policy": effective_policy,
        "requested_at": iso(requested_at),
        "effective_at": iso(effective_at) if effective_at else None,
        "previous_event_hash": previous["event_hash"] if previous else None,
    }
    event_hash = hash_record(record)
    conn.execute(
        """INSERT INTO policy_events
        (transition_id, subject_ref, event_type, effective_policy, requested_at, effective_at,
         previous_event_hash, event_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record["transition_id"], subject_ref, event_type, effective_policy,
            record["requested_at"], record["effective_at"], record["previous_event_hash"], event_hash,
        ),
    )
    conn.commit()
    return {**record, "event_hash": event_hash}


def latest_downgrade_request(events: list[sqlite3.Row]) -> sqlite3.Row | None:
    for row in reversed(events):
        if row["event_type"] == "DOWNGRADE_REQUESTED":
            return row
        if row["event_type"] in {"DOWNGRADE_CANCELLED", "DOWNGRADE_EFFECTIVE"}:
            return None
    return None


def append_signing_evidence(
    conn: sqlite3.Connection,
    subject_ref: str,
    document_hash: str,
    credential_ref: str,
    signed_at: datetime,
) -> dict:
    normalized_hash = document_hash.lower()
    if len(normalized_hash) != 64 or any(c not in "0123456789abcdef" for c in normalized_hash):
        raise HTTPException(status_code=400, detail="document_hash must be a SHA-256 hex digest")
    previous = conn.execute(
        "SELECT evidence_hash FROM signing_evidence WHERE subject_ref = ? ORDER BY seq DESC LIMIT 1",
        (subject_ref,),
    ).fetchone()
    record = {
        "evidence_id": str(uuid4()),
        "subject_ref": subject_ref,
        "document_hash": normalized_hash,
        "credential_ref": credential_ref,
        "signed_at": iso(signed_at),
        "previous_evidence_hash": previous["evidence_hash"] if previous else None,
    }
    evidence_hash = hash_record(record)
    conn.execute(
        """INSERT INTO signing_evidence
        (evidence_id, subject_ref, document_hash, credential_ref, signed_at,
         previous_evidence_hash, evidence_hash) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            record["evidence_id"], subject_ref, normalized_hash, credential_ref,
            record["signed_at"], record["previous_evidence_hash"], evidence_hash,
        ),
    )
    conn.commit()
    return {**record, "evidence_hash": evidence_hash}


@app.post("/v1/subjects", status_code=201)
def create_subject():
    subject_ref = str(uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO subjects(subject_ref, created_at) VALUES (?, ?)",
            (subject_ref, iso(now_utc())),
        )
        conn.commit()
    return {"subject_ref": subject_ref, "policy": "HANDWRITTEN_ALLOWED"}


@app.post("/v1/subjects/{subject_ref}/activate-digital-only")
def activate_digital_only(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
        if resolve_policy(rows, now_utc()) == "DIGITAL_ONLY":
            raise HTTPException(status_code=409, detail="Subject is already DIGITAL_ONLY")
        now = now_utc()
        return append_event(
            conn, subject_ref, "ACTIVATION_EFFECTIVE",
            effective_policy="DIGITAL_ONLY", effective_at=now,
        )


@app.post("/v1/subjects/{subject_ref}/request-downgrade")
def request_downgrade(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
        if resolve_policy(rows, now_utc()) != "DIGITAL_ONLY":
            raise HTTPException(status_code=409, detail="Subject is not DIGITAL_ONLY")
        if latest_downgrade_request(rows):
            raise HTTPException(status_code=409, detail="Downgrade already pending")
        requested = now_utc()
        return append_event(
            conn, subject_ref, "DOWNGRADE_REQUESTED",
            requested_at=requested, effective_at=requested + DOWNGRADE_COOLING_OFF,
        )


@app.post("/v1/subjects/{subject_ref}/cancel-downgrade")
def cancel_downgrade(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        if not latest_downgrade_request(events_for(conn, subject_ref)):
            raise HTTPException(status_code=409, detail="No downgrade pending")
        return append_event(conn, subject_ref, "DOWNGRADE_CANCELLED")


@app.post("/v1/subjects/{subject_ref}/complete-downgrade")
def complete_downgrade(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
        pending = latest_downgrade_request(rows)
        if not pending:
            raise HTTPException(status_code=409, detail="No downgrade pending")
        not_before = parse_ts(pending["effective_at"])
        now = now_utc()
        if now < not_before:
            raise HTTPException(status_code=409, detail="Downgrade cooling-off period is still active")
        return append_event(
            conn, subject_ref, "DOWNGRADE_EFFECTIVE",
            effective_policy="HANDWRITTEN_ALLOWED", effective_at=now,
        )


@app.post("/v1/subjects/{subject_ref}/enter-recovery")
def enter_recovery(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        if resolve_policy(events_for(conn, subject_ref), now_utc()) != "DIGITAL_ONLY":
            raise HTTPException(status_code=409, detail="Recovery demonstration requires DIGITAL_ONLY")
        return append_event(conn, subject_ref, "RECOVERY_ENTERED")


@app.post("/v1/subjects/{subject_ref}/exit-recovery")
def exit_recovery(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
        if not rows or rows[-1]["event_type"] != "RECOVERY_ENTERED":
            raise HTTPException(status_code=409, detail="Subject is not in recovery")
        return append_event(conn, subject_ref, "RECOVERY_EXITED")


@app.post("/v1/subjects/{subject_ref}/signing-evidence", status_code=201)
def record_signing_evidence(subject_ref: str, body: SigningEvidenceInput):
    signed_at = parse_ts(body.signed_at) if body.signed_at else now_utc()
    with db() as conn:
        require_subject(conn, subject_ref)
        return append_signing_evidence(
            conn, subject_ref, body.document_hash, body.credential_ref, signed_at
        )


@app.get("/v1/subjects/{subject_ref}/signing-evidence")
def get_signing_evidence(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = evidence_for(conn, subject_ref)
        if not verify_evidence_chain(rows):
            raise HTTPException(status_code=503, detail="Signing-evidence integrity failure")
        return [dict(row) for row in rows]


@app.get("/v1/signature-policy/{subject_ref}")
def get_signature_policy(subject_ref: str, at: str | None = None):
    queried_at = parse_ts(at) if at else now_utc()
    issued_at = now_utc()
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
        if simulated_outage or not verify_event_chain(rows):
            policy = "INDETERMINATE"
        else:
            policy = resolve_policy(rows, queried_at)
        event_head = rows[-1]["event_hash"] if rows else None

    signing_key = load_or_create_signing_key()
    assertion = {
        "subject_ref": subject_ref,
        "policy": policy,
        "queried_at": iso(queried_at),
        "assertion_issued_at": iso(issued_at),
        "assertion_expires_at": iso(issued_at + ASSERTION_TTL),
        "assertion_id": str(uuid4()),
        "issuer": REGISTRY_ISSUER,
        "key_id": key_id(signing_key),
        "schema_version": SCHEMA_VERSION,
        "jurisdiction": JURISDICTION,
        "event_chain_head": event_head,
        "legal_effect": "none-reference-implementation",
    }
    return {
        **assertion,
        "signature": {
            "alg": "Ed25519",
            "key_id": key_id(signing_key),
            "public_key": public_key_b64(signing_key),
            "value": sign_payload(assertion, signing_key),
        },
    }


@app.get("/v1/subjects/{subject_ref}/events")
def get_events(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        return [dict(row) for row in events_for(conn, subject_ref)]


@app.get("/v1/registry/public-key")
def get_registry_public_key():
    signing_key = load_or_create_signing_key()
    return {
        "issuer": REGISTRY_ISSUER,
        "alg": "Ed25519",
        "key_id": key_id(signing_key),
        "public_key": public_key_b64(signing_key),
        "use": "assertion-verification",
    }


@app.post("/v1/admin/simulate-outage")
def toggle_outage():
    global simulated_outage
    simulated_outage = not simulated_outage
    return {"simulated_outage": simulated_outage}
