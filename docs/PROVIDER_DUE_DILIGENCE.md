# AI Coach Cloud Provider Due Diligence Package

> Status: Ready for Product Owner use  
> Package version: `1.0.0`  
> Prepared: 2026-07-11

## Purpose and Scope

This package is a reusable request for written provider evidence. It does not
authorize a provider, create an account, accept legal terms, transmit health
data, or replace qualified legal review. Send only the data-category description
and closed schema from [AI_COACH.md](AI_COACH.md); never attach a real request,
database, report, screenshot, token, or personal health value.

## Provider Request Template

Subject: Enterprise data-retention and regional-processing confirmation for a
health decision-support application

```text
We are evaluating your text-generation API for a single-user health
decision-support application. The service would receive a minimized,
pseudonymized structured context and must not calculate medical or recovery
scores.

Our release requires written, product-specific confirmation for the exact API
endpoint, model snapshot, project/account tier, and processing region. Please
answer questionnaire DD-01 through DD-24 and attach the requested evidence.

We cannot begin a trial with real data until all mandatory controls pass. A
generic privacy policy, encryption statement, or “not used for training” claim
is not sufficient evidence of zero request/response retention.
```

## Mandatory Questionnaire

### Service Identity and Region

- `DD-01`: Legal service entity and contracting entity.
- `DD-02`: Exact product, API endpoint, model identifier, and immutable snapshot.
- `DD-03`: Supported customer deployment countries and billing countries.
- `DD-04`: Inference processing region and every location where customer content
  or content-derived metadata may be processed or stored.
- `DD-05`: Whether regional routing is contractually guaranteed or best effort.

### Retention and Data Use

- `DD-06`: Exact retention period for request content, response content,
  classifier outputs, embeddings, caches, traces, and abuse-monitoring logs.
- `DD-07`: Account/project control or contract term that provides Zero Data
  Retention for both request and response content.
- `DD-08`: Whether any feature silently overrides zero retention, including
  background processing, prompt caching, files, tools, conversations, or safety
  review.
- `DD-09`: Confirmation that customer content is excluded from training, model
  improvement, evaluation, distillation, and human annotation by default.
- `DD-10`: Confirmation that neither raw content nor content-derived features are
  reused across customers.
- `DD-11`: Deletion completion time, backup deletion time, and deletion evidence.

### Human Access and Security

- `DD-12`: Every condition that permits employee, contractor, or subprocessor
  access to content, including law, safety, support, and incident response.
- `DD-13`: Technical control that disables routine human review for the project.
- `DD-14`: Role-based access, privileged-access approval, and access-log retention.
- `DD-15`: Encryption in transit and at rest, key ownership, and key rotation.
- `DD-16`: Security certifications and latest independent audit period.
- `DD-17`: Breach notification deadline and customer incident contact path.

### Subprocessors, Law, and User Rights

- `DD-18`: Complete subprocessor list, purpose, location, and advance-change notice.
- `DD-19`: Government-request handling and customer-notification policy.
- `DD-20`: Support for access, correction, export, deletion, and processing
  restriction requests.
- `DD-21`: Data-processing agreement, sensitive-personal-information terms, and
  cross-border transfer mechanism applicable to the deployment.

### Technical Enforcement

- `DD-22`: Strict JSON Schema/structured-output support for the exact snapshot.
- `DD-23`: Confirmation that stateless text inference works with storage, tools,
  files, search, background mode, and provider conversation state disabled.
- `DD-24`: Machine-verifiable project settings or API response that demonstrate
  retention mode and region without exposing secrets.

## Required Evidence Bundle

Every mandatory answer must cite at least one dated artifact:

- signed enterprise agreement, addendum, DPA, or order form;
- provider-issued product and endpoint retention matrix;
- account/project console export showing region and retention mode;
- exact model/endpoint documentation and immutable snapshot availability;
- current subprocessor list and change-notification terms;
- current independent audit or certification report summary;
- provider security contact confirmation for ambiguous exceptions.

Sales email alone is insufficient for retention, training, review, region, or
subprocessor commitments unless incorporated into the binding agreement.
Screenshots must redact account identifiers and credentials before entering this
workspace. Signed contracts remain outside the repository; record only their
title, version, effective date, expiry date, and local secure reference.

