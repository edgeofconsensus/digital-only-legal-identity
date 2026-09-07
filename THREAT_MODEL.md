# Digital-Only Legal Identity — Threat Model

Status: Draft 0.4 companion

## 1. Security objective

The protocol must preserve a person's declared signature policy against forgery, downgrade, rollback, replay, impersonation, coercion, registry compromise, verifier negligence and misuse of recovery or privileged state-change paths.

A critical invariant is that failure of infrastructure MUST NOT silently restore handwritten signatures to full legal authority for a person whose effective policy is `DIGITAL_ONLY`.

## 2. Protected assets

The system protects:

- the subject's effective legal policy;
- the policy-transition and workflow-event history;
- the effective timestamp of each legal transition;
- the binding between legal identity and privacy-preserving policy reference;
- the authenticity and freshness of registry assertions;
- the integrity of minimal signing-evidence history;
- the distinction between workflow events and effective policy;
- the confidentiality of identity and signing-history data beyond what a verifier needs.

## 3. Actors

### Subject
The natural person whose legal-signature policy is registered.

### Registry authority
The public or legally authorized authority responsible for policy registration and authoritative assertions.

### Relying party
An entity deciding whether to rely on a signature or authorization.

### Credential provider
A high-assurance authentication/signature system used to authenticate the subject.

### Adversary
Any actor attempting to create, modify, suppress, replay or falsely attribute legal intent or policy state.

## 4. Threats and controls

### T1 — Handwritten-signature forgery

**Threat:** An attacker reproduces or pastes the subject's handwritten signature onto a document.

**Control:** A relying party checks authoritative policy. If effective policy is `DIGITAL_ONLY`, handwriting alone MUST NOT establish legal intent.

### T2 — Credential theft

**Threat:** An attacker gains control of a digital credential.

**Control:** Use credential revocation/suspension/re-issuance and audit. Credential compromise MUST NOT reactivate handwritten authority.

### T3 — Unauthorized activation

**Threat:** An attacker activates `DIGITAL_ONLY` for another person.

**Control:** Strong authentication and explicit transaction-specific confirmation. A national profile SHOULD provide independent notification where practical.

### T4 — Unauthorized downgrade

**Threat:** An attacker attempts to return a subject from `DIGITAL_ONLY` to `HANDWRITTEN_ALLOWED`.

**Control:** Downgrade is split into `DOWNGRADE_REQUESTED` and `DOWNGRADE_EFFECTIVE`, with a bounded cooling-off period, fresh high-assurance authentication and cancellation capability. The request alone never changes effective policy.

### T5 — Workflow/policy confusion

**Threat:** An implementation or relying party treats a workflow event such as `DOWNGRADE_REQUESTED` as if it were an effective legal policy state.

**Control:** Data models MUST separate `event_type` from optional `effective_policy`; policy resolution MUST ignore events without an effective policy transition.

### T6 — Registry rollback

**Threat:** A privileged actor restores an older internally consistent snapshot in which the subject was not yet `DIGITAL_ONLY`.

**Control:** Append-only/tamper-evident history plus external checkpoints, transparency/audit anchoring or independent replication in production. A local hash chain alone is insufficient to prove freshness.

### T7 — Replay of stale assertion

**Threat:** An old `HANDWRITTEN_ALLOWED` assertion is reused after activation.

**Control:** Assertions carry issue time, queried legal time, expiry/freshness semantics, unique identifiers and integrity protection. High-risk profiles SHOULD require adequate freshness.

### T8 — Registry outage

**Threat:** The registry cannot be queried.

**Control:** Return `INDETERMINATE` or equivalent non-permissive result. Outage MUST NOT imply `HANDWRITTEN_ALLOWED` or create a policy transition.

### T9 — Catastrophic infrastructure failure

**Threat:** A wide-area or long-duration failure makes ordinary digital verification unavailable and operational pressure causes actors to restore handwriting by default.

**Control:** Treat this as continuity-of-law, not downgrade. Alternative digital, analog-mechanical or other continuity mechanisms MAY be used only if they preserve equivalent assurance. No automatic handwriting fallback.

### T10 — Enumeration and privacy leakage

**Threat:** An attacker scans identifiers to discover citizens or their policy choices.

**Control:** Avoid a public population registry; use authorization, privacy-preserving references, rate limits, purpose limitation and minimal responses.

### T11 — Signing-history privacy leakage

**Threat:** A signing-evidence store reveals transaction relationships, document semantics or behavioral patterns.

**Control:** Store commitments/hashes rather than documents, minimize metadata, protect read access, resist enumeration/correlation and separate evidence storage from public policy lookup.

### T12 — Signing history used as a secret

**Threat:** A recovery design asks a subject to prove identity by recalling previous documents or evidence entries, turning public/observable history into a password.

