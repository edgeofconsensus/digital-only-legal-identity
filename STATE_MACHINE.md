# Digital-Only Legal Identity — Policy State Machine

Status: Draft 0.2 companion

## 1. Purpose

This document defines the minimum jurisdiction-neutral state machine for a person's handwritten-signature policy.

The legal meaning of each state is defined by legislation or regulation. The protocol defines how states and transitions are represented, authenticated, timestamped and queried.

## 2. States

### `HANDWRITTEN_ALLOWED`

Default compatibility state. The protocol does not itself restrict the legal effect of handwriting.

### `DIGITAL_ONLY_PENDING`

The subject has successfully requested activation of `DIGITAL_ONLY`, but the policy has not yet reached its legally effective timestamp.

This state allows jurisdictions to implement a cooling-off period, notification window or fraud review without losing the audit trail of the request.

### `DIGITAL_ONLY`

For covered transactions, handwriting alone is not sufficient evidence of the subject's legal intent.

### `DOWNGRADE_PENDING`

A request has been made to leave `DIGITAL_ONLY`, but the less restrictive state is not yet effective.

During this state, `DIGITAL_ONLY` remains authoritative.

### `RECOVERY_RESTRICTED`

Optional exceptional state used when the subject cannot access ordinary credentials or when a credential compromise is under recovery.

This state MUST NOT restore handwritten authority. It only constrains which digital or supervised recovery routes are accepted.

## 3. Allowed transitions

```text
HANDWRITTEN_ALLOWED
    -> DIGITAL_ONLY_PENDING
    -> DIGITAL_ONLY

DIGITAL_ONLY
    -> DOWNGRADE_PENDING
    -> HANDWRITTEN_ALLOWED

DIGITAL_ONLY
    -> RECOVERY_RESTRICTED
    -> DIGITAL_ONLY

DIGITAL_ONLY_PENDING
    -> HANDWRITTEN_ALLOWED   (cancel before effective time, if jurisdiction permits)

DOWNGRADE_PENDING
    -> DIGITAL_ONLY          (cancel downgrade before effective time)
```

Direct `DIGITAL_ONLY -> HANDWRITTEN_ALLOWED` transitions SHOULD NOT be permitted in high-assurance profiles.

## 4. Transition record

Every transition MUST produce an immutable or tamper-evident event containing at least:

- policy reference;
- previous state;
- requested state;
- request timestamp;
- effective timestamp;
- authentication method class;
- transition identifier;
- jurisdiction;
- schema version;
- registry signature or equivalent integrity proof.

Production systems SHOULD also retain the relying identity-provider reference and audit metadata required by national law, while minimizing what is exposed through verification APIs.

## 5. Activation

A request for `DIGITAL_ONLY` MUST:

1. authenticate the subject using a legally recognized high-assurance mechanism;
2. present an explicit statement that handwritten signatures will no longer be sufficient for covered transactions after the effective time;
3. require affirmative confirmation specific to this policy change;
4. create a transition event before the state becomes effective;
5. notify the subject through at least one channel independent of the immediate transaction where practicable.

The effective timestamp may be immediate or delayed by jurisdictional policy.

## 6. Downgrade

A downgrade reduces protection and therefore MUST NOT be easier than activation.

A high-assurance profile SHOULD require some combination of:

- fresh high-assurance authentication;
- an explicit downgrade statement;
- a mandatory delay;
- independent notification;
- additional recovery verification;
- cancellation during the delay period.

Until the downgrade effective timestamp is reached, the authoritative state remains `DIGITAL_ONLY`.

## 7. Recovery

Loss or compromise of a digital credential MUST NOT cause automatic downgrade to `HANDWRITTEN_ALLOWED`.

Recovery operates on credentials, not on the signature-policy principle.

A jurisdiction may enter `RECOVERY_RESTRICTED` while identity is re-established. Permitted recovery mechanisms may include supervised in-person identity proofing, another trusted credential, hardware recovery credentials or other legally approved high-assurance procedures.

## 8. Historical semantics

The authoritative answer for a transaction is the state effective at the legally relevant timestamp `t_legal`.

Given transition events ordered by effective timestamp, the registry resolves:

```text
policy_at(t_legal) = latest transition with effective_at <= t_legal
```

A later downgrade MUST NOT retroactively validate a handwritten signature created while `DIGITAL_ONLY` was effective.

Likewise, later activation MUST NOT retroactively alter the status of a transaction completed before its effective timestamp.

## 9. Verification outcomes

A core verification interface SHOULD return one of the following outcomes:

- `HANDWRITTEN_ALLOWED`
- `DIGITAL_ONLY`
- `INDETERMINATE`

Pending states are resolved according to the policy effective at the queried legal time. Internal workflow state need not always be exposed to relying parties.

`INDETERMINATE` means that an authoritative answer cannot currently be established. It MUST NOT be interpreted as `HANDWRITTEN_ALLOWED`.

## 10. Failure semantics

For a covered transaction:

```text
if verified_policy == DIGITAL_ONLY:
    handwritten_signature_alone = insufficient

if verified_policy == HANDWRITTEN_ALLOWED:
    apply ordinary jurisdictional law

if verified_policy == INDETERMINATE:
    do not infer HANDWRITTEN_ALLOWED
```

The jurisdiction determines whether an indeterminate high-risk transaction is delayed, rejected or routed to another high-assurance procedure.

## 11. Signed assertion requirements

An authoritative policy assertion MUST bind at least:

- privacy-preserving subject reference;
- resolved policy outcome;
- queried legal timestamp;
- assertion issuance timestamp;
- assertion expiry or freshness bound;
- jurisdiction;
- schema version;
- unique assertion identifier;
- registry issuer;
- cryptographic integrity proof.

The assertion SHOULD be independently verifiable without exposing unrelated identity data.

## 12. Core invariants

1. No outage or recovery event silently restores handwritten authority.
2. Effective timestamps control legal-time evaluation.
3. Policy downgrades are explicit, auditable and no easier than activation.
4. Credential recovery and signature-policy downgrade are separate operations.
5. Historical transitions remain verifiable after later policy changes.
6. `INDETERMINATE` never aliases to `HANDWRITTEN_ALLOWED`.

## 13. Next step

The reference implementation should implement this state machine with synthetic identities only and expose a minimal API for:

- creating a synthetic policy subject;
- requesting activation;
- requesting/cancelling downgrade;
- querying current or historical policy;
- returning signed demonstration assertions;
- demonstrating fail-closed behavior during simulated registry failure.
