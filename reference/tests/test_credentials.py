from datetime import datetime, timezone

import pytest

from reference.credential_registry import CredentialRegistry, recovery_route


def test_multiple_credentials_are_independent_and_subject_scoped():
    registry = CredentialRegistry()
    registry.add(credential_ref="phone:1", subject_ref="subject-a")
    registry.add(credential_ref="hardware:1", subject_ref="subject-a")
    registry.add(credential_ref="phone:2", subject_ref="subject-b")

    subject_a = registry.list_for_subject("subject-a")
    subject_b = registry.list_for_subject("subject-b")

    assert [record.credential_ref for record in subject_a] == ["phone:1", "hardware:1"]
    assert [record.credential_ref for record in subject_b] == ["phone:2"]


def test_loss_of_one_credential_keeps_credential_first_route_when_another_survives():
    registry = CredentialRegistry()
    registry.add(credential_ref="phone:1", subject_ref="subject-a")
    registry.add(credential_ref="hardware:1", subject_ref="subject-a")

    registry.revoke("phone:1")

    assert registry.get("phone:1").status == "REVOKED"
    assert registry.get("hardware:1").status == "ACTIVE"
    assert recovery_route(registry, "subject-a") == "CREDENTIAL_FIRST"


def test_enhanced_recovery_only_after_no_sufficient_credential_remains():
    registry = CredentialRegistry()
    registry.add(credential_ref="phone:1", subject_ref="subject-a")
    registry.add(credential_ref="hardware:1", subject_ref="subject-a")

    registry.revoke("phone:1")
    registry.revoke("hardware:1")

    assert registry.active_for_subject("subject-a") == []
    assert recovery_route(registry, "subject-a") == "ENHANCED_RECOVERY"


def test_low_assurance_credential_does_not_bypass_enhanced_recovery_threshold():
    registry = CredentialRegistry()
    registry.add(
        credential_ref="legacy:1",
        subject_ref="subject-a",
        assurance_level="LOW",
    )

    assert recovery_route(registry, "subject-a") == "ENHANCED_RECOVERY"
    assert recovery_route(
        registry,
        "subject-a",
        accepted_assurance_levels=("LOW", "HIGH"),
    ) == "CREDENTIAL_FIRST"


def test_replacement_revokes_old_credential_and_preserves_subject_continuity():
    registry = CredentialRegistry()
    registry.add(credential_ref="phone:1", subject_ref="subject-a")

    replacement = registry.replace(
        "phone:1",
        new_credential_ref="phone:2",
        at=datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc),
    )

    assert registry.get("phone:1").status == "REVOKED"
    assert replacement.status == "ACTIVE"
    assert replacement.subject_ref == "subject-a"
    assert replacement.replaces == "phone:1"
    assert recovery_route(registry, "subject-a") == "CREDENTIAL_FIRST"


def test_cross_subject_replacement_is_rejected():
    registry = CredentialRegistry()
    registry.add(credential_ref="credential:a", subject_ref="subject-a")

    with pytest.raises(ValueError, match="another subject"):
        registry.add(
            credential_ref="credential:b",
            subject_ref="subject-b",
            replaces="credential:a",
        )


def test_duplicate_credential_reference_is_rejected():
    registry = CredentialRegistry()
    registry.add(credential_ref="phone:1", subject_ref="subject-a")

    with pytest.raises(ValueError, match="already exists"):
        registry.add(credential_ref="phone:1", subject_ref="subject-a")


def test_revocation_is_idempotent():
    registry = CredentialRegistry()
    registry.add(credential_ref="phone:1", subject_ref="subject-a")

    first = registry.revoke("phone:1")
    second = registry.revoke("phone:1")

    assert first == second
    assert first.status == "REVOKED"


def test_credential_registry_contains_no_policy_transition_operation():
    registry = CredentialRegistry()
    public_methods = {name for name in dir(registry) if not name.startswith("_")}

    assert "downgrade" not in public_methods
    assert "activate" not in public_methods
    assert "set_policy" not in public_methods
