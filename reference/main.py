from datetime import datetime, timezone
from hashlib import sha256
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Digital-Only Legal Identity Reference API", version="0.1.0")

subjects: Dict[str, List[dict]] = {}
simulated_outage = False


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_policy(events: List[dict], at: datetime) -> str:
    effective = [e for e in events if e["effective_at"] <= at]
    if not effective:
        return "HANDWRITTEN_ALLOWED"
    return max(effective, key=lambda e: e["effective_at"])["state"]


def add_event(subject_id: str, state: str, effective_at: datetime | None = None) -> dict:
    event = {
        "transition_id": str(uuid4()),
        "state": state,
        "requested_at": now_utc(),
        "effective_at": effective_at or now_utc(),
    }
    subjects[subject_id].append(event)
    return event


@app.post("/v1/subjects", status_code=201)
def create_subject():
    subject_id = str(uuid4())
    subjects[subject_id] = []
    return {"subject_ref": subject_id, "policy": "HANDWRITTEN_ALLOWED"}


@app.post("/v1/subjects/{subject_id}/activate-digital-only")
def activate_digital_only(subject_id: str):
    if subject_id not in subjects:
        raise HTTPException(status_code=404, detail="Subject not found")
    event = add_event(subject_id, "DIGITAL_ONLY")
    return {
        "subject_ref": subject_id,
        "state": "DIGITAL_ONLY",
        "effective_at": iso(event["effective_at"]),
        "transition_id": event["transition_id"],
    }


@app.post("/v1/subjects/{subject_id}/request-downgrade")
def request_downgrade(subject_id: str):
    if subject_id not in subjects:
        raise HTTPException(status_code=404, detail="Subject not found")
    current = resolve_policy(subjects[subject_id], now_utc())
    if current != "DIGITAL_ONLY":
        raise HTTPException(status_code=409, detail="Subject is not DIGITAL_ONLY")
    event = add_event(subject_id, "DOWNGRADE_PENDING")
    return {
        "subject_ref": subject_id,
        "state": "DOWNGRADE_PENDING",
        "transition_id": event["transition_id"],
    }


@app.post("/v1/subjects/{subject_id}/cancel-downgrade")
def cancel_downgrade(subject_id: str):
    if subject_id not in subjects:
        raise HTTPException(status_code=404, detail="Subject not found")
    latest = subjects[subject_id][-1] if subjects[subject_id] else None
    if not latest or latest["state"] != "DOWNGRADE_PENDING":
        raise HTTPException(status_code=409, detail="No downgrade pending")
    event = add_event(subject_id, "DIGITAL_ONLY")
    return {
        "subject_ref": subject_id,
        "state": "DIGITAL_ONLY",
        "transition_id": event["transition_id"],
    }


@app.get("/v1/signature-policy/{subject_id}")
def get_signature_policy(subject_id: str, at: str | None = None):
    if subject_id not in subjects:
        raise HTTPException(status_code=404, detail="Subject not found")

    if at:
        try:
            queried_at = datetime.fromisoformat(at.replace("Z", "+00:00"))
            if queried_at.tzinfo is None:
                queried_at = queried_at.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid ISO-8601 timestamp") from exc
    else:
        queried_at = now_utc()

    issued_at = now_utc()

    if simulated_outage:
        policy = "INDETERMINATE"
    else:
        raw_policy = resolve_policy(subjects[subject_id], queried_at)
        # Workflow-only states are never exposed as permission to use handwriting.
        policy = "DIGITAL_ONLY" if raw_policy == "DOWNGRADE_PENDING" else raw_policy
        if policy not in {"HANDWRITTEN_ALLOWED", "DIGITAL_ONLY"}:
            policy = "INDETERMINATE"

    assertion_id = str(uuid4())
    payload = "|".join(
        [subject_id, policy, iso(queried_at), iso(issued_at), assertion_id, "0.2", "demo"]
    )
    integrity_proof = "demo-sha256:" + sha256(payload.encode("utf-8")).hexdigest()

    return {
        "subject_ref": subject_id,
        "policy": policy,
        "queried_at": iso(queried_at),
        "assertion_issued_at": iso(issued_at),
        "assertion_id": assertion_id,
        "schema_version": "0.2",
        "jurisdiction": "demo",
        "integrity_proof": integrity_proof,
        "legal_effect": "none-reference-implementation",
    }


@app.post("/v1/admin/simulate-outage")
def toggle_outage():
    global simulated_outage
    simulated_outage = not simulated_outage
    return {"simulated_outage": simulated_outage}
