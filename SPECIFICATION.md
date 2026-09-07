# Digital-Only Legal Identity — Specification

Status: Draft 0.3

## 1. Objective

Define a jurisdiction-neutral mechanism by which a natural person can formally refuse the future use of a handwritten signature as sufficient evidence of that person's legal intent.

The mechanism is intentionally separate from any particular electronic-signature technology. A jurisdiction may bind the policy to qualified electronic signatures, national electronic identification systems, hardware credentials, or other legally recognized high-assurance mechanisms.

## 2. Effective policy

The externally authoritative policy outcome at a legally relevant timestamp is one of:

- `HANDWRITTEN_ALLOWED`
- `DIGITAL_ONLY`
- `INDETERMINATE`

`HANDWRITTEN_ALLOWED` means the protocol itself does not restrict the ordinary legal treatment of handwriting.

`DIGITAL_ONLY` means that, for covered transactions, handwriting alone is not sufficient evidence of the subject's legal intent.

`INDETERMINATE` is a verification outcome used when an authoritative policy answer cannot safely be established. It MUST NOT be interpreted as `HANDWRITTEN_ALLOWED`.

Workflow states and events such as activation pending, downgrade pending, recovery restricted, cancellation or recovery completion are separate from the externally resolved policy. Pending or recovery workflow conditions MUST NOT silently restore handwritten authority.

## 3. Registry model

A production registry SHOULD minimize exposed data. Conceptually it requires:

- a privacy-preserving subject reference;
- an append-only or tamper-evident policy event history;
- request and effective timestamps;
- transition identifiers;
- jurisdiction and schema version;
- authentication and authorization evidence appropriate to the jurisdiction;
- cryptographic evidence that policy assertions were issued by an authorized registry.

The public verification interface SHOULD expose only information necessary to determine the policy for a specific subject and legal timestamp.

## 4. Activation and downgrade

Activation of `DIGITAL_ONLY` MUST require strong authentication and an explicit expression of intent. A jurisdiction MUST define the legally effective timestamp.

A downgrade reduces protection and MUST NOT be easier than activation. A high-assurance profile SHOULD require fresh high-assurance authentication, explicit confirmation, independent notification and a delay or recovery process where appropriate.

Until a downgrade becomes legally effective, the authoritative policy remains `DIGITAL_ONLY`.

Loss or compromise of a digital credential MUST NOT automatically downgrade the subject to `HANDWRITTEN_ALLOWED`.

## 5. Historical semantics

A transaction is evaluated against the policy effective at the legally relevant timestamp `t_legal`, not merely against the subject's current status.

Conceptually:

```text
policy_at(t_legal) = latest effective policy transition with effective_at <= t_legal
```

If multiple transitions share the same effective timestamp, the implementation MUST use a deterministic tie-break rule.

A later downgrade MUST NOT retroactively validate handwriting created while `DIGITAL_ONLY` was effective. A later activation MUST NOT retroactively alter transactions completed before activation became effective.

## 6. Signed policy assertions

A registry assertion MUST cryptographically bind at least:

- privacy-preserving subject reference;
- resolved policy outcome;
- queried legal timestamp;
- assertion issuance timestamp;
- assertion expiry or freshness bound;
- unique assertion identifier;
- registry issuer;
- signing-key identifier;
- jurisdiction;
- schema version;
- integrity reference to the policy history where applicable;
- cryptographic signature or equivalent integrity proof.

A relying party MUST establish trust in the authoritative registry key or certificate chain independently. An arbitrary public key embedded in an assertion is convenience data only and MUST NOT by itself establish trust.

The reference implementation uses Ed25519 demonstration signatures and a five-minute assertion lifetime. These are prototype choices, not mandatory protocol requirements.

## 7. Verification

Conceptual request:

```http
GET /v1/signature-policy/{privacy-preserving-identity-reference}?at=2026-09-07T17:00:00Z
```

The response is a signed assertion containing one of `HANDWRITTEN_ALLOWED`, `DIGITAL_ONLY` or `INDETERMINATE`.

A verifier SHOULD check:

1. registry/key trust;
2. assertion signature;
3. issuer and key identifier;
4. assertion freshness/expiry;
5. subject and queried timestamp;
6. schema/jurisdiction compatibility;
7. any policy-history integrity reference required by the profile.

## 8. Legal semantics

The central proposed rule is:

> A person may formally refuse recognition of a handwritten signature as sufficient evidence of that person's legal intent for future covered transactions.

An adopting jurisdiction must choose the precise legal consequence. Candidate models include invalidity, a rebuttable or irrebuttable presumption against handwriting-only consent, relying-party liability for failure to check the policy, or mandatory additional digital verification.

These are legal-policy choices and MUST NOT be silently encoded as technical assumptions.

## 9. Security rationale and invariants

Handwriting is reproducible information and has no native lifecycle for revocation, expiration, certificate validation or cryptographically verifiable audit history.

The protocol therefore preserves these core invariants:

1. No outage, recovery or credential compromise silently restores handwritten authority.
2. `INDETERMINATE` never aliases to `HANDWRITTEN_ALLOWED`.
3. Effective timestamps control legal-time evaluation.
4. Downgrades are explicit and auditable.
5. Credential recovery and policy downgrade are separate operations.
6. Policy history is append-only or tamper-evident.
7. Historical transitions remain verifiable after later changes.

The current reference implementation uses a per-subject SHA-256 hash chain plus SQLite append-only triggers. This protects the demonstration against ordinary update/delete operations and detects many history modifications, but it is not a substitute for production-grade externally anchored audit integrity or privileged-administrator controls.

## 10. Privacy principle

A verifier generally needs to know whether a particular legal identity was subject to `DIGITAL_ONLY` at a specified time. It does not need unrestricted access to the person's other registry data.

Implementations SHOULD therefore use data minimization, purpose limitation, privacy-preserving identifiers, access control and anti-enumeration measures.

## 11. Failure model

The protocol must address registry unavailability, compromised credentials, delayed revocation information, coercion, identity mismatch, assertion replay, malicious or negligent relying parties, unauthorized enumeration, rollback or alteration of policy history, and registry-authority compromise.

If an implementation cannot safely establish the policy, it MUST fail to `INDETERMINATE` or an equivalent non-permissive outcome rather than infer handwritten authority.

## 12. Reference implementation profile 0.3

The current prototype uses synthetic identities only and implements:

- persistent SQLite event storage;
- append-only update/delete protection;
- per-subject hash chaining and chain verification;
- current and historical policy resolution by `effective_at`;
- `DOWNGRADE_PENDING` workflow behavior that leaves effective policy at `DIGITAL_ONLY`;
- Ed25519-signed assertions with issuer, key identifier and five-minute expiry;
- a registry public-key endpoint;
- fail-closed `INDETERMINATE` behavior for simulated outage or detected chain corruption;
- automated tests and CI.

The prototype does not implement real citizen identity proofing, production PKI/HSM key management, authorization for mutation/admin endpoints, complete activation/recovery workflows, production privacy controls, external audit anchoring or jurisdiction-specific legal effect.

## 13. Non-goals

This project does not create or store real citizen identities, issue legally valid electronic signatures, replace national PKI/eID infrastructure, claim that the reference implementation creates legal effect, or prescribe one country's constitutional or evidentiary rules to another jurisdiction.

## 14. Next specification work

The next revision should define the full workflow-event model for delayed activation, completed downgrade and recovery, production trust/key rotation, authorization and anti-enumeration requirements, external audit anchoring, and a jurisdiction profile suitable for a real pilot.
