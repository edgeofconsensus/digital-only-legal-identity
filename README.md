# Digital-Only Legal Identity

An open proposal and reference implementation for a legal right to refuse recognition of a handwritten signature as sufficient evidence of a person's legal intent.

For an institution-facing summary focused on Ukraine, see [`docs/institutional-brief-ukraine.md`](docs/institutional-brief-ukraine.md).

## Core principle

A person should be able to formally activate a **digital-only legal identity** status. From its effective date, a handwritten signature attributed to that person should no longer be sufficient, by itself, to establish that person's legal intent in transactions covered by the regime.

The purpose is not merely to digitize handwriting. It is to replace a difficult-to-revoke graphical identifier with verifiable electronic authorization that has an explicit security lifecycle.

## Security premise

A handwritten signature has no native security lifecycle. A qualified electronic signature can have one: issuance, authentication, certificate validation, verification, logging, revocation and re-issuance.

This project therefore treats handwritten signatures primarily as a historical legal mechanism rather than the preferred mechanism for high-assurance authorization.

## Proposed model

The externally effective policy has two legal-policy states:

- `HANDWRITTEN_ALLOWED` — existing legal rules continue to apply.
- `DIGITAL_ONLY` — handwritten signatures are not sufficient evidence of legal intent for covered actions and a qualifying digital authorization is required.

`INDETERMINATE` is a verification outcome, not a permissive policy state. It means the registry cannot safely establish an authoritative answer and MUST NOT be interpreted as `HANDWRITTEN_ALLOWED`.

A national implementation would need to define activation and downgrade procedures, effective timestamps, covered transactions, verifier authorization, legal consequences, privacy controls, auditability, availability and interoperability with national and international electronic-signature frameworks.

## Reference protocol direction

A relying party should be able to ask a minimal question without obtaining unnecessary personal information:

`What signature policy was legally effective for this identity at time T?`

The current reference API returns a short-lived Ed25519-signed assertion containing the resolved policy, queried legal time, issuer/key metadata and an event-chain integrity reference.

No real personal data belongs in this repository. The software is a reference implementation of a protocol and policy model, not a population registry.

## Run the reference API

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reference/requirements.txt
uvicorn reference.main:app --reload
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1` instead.

The API is then available at `http://127.0.0.1:8000`; FastAPI's local interactive documentation is at `/docs`.

Run the automated tests with:

```bash
pytest -q reference/tests
```

Local SQLite data and the development signing key are intentionally excluded from version control.

## Reference implementation security boundary

The current API is a synthetic demonstration only. Mutation endpoints and the outage-simulation admin endpoint are deliberately unauthenticated. The development Ed25519 private key is generated locally, stored unencrypted and is not production key management.

The public key embedded in an assertion is convenience data only. A relying party must obtain or pin the authoritative registry key through a trusted channel; trusting an arbitrary embedded key would defeat the signature trust model.

The SQLite append-only triggers and per-subject hash chain make many modifications detectable, but they do not prevent a privileged operator from replacing the database with an older internally consistent snapshot. Production deployment requires stronger authorization, HSM or equivalent key protection, key rotation, external audit anchoring/checkpoints, anti-enumeration controls and operational availability guarantees.

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

Draft 0.3 specification / reference implementation. This repository does not provide legal advice and does not represent an operational government service.

## License

A permissive open-source license will be selected before the first software release.
