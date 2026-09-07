from __future__ import annotations

import base64
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException

APP_VERSION = "0.3.0"
SCHEMA_VERSION = "0.3"
JURISDICTION = "demo"
DB_PATH = Path(os.getenv("DOLI_DB_PATH", "reference/doli.sqlite3"))
KEY_PATH = Path(os.getenv("DOLI_SIGNING_KEY_PATH", "reference/dev-signing-key.pem"))

app = FastAPI(title="Digital-Only Legal Identity Reference API", version=APP_VERSION)
simulated_outage = False


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
            state TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            effective_at TEXT NOT NULL,
            previous_event_hash TEXT,
            event_hash TEXT NOT NULL UNIQUE,
            FOREIGN KEY(subject_ref) REFERENCES subjects(subject_ref)
        );

        CREATE TRIGGER IF NOT EXISTS policy_events_no_update
        BEFORE UPDATE ON policy_events
        BEGIN SELECT RAISE(ABORT, 'policy_events is append-only'); END;

        CREATE TRIGGER IF NOT EXISTS policy_events_no_delete
        BEFORE DELETE ON policy_events
        BEGIN SELECT RAISE(ABORT, 'policy_events is append-only'); END;
        """
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
    return key


def public_key_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def sign_payload(payload: dict) -> str:
    signature = load_or_create_signing_key().sign(canonical_json(payload))
    return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


def hash_event(event: dict) -> str:
    import hashlib

    return hashlib.sha256(canonical_json(event)).hexdigest()


def require_subject(conn: sqlite3.Connection, subject_ref: str) -> None:
    if not conn.execute(
        "SELECT 1 FROM subjects WHERE subject_ref = ?", (subject_ref,)
    ).fetchone():
        raise HTTPException(status_code=404, detail="Subject not found")


def events_for(conn: sqlite3.Connection, subject_ref: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM policy_events WHERE subject_ref = ? ORDER BY seq ASC",
        (subject_ref,),
    ).fetchall()


def resolve_policy(events: Iterable[sqlite3.Row], at: datetime) -> str:
    effective = [row for row in events if parse_ts(row["effective_at"]) <= at]
    if not effective:
        return "HANDWRITTEN_ALLOWED"
    raw = effective[-1]["state"]
    return "DIGITAL_ONLY" if raw == "DOWNGRADE_PENDING" else raw


def append_event(
    conn: sqlite3.Connection,
    subject_ref: str,
    state: str,
    effective_at: datetime | None = None,
) -> dict:
    requested_at = now_utc()
    effective_at = effective_at or requested_at
    previous = conn.execute(
        "SELECT event_hash FROM policy_events WHERE subject_ref = ? ORDER BY seq DESC LIMIT 1",
        (subject_ref,),
    ).fetchone()
    previous_hash = previous["event_hash"] if previous else None
    event = {
        "transition_id": str(uuid4()),
        "subject_ref": subject_ref,
        "state": state,
        "requested_at": iso(requested_at),
        "effective_at": iso(effective_at),
        "previous_event_hash": previous_hash,
    }
    event_hash = hash_event(event)
    conn.execute(
        """
        INSERT INTO policy_events (
            transition_id, subject_ref, state, requested_at, effective_at,
            previous_event_hash, event_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["transition_id"],
            subject_ref,
            state,
            event["requested_at"],
            event["effective_at"],
            previous_hash,
            event_hash,
        ),
    )
    conn.commit()
    return {**event, "event_hash": event_hash}


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
        current = resolve_policy(events_for(conn, subject_ref), now_utc())
        if current == "DIGITAL_ONLY":
            raise HTTPException(status_code=409, detail="Subject is already DIGITAL_ONLY")
        event = append_event(conn, subject_ref, "DIGITAL_ONLY")
    return event


@app.post("/v1/subjects/{subject_ref}/request-downgrade")
def request_downgrade(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
        if resolve_policy(rows, now_utc()) != "DIGITAL_ONLY":
            raise HTTPException(status_code=409, detail="Subject is not DIGITAL_ONLY")
        if rows and rows[-1]["state"] == "DOWNGRADE_PENDING":
            raise HTTPException(status_code=409, detail="Downgrade already pending")
        event = append_event(conn, subject_ref, "DOWNGRADE_PENDING")
    return event


@app.post("/v1/subjects/{subject_ref}/cancel-downgrade")
def cancel_downgrade(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
        if not rows or rows[-1]["state"] != "DOWNGRADE_PENDING":
            raise HTTPException(status_code=409, detail="No downgrade pending")
        event = append_event(conn, subject_ref, "DIGITAL_ONLY")
    return event


@app.get("/v1/signature-policy/{subject_ref}")
def get_signature_policy(subject_ref: str, at: str | None = None):
    queried_at = parse_ts(at) if at else now_utc()
    issued_at = now_utc()

    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
        policy = "INDETERMINATE" if simulated_outage else resolve_policy(rows, queried_at)
        if policy not in {"HANDWRITTEN_ALLOWED", "DIGITAL_ONLY", "INDETERMINATE"}:
            policy = "INDETERMINATE"
        event_head = rows[-1]["event_hash"] if rows else None

    assertion = {
        "subject_ref": subject_ref,
        "policy": policy,
        "queried_at": iso(queried_at),
        "assertion_issued_at": iso(issued_at),
        "assertion_id": str(uuid4()),
        "schema_version": SCHEMA_VERSION,
        "jurisdiction": JURISDICTION,
        "event_chain_head": event_head,
        "legal_effect": "none-reference-implementation",
    }
    return {
        **assertion,
        "signature": {
            "alg": "Ed25519",
            "public_key": public_key_b64(load_or_create_signing_key()),
            "value": sign_payload(assertion),
        },
    }


@app.get("/v1/subjects/{subject_ref}/events")
def get_events(subject_ref: str):
    with db() as conn:
        require_subject(conn, subject_ref)
        rows = events_for(conn, subject_ref)
    return [dict(row) for row in rows]


@app.get("/v1/registry/public-key")
def get_registry_public_key():
    return {
        "alg": "Ed25519",
        "public_key": public_key_b64(load_or_create_signing_key()),
        "use": "assertion-verification",
    }


@app.post("/v1/admin/simulate-outage")
def toggle_outage():
    global simulated_outage
    simulated_outage = not simulated_outage
    return {"simulated_outage": simulated_outage}
