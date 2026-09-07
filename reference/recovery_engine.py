from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from reference.credential_registry import CredentialRegistry, recovery_route


EVIDENCE_RESULTS = {
    "CONSISTENT",
    "ABSENT",
    "STALE",
    "BENIGN_MISMATCH",
    "MATERIAL_CONTRADICTION",
}


@dataclass(frozen=True)
class RecoveryEvidence:
    evidence_class: str
    result: str
    reference: str | None = None

    def __post_init__(self) -> None:
        if not self.evidence_class:
            raise ValueError("evidence_class is required")
        if self.result not in EVIDENCE_RESULTS:
            raise ValueError(f"unsupported evidence result: {self.result}")


@dataclass(frozen=True)
class RecoveryDecision:
    route: str
    outcome: str
    material_contradictions: tuple[str, ...] = ()
    unresolved_mismatches: tuple[str, ...] = ()
    consistent_evidence_classes: tuple[str, ...] = ()
    required_consistent_evidence_classes: int = 0

    @property
    def may_enter_cooling_off(self) -> bool:
        return self.outcome == "READY_FOR_COOLING_OFF"


@dataclass(frozen=True)
class RecoveryCoolingOff:
    subject_ref: str
    requested_at: datetime
    not_before: datetime
    status: str = "PENDING"

    def __post_init__(self) -> None:
        if self.requested_at.tzinfo is None or self.not_before.tzinfo is None:
            raise ValueError("cooling-off timestamps must be timezone-aware")
        if self.not_before < self.requested_at:
            raise ValueError("not_before cannot precede requested_at")
        if self.status not in {"PENDING", "CANCELLED", "COMPLETED"}:
            raise ValueError("unsupported cooling-off status")

    def can_complete(self, at: datetime) -> bool:
        return self.status == "PENDING" and at >= self.not_before


def evaluate_recovery(
    registry: CredentialRegistry,
    subject_ref: str,
    evidence: Iterable[RecoveryEvidence] = (),
    *,
    accepted_assurance_levels: Iterable[str] = ("HIGH",),
    min_consistent_evidence_classes: int = 2,
) -> RecoveryDecision:
    if min_consistent_evidence_classes < 1:
        raise ValueError("min_consistent_evidence_classes must be at least 1")

    route = recovery_route(
        registry,
        subject_ref,
        accepted_assurance_levels=accepted_assurance_levels,
    )
    if route == "CREDENTIAL_FIRST":
        return RecoveryDecision(
            route=route,
            outcome="USE_EXISTING_CREDENTIAL",
            required_consistent_evidence_classes=min_consistent_evidence_classes,
        )

    evidence = tuple(evidence)
    contradictions = tuple(
        item.evidence_class
        for item in evidence
        if item.result == "MATERIAL_CONTRADICTION"
    )
    if contradictions:
        return RecoveryDecision(
            route="ENHANCED_RECOVERY",
            outcome="BLOCKED_CONTRADICTION",
            material_contradictions=contradictions,
            required_consistent_evidence_classes=min_consistent_evidence_classes,
        )

    mismatches = tuple(
        item.evidence_class
        for item in evidence
        if item.result == "BENIGN_MISMATCH"
    )
    if mismatches:
        return RecoveryDecision(
            route="ENHANCED_RECOVERY",
            outcome="REQUIRES_RECONCILIATION",
            unresolved_mismatches=mismatches,
            required_consistent_evidence_classes=min_consistent_evidence_classes,
        )

    consistent = tuple(
        sorted({item.evidence_class for item in evidence if item.result == "CONSISTENT"})
    )
    if len(consistent) < min_consistent_evidence_classes:
        return RecoveryDecision(
            route="ENHANCED_RECOVERY",
            outcome="INSUFFICIENT_EVIDENCE",
            consistent_evidence_classes=consistent,
            required_consistent_evidence_classes=min_consistent_evidence_classes,
        )

    return RecoveryDecision(
        route="ENHANCED_RECOVERY",
        outcome="READY_FOR_COOLING_OFF",
        consistent_evidence_classes=consistent,
        required_consistent_evidence_classes=min_consistent_evidence_classes,
    )


def begin_recovery_cooling_off(
    subject_ref: str,
    decision: RecoveryDecision,
    *,
    duration: timedelta,
    requested_at: datetime | None = None,
) -> RecoveryCoolingOff:
    if not decision.may_enter_cooling_off:
        raise ValueError("recovery decision is not eligible for cooling-off")
    if duration.total_seconds() < 0:
        raise ValueError("cooling-off duration cannot be negative")
    requested = requested_at or datetime.now(timezone.utc)
    return RecoveryCoolingOff(
        subject_ref=subject_ref,
        requested_at=requested,
        not_before=requested + duration,
    )
