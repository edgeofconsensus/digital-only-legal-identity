# Digital-Only Legal Identity — Specification

Status: Draft 0.4.1

## 1. Objective

Define a jurisdiction-neutral mechanism by which a natural person can formally refuse recognition of a handwritten signature as sufficient evidence of that person's legal intent for future covered transactions after a defined effective time.

The mechanism is intentionally separate from any particular electronic-signature technology. A jurisdiction may bind the policy to qualified electronic signatures, national electronic identification systems, hardware credentials, analog-mechanical mechanisms, or other legally recognized high-assurance mechanisms that satisfy equivalent assurance requirements.

## 2. Effective legal policy

The externally effective legal policy is one of exactly two values:

- `HANDWRITTEN_ALLOWED`
- `DIGITAL_ONLY`

`HANDWRITTEN_ALLOWED` means the protocol itself does not restrict the ordinary legal treatment of handwriting.

`DIGITAL_ONLY` means that, for covered transactions, a handwritten signature attributed to the subject is not sufficient by itself to establish legal intent.

`INDETERMINATE` is not an effective legal policy. It is a verification outcome used when an authoritative answer cannot safely be established. It MUST NOT be interpreted as `HANDWRITTEN_ALLOWED`.

## 3. Default and voluntary-parallel semantics

In the absence of an effective DOLI activation, the subject remains under the ordinary legal regime:

```text
no effective activation -> HANDWRITTEN_ALLOWED
```

DOLI MUST NOT alter the legal treatment of persons who have not voluntarily activated `DIGITAL_ONLY`.

Parallel deployment therefore means coexistence between DOLI participants and non-participants at the societal/infrastructure level. It MUST NOT mean that handwriting silently remains an alternative authorization method for a subject after `DIGITAL_ONLY` becomes effective.

## 4. Workflow events are not policy states

Activation, downgrade, recovery and correction procedures are represented as workflow events separate from effective legal policy.

A reference profile MAY include events such as:

- `ACTIVATION_EFFECTIVE`
- `DOWNGRADE_REQUESTED`
- `DOWNGRADE_CANCELLED`
- `DOWNGRADE_EFFECTIVE`
- `RECOVERY_ENTERED`
- `RECOVERY_EXITED`
- `EVIDENCE_RECORDED`

Only events explicitly defined as effective policy transitions change legal policy. Workflow requests, recovery conditions and verification failures MUST NOT be treated as effective policy states.

## 5. Activation and open joining

Activation of `DIGITAL_ONLY` MUST require strong authentication and an explicit expression of intent. A jurisdiction MUST define the legally effective timestamp.

An additional credential, invitation or attestation by an existing participant MAY be used as a transitional bootstrap mechanism, but it MUST NOT create a closed membership model or give existing participants exclusive authority to admit new subjects.

The right to activate DOLI derives from the subject's legal eligibility, not from membership in a permissioned network.

## 6. Downgrade and cooling-off

A downgrade from `DIGITAL_ONLY` to `HANDWRITTEN_ALLOWED` reduces protection and MUST NOT be easier than activation.

A high-assurance profile SHOULD require fresh high-assurance authentication, explicit confirmation, auditable workflow events and a bounded cooling-off period before the downgrade becomes effective.

During the cooling-off period:

- the downgrade request is recorded;
- the effective legal policy remains `DIGITAL_ONLY`;
- the request can be cancelled through the defined procedure;
- no relying party may infer `HANDWRITTEN_ALLOWED` merely from the existence of a downgrade request.

Cooling-off is not a universal delay rule. Urgent credential revocation MAY require immediate effect.

## 7. Recovery is separate from downgrade

Loss or compromise of a credential MUST NOT automatically downgrade the subject to `HANDWRITTEN_ALLOWED`.

```text
identity recovery != security-policy downgrade
```

Recovery events MAY restrict accepted authorization methods while identity or credential control is re-established, but the effective policy remains unchanged unless a separate legally effective policy transition occurs.

### 7.1 Credential-first recovery

A DOLI identity MAY be associated with a set of independently usable high-assurance credentials rather than one permanent credential. Credential references SHOULD be independently revocable and replaceable without changing the effective legal policy.

Before entering an enhanced identity-recovery procedure, an implementation SHOULD determine whether at least one already-authorized credential remains usable. If sufficient credential control can be established, recovery SHOULD proceed through credential rotation, revocation or replacement and MUST NOT be treated as policy downgrade.

Loss of one credential therefore does not imply loss of the DOLI identity or loss of `DIGITAL_ONLY` protection.

### 7.2 Enhanced identity recovery

If no sufficient authorized credential remains available, a jurisdiction MAY define an enhanced recovery procedure. Such a procedure is an identity-continuity mechanism, not a hidden override of effective policy.

