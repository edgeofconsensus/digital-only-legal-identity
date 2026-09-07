# Digital-Only Legal Identity

An open proposal and reference implementation for a legal right to refuse recognition of a handwritten signature as sufficient evidence of a person's legal intent.

For an institution-facing summary focused on Ukraine, see [`docs/institutional-brief-ukraine.md`](docs/institutional-brief-ukraine.md).

## Core principle

A person should be able to formally activate a **digital-only legal identity** status. From its effective date, a handwritten signature attributed to that person should no longer be sufficient, by itself, to establish that person's legal intent in transactions covered by the regime.

DOLI regulates legal/evidentiary sufficiency, not the physical act of handwriting.

## Effective policy

The effective legal policy has exactly two values:

- `HANDWRITTEN_ALLOWED` — ordinary law continues to govern handwriting.
- `DIGITAL_ONLY` — handwriting alone is insufficient for covered legal actions.

`INDETERMINATE` is a verification outcome, not a third legal-policy state. It must never silently alias to `HANDWRITTEN_ALLOWED`.

A subject who has not activated DOLI remains in the ordinary legal regime. Parallel deployment therefore lets participants and non-participants coexist without weakening the policy of a participant who has already activated `DIGITAL_ONLY`.

## Workflow semantics

Draft 0.4 separates workflow events from effective legal policy. The reference implementation demonstrates:

- immediate synthetic `ACTIVATION_EFFECTIVE`;
- `DOWNGRADE_REQUESTED` with a configurable cooling-off period;
- `DOWNGRADE_CANCELLED`;
- `DOWNGRADE_EFFECTIVE` only after cooling-off;
- `RECOVERY_ENTERED` / `RECOVERY_EXITED` without policy downgrade;
- no outage or infrastructure-failure transition back to handwriting.

A workflow request is never treated as an effective policy merely because it is the newest event.

## Technology neutrality

The legal model is intentionally independent of a single product, vendor, network or computing class. A digital, analog-mechanical or other implementation may conform only if it preserves equivalent authenticity, integrity, temporal determinacy, historical verifiability and protection against unauthorized state change.

Technology neutrality is not a weaker assurance mode and is not a handwriting fallback.

## Signing-evidence history

The reference implementation includes a separate minimal signing-evidence stream. It stores a SHA-256 document commitment, credential reference, signing time and integrity-chain metadata; it does not store document content.

Signing evidence can support continuity and audit, but knowledge of previous evidence must not become an authentication password or recovery secret.

## Reference protocol direction

A relying party should be able to ask a minimal question without obtaining unnecessary personal information:

`What signature policy was legally effective for this identity at time T?`

The current reference API returns a short-lived Ed25519-signed assertion containing the resolved policy, queried legal time, issuer/key metadata and an event-chain integrity reference.

No real personal data belongs in this repository. The software is a reference implementation of a protocol and policy model, not a population registry.

## Policy proposal for Ukraine

`POLICY_PROPOSAL_UA.md` contains the normative-technical proposal for a voluntary Ukrainian pilot and institutional policy review.

No logos or implied partner endorsements are used. Potential integrations should be labeled only by factual status such as `implemented`, `compatible by design`, `proposed integration` or `out of scope`.

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

Draft 0.4 changes the synthetic SQLite schema to structurally separate workflow events from effective policy. If upgrading a local Draft 0.3 demo checkout, remove the old local `reference/doli.sqlite3` file before starting 0.4. No real data belongs in that database.

## Reference implementation security boundary

The current API is a synthetic demonstration only. Mutation, evidence-listing and outage-simulation endpoints are deliberately unauthenticated and are not production interfaces. The development Ed25519 private key is generated locally, stored unencrypted and is not production key management.

The public key embedded in an assertion is convenience data only. A relying party must obtain or pin the authoritative registry key through a trusted channel.

SQLite append-only triggers and per-subject hash chains make many modifications detectable, but they do not prevent a privileged operator from replacing the database with an older internally consistent snapshot. Production deployment requires authorization, protected key management, rotation, external freshness/audit anchoring, anti-enumeration controls, privacy protection for signing evidence and operational continuity guarantees.

The reference SQLite append path is also not hardened as a production concurrent-writer protocol.

## Project stages

**Stage 1 — Specification**  
Define legal semantics, state transitions, threat model and privacy requirements.

**Stage 2 — Reference API**  
Implement and test a synthetic registry, workflow model and verification endpoint.

**Stage 3 — Demonstration**  
Model a relying party checking DOLI before accepting a legal authorization.

**Stage 4 — Policy proposal**  
Prepare the Ukrainian normative-technical proposal and pilot profile for institutional review.

## Status

Draft 0.4 specification / reference implementation and Draft 0.2 Ukrainian policy proposal. This repository does not provide legal advice and does not represent an operational government service.

## License

A permissive open-source license will be selected before the first software release.