## Acceptance Matrix

This is a conjunctive gate, not a weighted score. Every mandatory control must
be `PASS`; `UNKNOWN`, `PARTIAL`, `EXCEPTION`, or `NOT APPLICABLE` is not approval.

| Gate | Required result | Evidence owner |
| --- | --- | --- |
| Supported deployment and billing region | PASS | Product Owner |
| Exact provider/model/endpoint/region | PASS | Chief Architect |
| Request and response Zero Data Retention | PASS | Product Owner |
| No training, improvement, annotation, or distillation | PASS | Product Owner |
| Routine human review disabled | PASS | Product Owner |
| No content-derived cross-customer reuse | PASS | Chief Architect |
| Stateless structured output with prohibited features off | PASS | Lead Engineer |
| Subprocessors and transfer mechanism accepted | PASS | Product Owner |
| Deletion and incident terms accepted | PASS | Product Owner |
| Evidence current and contractually applicable | PASS | Product Owner |

## Contract Red Lines

Reject or renegotiate when any term permits:

- provider retention of request or response content beyond transient inference;
- training, model improvement, distillation, annotation, or cross-customer reuse;
- routine human review or unspecified contractor access;
- unspecified processing locations or subprocessors;
- unilateral material data-use changes without advance notice and termination rights;
- indefinite backups, caches, traces, or abuse logs containing customer content;
- provider ownership of input, output, or content-derived features;
- a disclaimer that removes confidentiality obligations for submitted content;
- using unsupported regions, proxy routing, or third-party accounts.

Legally mandatory exceptional retention must be documented with trigger,
scope, maximum duration, access control, notice, and deletion behavior. It does
not automatically pass the project's Zero Data Retention gate.

## Evidence Review Record

Create one record per exact provider configuration:

```markdown
# Provider Evidence Review

- Review ID: PD-YYYY-NNN
- Provider / legal entity: [填写]
- Product / endpoint / snapshot: [填写]
- Deployment / processing region: [填写]
- Contract and evidence effective dates: [填写]
- Evidence secure reference: [填写，不放密钥或健康数据]
- Reviewer: [填写]
- Review date: YYYY-MM-DD
- Next review date: YYYY-MM-DD

| Question | PASS / FAIL / UNKNOWN | Evidence reference | Notes |
| --- | --- | --- | --- |
| DD-01…DD-24 | [填写] | [填写] | [填写] |

- Mandatory gate result: PASS / BLOCKED
- Exceptions: None / [填写]
- Product Owner approval: Pending / Approved / Rejected
- Chief Architect review: Pending / Accepted / Rejected
- Implementation authorization: NO / YES
```

`Implementation authorization` remains `NO` unless every mandatory gate passes,
the Product Owner explicitly approves, and the Chief Architect accepts the exact
configuration. Approval of one snapshot or region does not cover another.
After approval, encode only the non-secret decision metadata in
[`ai_coach_provider_approval.json`](../config/ai_coach_provider_approval.json)
and compute its configuration fingerprint. The committed default remains blocked.

## Revalidation Triggers

Re-run DD-01 through DD-24 before the first live request and at least annually.
Immediate revalidation is required for provider, legal entity, model snapshot,
endpoint, region, retention control, subprocessor, contract, safety-review,
pricing tier, or API-feature changes; provider incident or policy notice; and any
evidence older than 12 months.

Runtime must fail closed if an approved control is removed or expires. Historical
approval cannot authorize new requests after expiry, though existing local audit
records follow their approved deletion schedule.

## Safe Handling Rules

- Use synthetic examples only during procurement and technical verification.
- Do not put API keys, signed contracts, account IDs, or real health data in Git,
  project docs, tickets, screenshots, or email templates.
- Do not enable a trial merely to discover retention behavior.
- Record evidence metadata and decision outcome, not confidential contract text.
- Escalate legal interpretation to qualified counsel; Codex records technical
  controls but does not accept contracts or make legal conclusions.
# Supplement product enrichment

Supplement enrichment inherits the existing Provider Approval Gate. Current
status is `provider_blocked`; no provider adapter is active and no network call
is permitted. Any future provider must return source-bearing candidates only,
preserve retrieval time and regional/formula distinctions, and require explicit
user confirmation before formal catalog writes.
