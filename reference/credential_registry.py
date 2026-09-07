from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Iterable


VALID_STATUSES = {"ACTIVE", "REVOKED"}


@dataclass(frozen=True)
class CredentialRecord:
    credential_ref: str
    subject_ref: str
    assurance_level: str
    status: str
    created_at: datetime
    revoked_at: datetime | None = None
    replaces: str | None = None

    def __post_init__(self) -> None:
        if not self.credential_ref:
            raise ValueError("credential_ref is required")
        if not self.subject_ref:
            raise ValueError("subject_ref is required")
        if not self.assurance_level:
            raise ValueError("assurance_level is required")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"unsupported credential status: {self.status}")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.revoked_at is not None and self.revoked_at.tzinfo is None:
            raise ValueError("revoked_at must be timezone-aware")
        if self.status == "ACTIVE" and self.revoked_at is not None:
            raise ValueError("ACTIVE credential cannot have revoked_at")
        if self.status == "REVOKED" and self.revoked_at is None:
            raise ValueError("REVOKED credential requires revoked_at")


class CredentialRegistry:
    """Synthetic in-memory credential set used by the DOLI reference model.

    Credential state is intentionally independent of effective legal policy.
    Revocation and replacement never imply DIGITAL_ONLY -> HANDWRITTEN_ALLOWED.
    """

    def __init__(self) -> None:
        self._records: dict[str, CredentialRecord] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def add(
        self,
        *,
        credential_ref: str,
        subject_ref: str,
        assurance_level: str = "HIGH",
        created_at: datetime | None = None,
        replaces: str | None = None,
    ) -> CredentialRecord:
        if credential_ref in self._records:
            raise ValueError("credential already exists")
        if replaces is not None:
            previous = self._records.get(replaces)
            if previous is None:
                raise ValueError("replacement target does not exist")
            if previous.subject_ref != subject_ref:
                raise ValueError("replacement target belongs to another subject")
        record = CredentialRecord(
            credential_ref=credential_ref,
            subject_ref=subject_ref,
            assurance_level=assurance_level,
            status="ACTIVE",
            created_at=created_at or self._now(),
            replaces=replaces,
        )
        self._records[credential_ref] = record
        return record

    def get(self, credential_ref: str) -> CredentialRecord:
        try:
            return self._records[credential_ref]
        except KeyError as exc:
            raise KeyError("credential not found") from exc

    def list_for_subject(self, subject_ref: str) -> list[CredentialRecord]:
        return sorted(
            (record for record in self._records.values() if record.subject_ref == subject_ref),
            key=lambda record: (record.created_at, record.credential_ref),
        )

    def active_for_subject(self, subject_ref: str) -> list[CredentialRecord]:
        return [record for record in self.list_for_subject(subject_ref) if record.status == "ACTIVE"]

    def has_sufficient_active_credential(
        self,
        subject_ref: str,
        *,
        accepted_assurance_levels: Iterable[str] = ("HIGH",),
    ) -> bool:
        accepted = set(accepted_assurance_levels)
        return any(
            record.status == "ACTIVE" and record.assurance_level in accepted
            for record in self.list_for_subject(subject_ref)
        )

    def revoke(
        self,
        credential_ref: str,
        *,
        revoked_at: datetime | None = None,
    ) -> CredentialRecord:
        record = self.get(credential_ref)
        if record.status == "REVOKED":
            return record
        updated = replace(
            record,
            status="REVOKED",
            revoked_at=revoked_at or self._now(),
        )
        self._records[credential_ref] = updated
        return updated

    def replace(
        self,
        credential_ref: str,
        *,
        new_credential_ref: str,
        assurance_level: str | None = None,
        at: datetime | None = None,
    ) -> CredentialRecord:
        old = self.get(credential_ref)
        if old.status != "ACTIVE":
            raise ValueError("only an ACTIVE credential can be replaced")
        when = at or self._now()
        self.revoke(credential_ref, revoked_at=when)
        return self.add(
            credential_ref=new_credential_ref,
            subject_ref=old.subject_ref,
            assurance_level=assurance_level or old.assurance_level,
            created_at=when,
            replaces=credential_ref,
        )


def recovery_route(
    registry: CredentialRegistry,
    subject_ref: str,
    *,
    accepted_assurance_levels: Iterable[str] = ("HIGH",),
) -> str:
    """Return the next recovery layer without changing legal policy.

    CREDENTIAL_FIRST means an already-authorized sufficient credential exists.
    ENHANCED_RECOVERY means no sufficient authorized credential remains available.
    """

    if registry.has_sufficient_active_credential(
        subject_ref,
        accepted_assurance_levels=accepted_assurance_levels,
    ):
        return "CREDENTIAL_FIRST"
    return "ENHANCED_RECOVERY"