**Control:** Signing history MAY support cryptographic continuity and audit but MUST NOT be treated as a knowledge-based authentication secret.

### T13 — Identity mismatch

**Threat:** A policy assertion is checked for the wrong person.

**Control:** Establish authoritative identity binding before policy verification. Human-readable names alone are not unique identifiers.

### T14 — Coercion

**Threat:** A person is forced to activate, downgrade or authorize a transaction.

**Control:** Cryptography alone cannot solve coercion. Profiles SHOULD use delay for downgrade, independent notification, transaction-specific review and legally defined safeguards where appropriate.

### T15 — Malicious or negligent relying party

**Threat:** An institution skips the policy check and accepts handwriting despite `DIGITAL_ONLY`.

**Control:** The legal layer should assign consequences or liability; the technical layer produces verifiable evidence of policy checks.

### T16 — Malicious registry authority

**Threat:** An insider alters state/history, substitutes registry data or abuses signing authority.

**Control:** Authentication, separation of duties, protected signing keys, key rotation, independent audit and externally anchored integrity evidence in production.

### T17 — Privileged recovery/override backdoor

**Threat:** A permanent administrative or recovery channel becomes an easier path to change legal state than the normal subject-controlled workflow.

**Control:** Minimize independent state-changing channels. Each privileged path MUST have a concrete legal/operational justification, equal or stronger assurance, auditability and explicit semantics. Existing verified history should be used for continuity where possible instead of adding unnecessary override channels.

### T18 — Closed bootstrap capture

**Threat:** An invite/second-credential bootstrap mechanism evolves into a permissioned membership system where existing participants control who can exercise the legal right to activate DOLI.

**Control:** Bootstrap credentials MAY assist initial enrollment but MUST NOT be the exclusive source of eligibility. Eligibility derives from legal identity/status under the adopting jurisdiction.

### T19 — Cooling-off abuse

**Threat:** An attacker repeatedly requests downgrades, blocks cancellation, or exploits timing ambiguity around the not-before completion time.

**Control:** Requests are uniquely identified and auditable; effective policy remains `DIGITAL_ONLY` until a separate successful completion event; completion verifies the pending request, cooling-off time and required fresh authorization.

### T20 — Technology-specific trust collapse

**Threat:** Legal validity becomes coupled to one vendor/network/implementation, causing policy continuity to fail when that technology disappears.

**Control:** Define assurance requirements independently of implementation technology and permit alternative conforming implementations with equivalent authenticity, integrity, timing and historical-verification properties.

## 5. Trust assumptions

The reference protocol assumes:

1. an authoritative legal-identity context exists;
2. at least one high-assurance mechanism can establish subject authorization for state-changing operations;
3. a registry authority is legally empowered to publish policy assertions;
4. verifiers authenticate registry assertions using independently trusted key material or an equivalent trust anchor;
5. law defines the legal consequence of ignoring the policy.

The protocol does not assume that any single credential, registry, network or government IT system is infallible. A public key carried inside an assertion MUST NOT establish its own authority.

## 6. Security invariants

- **I1:** No infrastructure failure silently converts `DIGITAL_ONLY` into `HANDWRITTEN_ALLOWED`.
- **I2:** `INDETERMINATE` is a verification outcome, not an effective policy state.
- **I3:** Policy history is evaluated at the legally relevant time.
- **I4:** Workflow events and effective-policy transitions are structurally distinct.
- **I5:** A downgrade request cannot change policy before a separate valid completion event.
- **I6:** Credential recovery does not imply policy downgrade.
- **I7:** Stale assertions are distinguishable from fresh assertions.
- **I8:** A verifier learns no more identity/history information than necessary.
- **I9:** Historical policy changes leave detectable integrity evidence in the production trust model.
- **I10:** Compromise of one credential does not make handwriting valid again.
- **I11:** Signing evidence is not an authentication secret.
- **I12:** Bootstrap assistance does not create closed membership.
- **I13:** Additional privileged state-change channels are minimized and justified.
- **I14:** Technology neutrality preserves equivalent assurance rather than lowering it.

## 7. Reference implementation boundary

The reference implementation uses synthetic identities, local SQLite storage, local Ed25519 development keys and unauthenticated demonstration mutation/admin endpoints. Those choices are not production controls.

The prototype hash chains detect many in-place modifications but cannot alone detect replacement by an older valid snapshot. Production anti-rollback requires an external freshness/integrity reference.

## 8. Out of scope for Draft 0.4

This threat model does not prescribe a national identity-number format, a specific QES/eID provider, a blockchain, a universal coercion solution, jurisdiction-specific liability thresholds, a production HSM architecture, a specific transparency-log technology or a single continuity-of-law implementation.
