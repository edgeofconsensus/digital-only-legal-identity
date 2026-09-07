# Digital-Only Legal Identity — Threat Model

Status: Draft 0.2 companion

## 1. Security objective

The protocol must preserve a person's declared signature policy against forgery, downgrade, rollback, replay, impersonation, coercion, registry compromise and verifier negligence.

A critical invariant is that failure of infrastructure MUST NOT silently restore handwritten signatures to full legal authority for a person whose effective policy is `DIGITAL_ONLY`.

## 2. Protected assets

The system protects:

- the person's current signature-policy state;
- the complete policy-transition history;
- the effective timestamp of each transition;
- the binding between a legal identity and a privacy-preserving policy reference;
- the authenticity and freshness of registry assertions;
- the integrity of audit evidence;
- the confidentiality of identity data beyond what a verifier needs to know.

## 3. Actors

### Subject
The natural person whose legal-signature policy is registered.

### Registry authority
The public or legally authorized authority responsible for policy registration and authoritative assertions.

### Relying party
A bank, notary, court, employer, registrar, insurer, public authority or other entity deciding whether to rely on a signature.

### Credential provider
An existing high-assurance electronic-signature or electronic-identification system used to authenticate the subject.

### Adversary
Any actor attempting to create, modify, suppress, replay or falsely attribute legal intent.

## 4. Threats and required controls

### T1 — Handwritten-signature forgery

**Threat:** An attacker reproduces or pastes the subject's handwritten signature onto a document.

**Control:** For covered transactions, a verifier MUST check the authoritative policy before relying on handwriting. If the effective policy is `DIGITAL_ONLY`, handwriting alone MUST NOT establish legal intent.

### T2 — Credential theft

**Threat:** An attacker obtains control of a digital signing credential.

**Control:** Credential compromise is handled by the underlying credential lifecycle: authentication controls, revocation, suspension where supported, re-issuance and audit. The policy registry MUST NOT treat credential compromise as a reason to reactivate handwritten authority.

### T3 — Unauthorized policy activation

**Threat:** An attacker activates `DIGITAL_ONLY` for another person.

**Control:** Activation MUST require strong authentication plus an explicit, transaction-specific confirmation of the policy change. The registry SHOULD notify the subject over at least one independent notification channel.

### T4 — Unauthorized downgrade

**Threat:** An attacker changes a subject from `DIGITAL_ONLY` to a less restrictive state.

**Control:** Downgrade MUST be treated as higher risk than activation. It MUST require strong authentication and SHOULD require stronger recovery procedures, delay, multi-channel notification or additional verification defined by jurisdictional policy.

### T5 — Registry rollback

**Threat:** A compromised administrator or system restores an older registry snapshot in which the subject was not yet `DIGITAL_ONLY`.

**Control:** Policy history MUST be append-only or cryptographically tamper-evident. Assertions MUST identify the policy version and effective timestamp. Independent audit evidence SHOULD make rollback detectable.

### T6 — Replay of stale assertion

**Threat:** A verifier or attacker reuses an old `HANDWRITTEN_ALLOWED` assertion after the subject activates `DIGITAL_ONLY`.

**Control:** Assertions MUST carry issuance time, queried legal time, expiration or maximum-validity semantics, unique identifiers and integrity protection. High-risk transactions SHOULD require online freshness.

### T7 — Registry outage

**Threat:** The verifier cannot query the registry.

**Control:** Fail closed for handwritten authorization in covered high-risk contexts. Outage MUST NOT imply `HANDWRITTEN_ALLOWED`. A jurisdiction may define delayed processing or another high-assurance digital route.

### T8 — Enumeration and privacy leakage

**Threat:** An attacker scans identifiers to discover citizens or their policy choices.

**Control:** The public interface MUST NOT expose a population registry. Implementations SHOULD use authenticated relying parties, privacy-preserving references, rate limits, purpose binding and minimal responses.

### T9 — Identity mismatch

**Threat:** A policy assertion is checked for the wrong person.

**Control:** The relying party MUST establish an authoritative identity binding before policy verification. Human-readable names alone MUST NOT be treated as unique identifiers.

### T10 — Coercion

**Threat:** A person is forced to activate, deactivate or digitally authorize a transaction.

**Control:** Coercion cannot be solved purely cryptographically. The protocol SHOULD support jurisdictional safeguards such as delayed effect for downgrades, independent notifications, recovery channels and transaction-specific review for high-risk acts.

### T11 — Malicious or negligent relying party

**Threat:** An institution skips the policy check and accepts handwriting despite an active `DIGITAL_ONLY` state.

**Control:** The legal layer SHOULD assign evidentiary consequences or liability to the relying party. The technical system SHOULD produce verifiable audit evidence showing whether and when a policy check occurred.

### T12 — Malicious registry authority

**Threat:** An insider alters policy state or history.

**Control:** Administrative changes MUST be authenticated, logged and independently auditable. Production systems SHOULD use separation of duties and tamper-evident logs. High-assurance deployments MAY use externally anchored transparency proofs.

## 5. Trust assumptions

The reference protocol assumes:

1. an existing authoritative legal-identity system;
2. at least one legally recognized high-assurance digital authentication or signature mechanism;
3. a registry authority legally empowered to publish signature-policy assertions;
4. verifiers can authenticate registry assertions;
5. courts or legislation define the legal consequence of ignoring the policy.

The project does not assume that any single credential, registry or government system is infallible.

## 6. Security invariants

The following invariants are normative design goals:

- **I1:** No infrastructure failure silently converts `DIGITAL_ONLY` into `HANDWRITTEN_ALLOWED`.
- **I2:** Policy history is evaluated at the legally relevant time, not only at query time.
- **I3:** A downgrade cannot be easier to perform than an activation.
- **I4:** A stale assertion cannot be indistinguishable from a fresh authoritative assertion.
- **I5:** A verifier learns no more identity information than necessary for the transaction.
- **I6:** Registry operators cannot alter historical policy transitions without leaving detectable evidence.
- **I7:** Compromise of one digital credential does not make handwritten signatures valid again.

## 7. Out of scope for Draft 0.2

This threat model does not yet prescribe:

- a specific PKI algorithm;
- a national identity-number format;
- a particular KEP/QES/eID implementation;
- a blockchain or distributed ledger;
- a universal coercion-detection mechanism;
- jurisdiction-specific liability thresholds.

Those choices belong in implementation profiles and national law, not in the jurisdiction-neutral core protocol.
