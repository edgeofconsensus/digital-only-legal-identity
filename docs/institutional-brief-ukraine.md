# Institutional Review Brief — Ukraine

## Purpose

This note is intended to support an initial institutional and technical review of the **Digital-Only Legal Identity** proposal in the Ukrainian context.

It is not a request to deploy the current reference implementation and does not assume that the proposed legal model should be adopted unchanged. The immediate objective is narrower: determine whether an opt-in legal mechanism that limits reliance on handwritten signatures is worth formal policy, legal, security, and interoperability analysis.

## Problem statement

A handwritten signature is a persistent graphical identifier. Once copied, reproduced, or disputed, it has no native revocation lifecycle comparable to modern electronic authorization mechanisms.

Ukraine already has mature electronic-identification and qualified electronic-signature infrastructure. The proposal asks whether an individual should be able to formally declare that, for covered legal actions after a defined effective time, a handwritten signature attributed to that individual is not sufficient by itself to establish legal intent.

## Proposed policy primitive

The model introduces an opt-in legal status with two externally effective policy states:

- `HANDWRITTEN_ALLOWED` — existing legal rules continue to apply;
- `DIGITAL_ONLY` — a handwritten signature alone is insufficient for covered actions and a qualifying electronic authorization is required.

The status is time-dependent. A verifier therefore needs an authoritative answer to a narrow question:

`What signature policy was legally effective for this identity at time T?`

The proposal is deliberately compatible with a history-based model: activation, later changes, and their effective times should remain auditable rather than being represented only by the current state.

## Design objectives

A production design should aim for:

- voluntary activation rather than mandatory removal of handwritten signatures;
- explicit effective timestamps and an auditable history of state changes;
- minimal disclosure to relying parties;
- interoperability with existing Ukrainian electronic-identification and qualified-signature infrastructure;
- strong authentication for activation and any later status change;
- clear downgrade and credential-recovery rules;
- verifiable issuer keys, rotation, revocation, and external audit anchoring;
- anti-enumeration and privacy protections;
- defined behavior during registry or network outages;
- accessibility and legally defined continuity procedures that preserve equivalent assurance and do not silently restore handwritten-signature sufficiency for a person whose `DIGITAL_ONLY` policy remains effective.

## Non-goals

The proposal does **not** require:

- abolishing handwritten signatures for the population as a whole;
- replacing existing qualified electronic signatures or Ukrainian digital-identity systems;
- storing unnecessary transaction data in a central registry;
- treating the current reference API as production-ready infrastructure;
- assuming that a technical mechanism alone determines legal validity;
- treating handwriting as an emergency fallback after `DIGITAL_ONLY` has become effective.

## Reference implementation

The repository contains a small synthetic reference API used to make the policy primitive testable.

The current Draft 0.4.1 implementation demonstrates:

- time-dependent policy resolution;
- signed assertions over the resolved policy;
- an event-chain integrity reference;
- synthetic identities only;
- explicit handling of an indeterminate verification result;
- a set of independently revocable/replaceable synthetic credentials;
- credential-first recovery routing;
- enhanced-recovery evidence classification with contradiction and reconciliation gates;
- a profile-defined evidence-sufficiency threshold and recovery cooling-off that do not alter the effective DOLI policy.

The implementation intentionally exposes several development-only security limitations. It is a protocol demonstration, not an operational registry and not a government service. Its recovery evidence is synthetic input; it does not perform production identity proofing.

## Questions for institutional review

An initial review could focus on the following questions:

1. Is the proposed opt-in legal status compatible with Ukrainian civil-law, electronic-trust-services, notarial, banking, and administrative frameworks?
2. Which existing electronic authorization mechanisms could satisfy the `DIGITAL_ONLY` requirement without creating a parallel identity system?
3. Which institution, if any, could authoritatively resolve the policy state at a historical time while minimizing personal-data exposure?
4. What activation, cooling-off, downgrade, credential-recovery, inheritance, incapacity, and emergency-continuity procedures would be legally necessary?
5. How should offline or unavailable-registry cases be treated without silently weakening the declared policy?
6. Which transaction classes should be in scope, excluded, or introduced only through a limited pilot?
7. Which enhanced-recovery assurance profile should determine the number and combination of independent evidence classes sufficient to admit a request into cooling-off?

## Suggested next step

A proportionate next step would be a **policy and threat-model review using synthetic identities**, followed, only if the concept survives that review, by a narrowly scoped interoperability prototype against existing Ukrainian electronic-authorization mechanisms.

This keeps legal interpretation, security architecture, privacy, and implementation feasibility separate until each has been evaluated.

## Project status

Concept and Draft 0.4.1 reference implementation. Open for legal, policy, security, cryptographic, privacy, accessibility, and interoperability review.
