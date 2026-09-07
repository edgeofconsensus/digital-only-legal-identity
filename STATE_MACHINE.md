# Digital-Only Legal Identity — Policy State Machine

Status: Draft 0.4 companion

## 1. Purpose

This document defines the state semantics of DOLI by strictly separating effective legal policy, workflow events and verification outcomes.

## 2. Effective legal policy

The effective policy is intentionally binary:

### `HANDWRITTEN_ALLOWED`

Default compatibility state. DOLI itself does not restrict the ordinary legal treatment of handwriting.

### `DIGITAL_ONLY`

For covered transactions, handwriting alone is not sufficient evidence of the subject's legal intent.

`INDETERMINATE` is not a policy state. It is a verification outcome.

## 3. Workflow events

The reference workflow uses events rather than pseudo-policy states:

- `ACTIVATION_EFFECTIVE`
- `DOWNGRADE_REQUESTED`
- `DOWNGRADE_CANCELLED`
- `DOWNGRADE_EFFECTIVE`
- `RECOVERY_ENTERED`
- `RECOVERY_EXITED`

A workflow event changes effective policy only when its semantics explicitly define an effective policy transition.

`DOWNGRADE_REQUESTED`, `DOWNGRADE_CANCELLED`, `RECOVERY_ENTERED` and `RECOVERY_EXITED` do not themselves change effective policy.

## 4. Conceptual transitions

```text
HANDWRITTEN_ALLOWED
    -- ACTIVATION_EFFECTIVE --> DIGITAL_ONLY

DIGITAL_ONLY
    -- DOWNGRADE_REQUESTED --> DIGITAL_ONLY
    -- DOWNGRADE_CANCELLED --> DIGITAL_ONLY
    -- DOWNGRADE_EFFECTIVE --> HANDWRITTEN_ALLOWED

DIGITAL_ONLY
    -- RECOVERY_ENTERED --> DIGITAL_ONLY
    -- RECOVERY_EXITED --> DIGITAL_ONLY
```

No outage or infrastructure-failure event creates a policy transition.

## 5. Default semantics and parallel integration

A subject with no effective activation is resolved as `HANDWRITTEN_ALLOWED` under the ordinary legal regime.

Activation by one subject has no effect on another subject.

Parallel deployment means that participants and non-participants may coexist. It does not mean handwriting remains an alternative authorization route for a subject after `DIGITAL_ONLY` is effective.

## 6. Event record

Each event is immutable or tamper-evident and binds at least:

- `transition_id`;
- `subject_ref`;
- `event_type`;
- optional `effective_policy`;
- `requested_at`;
- optional `effective_at`;
- previous integrity reference;
- event integrity proof.

Only `ACTIVATION_EFFECTIVE` and `DOWNGRADE_EFFECTIVE` carry an effective policy in reference profile 0.4.

The schema is deliberately structured so that a workflow request cannot be resolved as a legal policy merely because it is the newest appended record.

## 7. Activation

Reference activation is immediate for demonstration purposes:

```text
ACTIVATION_EFFECTIVE(effective_policy=DIGITAL_ONLY)
```

A national profile may add an `ACTIVATION_REQUESTED` stage and a cooling-off period if required, but this is not necessary to demonstrate the core semantics.

Joining MAY use a transitional second credential or invitation as a bootstrap factor, but eligibility MUST NOT derive exclusively from membership in a closed participant set.

## 8. Downgrade and cooling-off

A downgrade is a controlled two-stage workflow.

First:

```text
DOWNGRADE_REQUESTED
```

The request records `requested_at` and a not-before completion time. During this period the effective policy remains `DIGITAL_ONLY`.

The subject may cancel:

```text
DOWNGRADE_CANCELLED
```

or, after the configured cooling-off period and successful completion checks, complete:

```text
DOWNGRADE_EFFECTIVE(effective_policy=HANDWRITTEN_ALLOWED)
```

A completed downgrade changes only future policy from its `effective_at`; it does not retroactively validate handwriting from a prior `DIGITAL_ONLY` period.

## 9. Recovery

Recovery operates on credentials and authorization capability, not on the legal policy itself.

```text
RECOVERY_ENTERED -> effective policy unchanged
RECOVERY_EXITED  -> effective policy unchanged
```

Loss of a credential, recovery mode or catastrophic infrastructure outage never implies a downgrade.

## 10. Infrastructure continuity

If the registry or broader digital infrastructure becomes unavailable, no event is appended merely to manufacture a more permissive policy.

The verification outcome may become `INDETERMINATE`, but the underlying legal policy remains whatever was previously effective.

Any analog-mechanical or other continuity mechanism is a separate implementation of policy verification and must preserve equivalent assurance; it is not a handwriting fallback.

## 11. Historical resolution

The authoritative policy for legal time `t_legal` is resolved only from effective-policy transitions:

```text
policy_at(t_legal) = latest event
    where effective_policy is not null
      and effective_at <= t_legal
```

If no such event exists, return `HANDWRITTEN_ALLOWED`.

If multiple effective transitions share the same timestamp, use deterministic sequence order as the tie-break rule.

Workflow-only events are ignored by policy resolution.

## 12. Verification outcomes

A verifier receives one of:

- `HANDWRITTEN_ALLOWED`
- `DIGITAL_ONLY`
- `INDETERMINATE`

`INDETERMINATE` means the current verification process cannot establish an authoritative result. It MUST NOT be persisted as effective policy and MUST NOT alias to `HANDWRITTEN_ALLOWED`.

## 13. Signing-evidence history

Signing evidence is a separate append-only/tamper-evident stream and is not part of policy resolution.

A minimal entry contains a document hash/commitment rather than document content, subject reference, signing time, credential reference and integrity-chain references.

Signing evidence may support continuity and audit, but knowledge of past evidence must never become an authentication secret.

## 14. Failure semantics

```text
if verified_policy == DIGITAL_ONLY:
    handwritten_signature_alone = insufficient

if verified_policy == HANDWRITTEN_ALLOWED:
    apply ordinary jurisdictional law

if verification_outcome == INDETERMINATE:
    do not infer HANDWRITTEN_ALLOWED
```

The legal system determines whether an indeterminate transaction is delayed, rejected or routed to another equivalent-assurance mechanism.

## 15. Core invariants

1. Effective legal policy has two values only.
2. `INDETERMINATE` is a verification outcome, never a stored policy.
3. Workflow events are structurally distinct from effective-policy transitions.
4. No outage, recovery or credential compromise silently restores handwritten authority.
5. Effective timestamps control legal-time evaluation.
6. Downgrade requires request plus a separately completed effective transition.
7. Cooling-off preserves `DIGITAL_ONLY` until completion.
8. Credential recovery and policy downgrade are separate operations.
9. Historical transitions remain verifiable after later changes.
10. Parallel integration does not weaken an activated subject's policy.
11. Technology continuity mechanisms preserve equivalent assurance rather than falling back to handwriting.

## 16. Reference implementation target 0.4

Prototype 0.4 implements synthetic-subject creation, immediate activation, requested/cancelled/completed downgrade with configurable cooling-off, recovery enter/exit events, historical policy resolution, signed assertions, append-only event storage, hash-chain verification, fail-closed outage behavior and a separate minimal signing-evidence history.
