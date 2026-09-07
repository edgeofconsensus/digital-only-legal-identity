# Digital-Only Legal Identity

An open proposal and reference implementation for a legal right to refuse recognition of a handwritten signature as sufficient evidence of a person's legal intent.

## Core principle

A person should be able to formally activate a **digital-only legal identity** status. From its effective date, a handwritten signature attributed to that person should no longer be sufficient, by itself, to establish that person's legal intent in transactions covered by the regime.

The purpose is not merely to digitize handwriting. It is to replace a difficult-to-revoke graphical identifier with verifiable electronic authorization that has an explicit security lifecycle.

## Security premise

A handwritten signature has no native security lifecycle. A qualified electronic signature can have one: issuance, authentication, certificate validation, verification, logging, revocation and re-issuance.

This project therefore treats handwritten signatures primarily as a historical legal mechanism rather than the preferred mechanism for high-assurance authorization.

## Proposed model

The initial model has two policy states:

- `HANDWRITTEN_ALLOWED` — existing legal rules continue to apply.
- `DIGITAL_ONLY` — handwritten signatures are not sufficient evidence of legal intent for covered actions and a qualifying digital authorization is required.

A national implementation would need to define:

1. how a person activates and changes the status;
2. when the status becomes legally effective;
3. which transactions are covered;
4. how institutions verify the status;
5. what legal consequence follows when an institution accepts handwriting despite `DIGITAL_ONLY`;
6. privacy-preserving access to the status;
7. auditability and availability requirements;
8. interoperability with national and international electronic-signature frameworks.

## Reference protocol direction

A relying party should be able to ask a minimal question without obtaining unnecessary personal information:

`What signature policy was legally effective for this identity at time T?`

A reference API may return a signed assertion containing only the policy state, effective time, jurisdiction/version information and verification metadata.

No real personal data belongs in this repository. The software developed here is a reference implementation of a protocol and policy model, not a population registry.

## Project stages

**Stage 1 — Specification**  
Define legal semantics, state transitions, threat model and privacy requirements.

**Stage 2 — Reference API**  
Implement a small registry simulator and verification endpoint using synthetic identities.

**Stage 3 — Demonstration**  
Model a relying party such as a bank or notary receiving a handwritten document, checking the policy and requiring digital authorization when the status is `DIGITAL_ONLY`.

**Stage 4 — Policy proposal**  
Prepare a jurisdiction-neutral policy paper and an implementation profile for Ukraine that can be submitted for institutional review.

## Status

Early specification / reference implementation. This repository does not provide legal advice and does not represent an operational government service.

## License

A permissive open-source license will be selected before the first software release.
