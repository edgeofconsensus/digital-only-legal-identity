# Digital-Only Legal Identity — Initial Specification

Status: Draft 0.1

## 1. Objective

Define a jurisdiction-neutral mechanism by which a natural person can formally refuse the future use of a handwritten signature as sufficient evidence of that person's legal intent.

The mechanism is intentionally separate from any particular electronic-signature technology. A jurisdiction may bind the policy to qualified electronic signatures, national electronic identification systems, hardware credentials, or other legally recognized high-assurance mechanisms.

## 2. Policy states

### `HANDWRITTEN_ALLOWED`

The person has not activated the digital-only policy. Existing law determines the evidentiary and legal effect of handwritten and electronic signatures.

### `DIGITAL_ONLY`

For transactions within the scope of the regime, a handwritten signature attributed to the person is not sufficient by itself to establish legal intent. A legally qualifying digital authorization is required.

## 3. Minimum registry record

A production system should minimize disclosed information. Conceptually, a policy record requires:

- a non-public or privacy-preserving identity reference;
- policy state;
- effective timestamp;
- jurisdiction;
- policy/schema version;
- record status;
- cryptographic evidence that the assertion was issued by an authorized registry.

The public verification interface should not expose a national population database.

## 4. Activation

Activation of `DIGITAL_ONLY` MUST require strong authentication of the person and an explicit expression of intent.

The jurisdiction MUST define an effective time. Historical documents MUST be evaluated against the policy state effective at the relevant legal time, rather than merely against the person's current status.

## 5. Verification

Before relying on a handwritten signature for a covered transaction, a relying party queries or otherwise obtains an authoritative assertion of the person's signature policy.

Conceptual request:

```http
GET /v1/signature-policy/{privacy-preserving-identity-reference}?at=2026-09-07T17:00:00Z
```

Conceptual response:

```json
{
  "policy": "DIGITAL_ONLY",
  "effective_from": "2026-09-01T00:00:00Z",
  "jurisdiction": "example",
  "schema_version": "0.1",
  "assertion_issued_at": "2026-09-07T17:00:01Z"
}
```

The final protocol MUST define authentication, authorization, rate limiting, privacy controls, integrity protection and cryptographic verification of assertions.

## 6. Legal semantics

The central proposed rule is:

> A person may formally refuse recognition of a handwritten signature as sufficient evidence of that person's legal intent for future covered transactions.

A jurisdiction adopting the model must choose the precise consequence of violating the policy. Candidate models include:

- invalidity of the attempted authorization;
- rebuttable or irrebuttable presumption that handwriting alone did not establish consent;
- liability assigned to a relying institution that failed to check the policy;
- mandatory additional digital verification before legal effect can arise.

These alternatives are policy questions and MUST NOT be silently encoded as technical assumptions.

## 7. Security rationale

Handwriting is reproducible information and does not provide a native mechanism for revocation, expiration, certificate validation or cryptographically verifiable audit history.

Modern electronic-signature systems can provide an explicit credential lifecycle including issuance, authentication, validation, revocation and re-issuance. The protocol should preserve those advantages rather than attempting to create a digital image-based replacement for handwriting.

## 8. Privacy principle

A verifier generally needs to know whether a particular legal identity was subject to `DIGITAL_ONLY` at a specified time. It does not need unrestricted access to the person's other registry data.

Implementations SHOULD therefore use data minimization, purpose limitation and privacy-preserving identifiers or assertions wherever practical.

## 9. Failure model

The specification must explicitly address:

- registry unavailability;
- compromised digital credentials;
- delayed revocation information;
- coercion;
- identity mismatch;
- replay of old policy assertions;
- malicious or negligent relying parties;
- unauthorized enumeration of citizens;
- rollback or alteration of policy history.

No failure mode should silently restore handwritten signatures to full authority for a person whose effective policy is `DIGITAL_ONLY`.

## 10. Non-goals

This project does not:

- create or store real citizen identities;
- issue legally valid electronic signatures;
- replace national PKI or electronic-identification infrastructure;
- claim that a reference implementation itself creates legal effect;
- prescribe one country's constitutional or evidentiary rules to another jurisdiction.

## 11. Next specification work

Draft 0.2 should define the policy state machine, activation/recovery rules, historical-query semantics, signed assertion format and a threat model before implementation is treated as more than a demonstration.
