# Digital-Only Legal Identity — Policy State Machine

Status: Draft 0.3 companion

## 1. Purpose

This document separates externally effective signature policy from internal workflow state.

The legal meaning of each transition is defined by legislation or regulation. The protocol defines how requests, effective times, recovery conditions and verification outcomes are represented and queried.

## 2. Effective policy states

The externally effective policy is intentionally small:

### `HANDWRITTEN_ALLOWED`

Default compatibility state. The protocol does not itself restrict the legal effect of handwriting.

### `DIGITAL_ONLY`

For covered transactions, handwriting alone is not sufficient evidence of the subject's legal intent.

`INDETERMINATE` is not a stored policy state. It is a verification outcome returned when an authoritative answer cannot safely be established.

## 3. Workflow events and conditions

A production profile may represent workflow with events or internal conditions such as:

- `ACTIVATION_REQUESTED`
- `ACTIVATION_EFFECTIVE`
- `ACTIVATION_CANCELLED`
- `DOWNGRADE_REQUESTED`
- `DOWNGRADE_CANCELLED`
- `DOWNGRADE_EFFECTIVE`
- `RECOVERY_ENTERED`
- `RECOVERY_EXITED`

A workflow event does not automatically change the effective policy. The effective timestamp and transition semantics determine when the externally authoritative policy changes.

The current reference implementation uses `DOWNGRADE_PENDING` as a demonstration event/state label. It resolves this label externally as `DIGITAL_ONLY`; therefore a pending downgrade never restores handwritten authority.

Delayed activation, completed downgrade and recovery-state transitions remain specification work for the next prototype revision.

## 4. Conceptual transitions

```text
HANDWRITTEN_ALLOWED
    -- activation requested --> HANDWRITTEN_ALLOWED
    -- activation effective --> DIGITAL_ONLY

DIGITAL_ONLY
    -- downgrade requested --> DIGITAL_ONLY
    -- downgrade cancelled --> DIGITAL_ONLY
    -- downgrade effective --> HANDWRITTEN_ALLOWED

DIGITAL_ONLY
    -- recovery entered --> DIGITAL_ONLY
    -- recovery exited --> DIGITAL_ONLY
```

Direct immediate downgrade from `DIGITAL_ONLY` to `HANDWRITTEN_ALLOWED` SHOULD NOT be permitted in high-assurance profiles.

## 5. Transition record

Each transition or workflow event SHOULD be represented by an immutable or tamper-evident record binding at least:

- subject/policy reference;
- event or requested transition type;
- request timestamp;
- effective timestamp where applicable;
- transition identifier;
- authentication method class;
- jurisdiction;
- schema version;
- previous integrity reference where a chain is used;
- registry integrity proof or equivalent audit evidence.

The reference implementation currently records `transition_id`, `subject_ref`, `state`, `requested_at`, `effective_at`, `previous_event_hash` and `event_hash` in an append-only SQLite demonstration store.

## 6. Activation

A production activation request for `DIGITAL_ONLY` MUST:

1. authenticate the subject using a legally recognized high-assurance mechanism;
2. present an explicit statement that handwriting will no longer be sufficient for covered transactions after the effective time;
3. require affirmative confirmation specific to the policy change;
4. record the request before the policy becomes effective;
5. notify the subject through an independent channel where practicable.

The effective timestamp may be immediate or delayed by jurisdictional policy.

The current reference implementation demonstrates immediate activation and therefore records `DIGITAL_ONLY` directly.

## 7. Downgrade

A downgrade reduces protection and MUST NOT be easier than activation.

A high-assurance profile SHOULD require fresh high-assurance authentication, an explicit downgrade statement, independent notification, and a mandatory delay or recovery procedure where appropriate.

Until `DOWNGRADE_EFFECTIVE` becomes legally effective, the authoritative policy remains `DIGITAL_ONLY`.

The current reference implementation demonstrates `DOWNGRADE_PENDING` and cancellation only; it intentionally does not implement completed downgrade to `HANDWRITTEN_ALLOWED`.

## 8. Recovery

Loss or compromise of a digital credential MUST NOT cause automatic downgrade to `HANDWRITTEN_ALLOWED`.

Recovery operates on credentials, not on the signature-policy principle. A jurisdiction may constrain digital authorization while identity is re-established, but handwriting MUST NOT silently regain authority because ordinary credentials are unavailable.

## 9. Historical semantics

The authoritative answer for a transaction is the policy effective at legally relevant timestamp `t_legal`.

Conceptually:

```text
policy_at(t_legal) = latest effective policy transition with effective_at <= t_legal
```

If multiple effective transitions share the same timestamp, the implementation MUST use a deterministic tie-break rule.

The reference implementation resolves by `(effective_at, seq)` so append order alone cannot override an earlier legally effective transition.

A later downgrade MUST NOT retroactively validate handwriting created while `DIGITAL_ONLY` was effective. Likewise, later activation MUST NOT retroactively alter the status of a transaction completed before activation became effective.

## 10. Verification outcomes

A core verification interface returns one of:

- `HANDWRITTEN_ALLOWED`
- `DIGITAL_ONLY`
- `INDETERMINATE`

`INDETERMINATE` means an authoritative answer cannot currently be established. It MUST NOT be interpreted as `HANDWRITTEN_ALLOWED`.

The reference implementation returns `INDETERMINATE` during simulated registry outage or when the per-subject event hash chain fails verification.

## 11. Signed assertion requirements

An authoritative assertion MUST bind at least:

- privacy-preserving subject reference;
- resolved policy outcome;
- queried legal timestamp;
- assertion issuance timestamp;
- assertion expiry/freshness bound;
- unique assertion identifier;
- registry issuer;
- signing-key identifier;
- jurisdiction;
- schema version;
- relevant history integrity reference where applicable;
- cryptographic signature or equivalent proof.

The reference implementation uses Ed25519, includes issuer and `key_id`, and gives assertions a five-minute lifetime. A relying party MUST trust or pin an authoritative registry key independently; an embedded public key does not establish trust by itself.

## 12. Integrity and failure semantics

For a covered transaction:

```text
if verified_policy == DIGITAL_ONLY:
    handwritten_signature_alone = insufficient

if verified_policy == HANDWRITTEN_ALLOWED:
    apply ordinary jurisdictional law

if verified_policy == INDETERMINATE:
    do not infer HANDWRITTEN_ALLOWED
```

The current prototype uses SQLite triggers to reject ordinary update/delete operations and a per-subject SHA-256 hash chain to detect event-history modification. This is demonstration-level tamper evidence, not production-grade protection against a privileged database administrator.

## 13. Core invariants

1. No outage, recovery event or credential compromise silently restores handwritten authority.
2. Effective timestamps control legal-time evaluation.
3. Policy downgrades are explicit, auditable and no easier than activation.
4. Credential recovery and signature-policy downgrade are separate operations.
5. Historical transitions remain verifiable after later policy changes.
6. `INDETERMINATE` never aliases to `HANDWRITTEN_ALLOWED`.
7. Pending workflow conditions do not automatically become effective policy.

## 14. Reference implementation status

Prototype 0.3 implements synthetic-subject creation, immediate activation, pending/cancelled downgrade, current and historical policy queries, signed assertions, public-key discovery, append-only event storage, hash-chain verification and fail-closed outage behavior.

The next implementation step is the full workflow-event model: delayed activation, completed downgrade, recovery transitions, authentication/authorization, key rotation and stronger externally anchored audit integrity.