An enhanced recovery procedure MAY use a structured identity interview or other post-classical evidence evaluation that combines independent evidence classes rather than relying on a single reusable secret. The procedure SHOULD:

- evaluate claims against independently verifiable identity, credential, policy and authorization history where legally permitted;
- minimize disclosure of document content and unrelated personal data;
- distinguish continuity evidence from authentication secrets;
- record the evidence classes and decision result without unnecessarily centralizing raw evidence;
- fail closed when material contradictions cannot be resolved;
- resist social-engineering answers derived from public or previously leaked information.

The interview itself MUST NOT be treated as a password, knowledge-based authentication quiz or authority to downgrade policy.

### 7.3 Contradiction gate

Material contradictions between recovery claims and authoritative or independently verifiable evidence MUST prevent automatic recovery completion until resolved under the jurisdiction's defined procedure.

A contradiction gate SHOULD distinguish at least:

- absence of evidence;
- stale or superseded evidence;
- benign mismatch that can be reconciled;
- material contradiction indicating possible impersonation, coercion or corrupted records.

The system MUST NOT resolve a material contradiction by silently lowering the assurance threshold or restoring handwritten authority.

### 7.4 Recovery cooling-off

Successful enhanced identity proofing MAY create a pending credential-recovery result subject to a bounded cooling-off period before a replacement credential becomes fully authoritative. During that interval, the effective DOLI policy remains unchanged.

A recovery cooling-off period SHOULD support cancellation or challenge through any still-valid independent credential or other defined high-assurance channel. It MUST NOT delay urgent revocation of a credential known or suspected to be compromised.

Recovery completion authorizes credential continuity only. A separate downgrade workflow is required to change `DIGITAL_ONLY` to `HANDWRITTEN_ALLOWED`.

## 8. Infrastructure failure and continuity of law

Registry unavailability, widespread technical failure or loss of a particular class of digital infrastructure MUST NOT automatically change effective policy.

Catastrophic infrastructure failure is a continuity-of-law problem, not an implicit `DIGITAL_ONLY -> HANDWRITTEN_ALLOWED` transition.

A jurisdiction MAY define independent continuity mechanisms, including non-digital implementations, but such mechanisms MUST preserve equivalent assurance requirements and MUST NOT silently restore handwriting as sufficient evidence of legal intent.

## 9. Technology neutrality

The legal validity of DOLI MUST NOT depend on one software product, vendor, network, hardware platform or class of computing technology.

A digital, analog-mechanical or other implementation MAY conform if it provides equivalent guarantees for:

- authenticity;
- integrity;
- temporal determinacy;
- historical verifiability;
- resistance to unauthorized state change;
- auditable provenance appropriate to the jurisdiction.

Technology neutrality does not reduce the assurance threshold.

## 10. Historical policy semantics

A transaction is evaluated against the effective policy at legally relevant timestamp `t_legal`.

Conceptually:

```text
policy_at(t_legal) = latest effective policy transition with effective_at <= t_legal
```

Workflow-only events are ignored by policy resolution.

If multiple effective policy transitions share the same timestamp, the implementation MUST use a deterministic tie-break rule.

A later downgrade MUST NOT retroactively validate handwriting created while `DIGITAL_ONLY` was effective. A later activation MUST NOT retroactively alter transactions completed before activation became effective.

## 11. Legal semantics

The central proposed rule is:

> A person may formally refuse recognition of a handwritten signature as sufficient evidence of that person's legal intent for future covered transactions.

Under `DIGITAL_ONLY`, handwriting alone does not create a presumption of the subject's legal intent and is not sufficient evidence of consent for the covered action.

This core rule does not itself require automatic invalidity of the entire document. An adopting jurisdiction may impose stronger sector-specific consequences, including statutory invalidity, presumptions against handwriting-only consent, relying-party liability or mandatory additional authorization.

Such consequences are legal-policy choices and MUST NOT be silently encoded as technical assumptions.

## 12. Signed policy assertions

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
- relevant history integrity reference where applicable;
- cryptographic signature or equivalent integrity proof.

A relying party MUST establish trust in the authoritative registry key or certificate chain independently. A public key embedded in an assertion MUST NOT establish its own authority.

## 13. Verification

Conceptual request:

```http
GET /v1/signature-policy/{privacy-preserving-identity-reference}?at=2026-09-07T17:00:00Z
```

The response is a signed assertion containing `HANDWRITTEN_ALLOWED`, `DIGITAL_ONLY` or the verification outcome `INDETERMINATE`.

A verifier SHOULD check registry/key trust, signature, issuer, key identifier, assertion freshness, subject, queried timestamp, schema/jurisdiction compatibility and required history-integrity references.

If an implementation cannot safely establish the policy, it MUST return `INDETERMINATE` or an equivalent non-permissive verification outcome rather than infer handwritten authority.

## 14. Minimal policy-event history

A production registry SHOULD maintain an append-only or tamper-evident history that distinguishes:

