from datetime import datetime, timedelta, timezone

import pytest

from reference.credential_registry import CredentialRegistry
from reference.recovery_engine import (
    RecoveryEvidence,
    begin_recovery_cooling_off,
    evaluate_recovery,
)


def test_existing_high_assurance_credential_short_circuits_enhanced_recovery():
    registry = CredentialRegistry()
    registry.add(credential_ref="hardware:1", subject_ref="subject-a")

    decision = evaluate_recovery(
        registry,
        "subject-a",
        [RecoveryEvidence("identity-history", "MATERIAL_CONTRADICTION")],
    )

    assert decision.route == "CREDENTIAL_FIRST"
    assert decision.outcome == "USE_EXISTING_CREDENTIAL"
    assert decision.required_consistent_evidence_classes == 2
    assert not decision.may_enter_cooling_off


def test_material_contradiction_blocks_automatic_recovery():
    registry = CredentialRegistry()
    evidence = [
        RecoveryEvidence("policy-history", "CONSISTENT"),
        RecoveryEvidence("credential-history", "MATERIAL_CONTRADICTION"),
    ]

    decision = evaluate_recovery(registry, "subject-a", evidence)

    assert decision.outcome == "BLOCKED_CONTRADICTION"
    assert decision.material_contradictions == ("credential-history",)
    assert not decision.may_enter_cooling_off


def test_benign_mismatch_requires_reconciliation_before_cooling_off():
    registry = CredentialRegistry()
    evidence = [
        RecoveryEvidence("policy-history", "CONSISTENT"),
        RecoveryEvidence("identity-record", "BENIGN_MISMATCH"),
    ]

    decision = evaluate_recovery(registry, "subject-a", evidence)

    assert decision.outcome == "REQUIRES_RECONCILIATION"
    assert decision.unresolved_mismatches == ("identity-record",)
    assert not decision.may_enter_cooling_off


def test_absent_or_stale_evidence_does_not_become_positive_identity_proof():
    registry = CredentialRegistry()
    evidence = [
        RecoveryEvidence("old-device", "STALE"),
        RecoveryEvidence("signing-evidence", "ABSENT"),
    ]

    decision = evaluate_recovery(registry, "subject-a", evidence)

    assert decision.outcome == "INSUFFICIENT_EVIDENCE"
    assert not decision.may_enter_cooling_off


def test_default_reference_profile_requires_two_independent_consistent_classes():
    registry = CredentialRegistry()
    one_class = [RecoveryEvidence("authoritative-identity", "CONSISTENT")]

    decision = evaluate_recovery(registry, "subject-a", one_class)

    assert decision.outcome == "INSUFFICIENT_EVIDENCE"
    assert decision.consistent_evidence_classes == ("authoritative-identity",)
    assert decision.required_consistent_evidence_classes == 2
    assert not decision.may_enter_cooling_off


def test_consistent_enhanced_evidence_can_enter_recovery_cooling_off():
    registry = CredentialRegistry()
    evidence = [
        RecoveryEvidence("authoritative-identity", "CONSISTENT"),
        RecoveryEvidence("credential-history", "CONSISTENT"),
        RecoveryEvidence("signing-continuity", "STALE"),
    ]

    decision = evaluate_recovery(registry, "subject-a", evidence)

    assert decision.outcome == "READY_FOR_COOLING_OFF"
    assert decision.may_enter_cooling_off


def test_assurance_profile_can_propose_a_different_consistent_evidence_threshold():
    registry = CredentialRegistry()
    evidence = [RecoveryEvidence("authoritative-identity", "CONSISTENT")]

    decision = evaluate_recovery(
        registry,
        "subject-a",
        evidence,
        min_consistent_evidence_classes=1,
    )

    assert decision.outcome == "READY_FOR_COOLING_OFF"
    assert decision.required_consistent_evidence_classes == 1


def test_duplicate_consistent_evidence_class_does_not_count_twice():
    registry = CredentialRegistry()
    evidence = [
        RecoveryEvidence("authoritative-identity", "CONSISTENT", "source-a"),
        RecoveryEvidence("authoritative-identity", "CONSISTENT", "source-b"),
    ]

    decision = evaluate_recovery(registry, "subject-a", evidence)

    assert decision.outcome == "INSUFFICIENT_EVIDENCE"
    assert decision.consistent_evidence_classes == ("authoritative-identity",)


def test_cooling_off_has_explicit_not_before_and_no_policy_field():
    registry = CredentialRegistry()
    decision = evaluate_recovery(
        registry,
        "subject-a",
        [
            RecoveryEvidence("authoritative-identity", "CONSISTENT"),
            RecoveryEvidence("continuity-history", "CONSISTENT"),
        ],
    )
    requested = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)

    cooling = begin_recovery_cooling_off(
        "subject-a",
        decision,
        duration=timedelta(minutes=10),
        requested_at=requested,
    )

    assert cooling.status == "PENDING"
    assert cooling.not_before == requested + timedelta(minutes=10)
    assert not cooling.can_complete(requested + timedelta(minutes=9, seconds=59))
    assert cooling.can_complete(requested + timedelta(minutes=10))
    assert not hasattr(cooling, "effective_policy")
    assert not hasattr(cooling, "policy")


def test_blocked_decision_cannot_start_cooling_off():
    registry = CredentialRegistry()
    decision = evaluate_recovery(
        registry,
        "subject-a",
        [RecoveryEvidence("identity-record", "MATERIAL_CONTRADICTION")],
    )

    with pytest.raises(ValueError, match="not eligible"):
        begin_recovery_cooling_off(
            "subject-a",
            decision,
            duration=timedelta(minutes=10),
        )


def test_low_assurance_credential_does_not_prevent_enhanced_recovery():
    registry = CredentialRegistry()
    registry.add(
        credential_ref="legacy:1",
        subject_ref="subject-a",
        assurance_level="LOW",
    )

    decision = evaluate_recovery(
        registry,
        "subject-a",
        [
            RecoveryEvidence("authoritative-identity", "CONSISTENT"),
            RecoveryEvidence("continuity-history", "CONSISTENT"),
        ],
    )

    assert decision.route == "ENHANCED_RECOVERY"
    assert decision.outcome == "READY_FOR_COOLING_OFF"
