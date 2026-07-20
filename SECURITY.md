# Security policy

## Supported versions

The latest code on `main` and the latest published prerelease receive security
fixes. The project is currently alpha; operators should pin a reviewed commit
and revalidate integrations before clinical-environment use.

## Reporting a vulnerability

Do not open a public issue containing an exploit, credential, patient data, or
other sensitive detail. Use GitHub's private vulnerability reporting for this
repository. If that option is unavailable, open a minimal public issue asking a
maintainer to enable a private contact channel, without disclosing the flaw.

Include the affected commit/version, impact, reproduction conditions, and any
known mitigation. Remove real patient data and secrets from all evidence.

## Deployment threat model

This repository is a gateway component, not a complete hospital security
boundary. A production operator remains responsible for network segmentation,
identity and access management, SMART/FHIR authorization, consent, audit logs,
retention, backups, regulatory compliance, and incident response.

Built-in safeguards include:

- bearer/API secrets are server settings and are excluded from MCP arguments,
  results, and normal logs;
- FHIR access is read-only and patient resources require explicit patient
  context;
- file access is limited to configured roots and rejects symlinks/escapes;
- SQLite is opened read-only with allowlisted, validated projections and bound
  search values; agents cannot submit SQL;
- vector search forwards no patient context except an operator-approved explicit
  filter object;
- web retrieval uses a startup allowlist of credential-free HTTPS URLs, follows
  no redirects, and enforces byte limits;
- upstream failures remain visible instead of being silently replaced.

## Sensitive data guidance

Never commit `.env`, access tokens, FHIR exports, production database files,
patient documents, or local indexes. Prefer short-lived workload credentials.
Use synthetic data in tests and examples. Treat query text and
`context.patient_id` as potentially sensitive, and configure transport/logging
accordingly in the deployment environment.

## Clinical safety

Public labels, spontaneous adverse-event reports, open datasets, and generated
summaries may be incomplete or delayed. Preserve provenance, warnings, errors,
effective dates, and the disclaimer. Do not use this gateway as the sole basis
for diagnosis, prescribing, dispensing, or dose adjustment.