- workflow event type;
- optional effective policy value;
- request timestamp;
- effective timestamp where applicable;
- transition identifier;
- previous integrity reference where chaining is used;
- authorization/audit evidence appropriate to the jurisdiction.

The data model SHOULD make it structurally difficult to mistake a workflow request for an effective legal policy transition.

## 15. Signing-evidence history

DOLI MAY maintain a separate minimal history of prior cryptographically verifiable legal authorizations to support continuity and audit without creating additional permanent privileged recovery paths.

Signing-evidence history MUST be logically distinct from policy-transition history.

A minimal evidence record MAY contain:

- evidence identifier;
- subject reference;
- document hash or commitment rather than document content;
- signing/authorization timestamp;
- credential or key reference;
- issuer/verifier metadata where needed;
- previous evidence integrity reference;
- integrity proof.

Knowledge of previous documents or evidence entries MUST NOT become a recovery secret or authentication password.

## 16. Minimize privileged state-change channels

DOLI SHOULD minimize independent mechanisms capable of changing legally significant state.

Where trust can be established through existing high-assurance credentials, auditable policy history and verifiable signing evidence, a permanent override/recovery backdoor SHOULD NOT be mandatory merely for convenience.

Each additional state-changing channel is a separate trust boundary and MUST be justified by a concrete recovery or legal requirement.

## 17. Privacy

A verifier generally needs to know whether a specific legal identity was subject to `DIGITAL_ONLY` at a specific time. It does not need unrestricted access to unrelated identity data or signing history.

Implementations SHOULD use data minimization, purpose limitation, privacy-preserving identifiers, authorization, anti-enumeration measures and controls against correlation of signing-evidence history.

A public searchable list of `DIGITAL_ONLY` subjects is not required by the protocol.

## 18. Security rationale and invariants

The protocol preserves these core invariants:

1. No outage, recovery event, credential compromise or infrastructure failure silently restores handwritten authority.
2. `INDETERMINATE` never aliases to `HANDWRITTEN_ALLOWED`.
3. Effective timestamps control legal-time evaluation.
4. Workflow events and effective legal policy are distinct data concepts.
5. Downgrades are explicit, auditable and subject to a defined completion procedure.
6. Credential recovery and policy downgrade are separate operations.
7. Policy history is append-only or tamper-evident.
8. Historical transitions remain verifiable after later changes.
9. Joining may use transitional bootstrap credentials but MUST NOT become permissioned membership.
10. Technology neutrality MUST preserve equivalent assurance.
11. Additional privileged state-change channels are minimized and justified.
12. Signing evidence proves continuity/audit history and is not an authentication secret.
13. Loss of one credential does not imply loss of identity when another sufficient authorized credential remains usable.
14. Enhanced recovery MUST NOT complete automatically across unresolved material contradictions.
15. Recovery completion authorizes credential continuity, not policy downgrade.

## 19. Failure and threat model

The protocol must address registry unavailability, compromised credentials, delayed revocation information, coercion, identity mismatch, assertion replay, malicious or negligent relying parties, unauthorized enumeration, rollback or alteration of policy history, registry-authority compromise, abuse of downgrade/recovery channels, signing-history privacy leakage and infrastructure continuity.

Enhanced recovery must additionally address public-information impersonation, contradictory evidence, recovery-channel capture, coercive recovery attempts and attempts to convert credential loss into a policy downgrade.

Local hash chains or append-only database controls do not by themselves prove freshness of the authoritative snapshot. Production systems SHOULD use externally verifiable checkpoints, transparency mechanisms, independent replication or equivalent audit anchoring where appropriate.

## 20. Reference implementation profile 0.4

The reference profile should demonstrate with synthetic subjects:

- separate workflow events and effective policy transitions;
- default `HANDWRITTEN_ALLOWED` semantics for non-activated subjects;
- immediate demonstration activation;
- requested/cancelled/completed downgrade with configurable cooling-off;
- recovery events that do not change effective policy;
- current and historical policy resolution by `effective_at`;
- signed short-lived assertions;
- fail-closed `INDETERMINATE` behavior;
- append-only/tamper-evident event history;
- minimal signing-evidence commitments without document content;
- automated semantic and integrity tests.

Draft 0.4.1 specifies, but the current prototype does not yet implement, credential-set management, enhanced identity interview evaluation, contradiction classification or recovery cooling-off for replacement credentials. These are the next reference-implementation layer and MUST preserve the two-state effective-policy model.

The prototype does not implement real citizen identity proofing, production PKI/HSM key management, production authorization, national legal effect, complete continuity-of-law infrastructure or production privacy controls.

## 21. Non-goals

This project does not create or store real citizen identities, issue legally valid electronic signatures, replace national PKI/eID infrastructure, prescribe a mandatory blockchain, or claim that the reference implementation itself creates legal effect.
