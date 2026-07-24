# Project constitution

This document records the non-negotiable design rules for Pharmacy MCP.

## 1. One knowledge gateway

MCP `query_pharmacy`, the Python `PharmacyHarness`, and the CLI are views of one
application contract. New cross-source capabilities join the provider port and
registry instead of creating disconnected gateways. Focused atomic tools may
remain when deterministic workflow operations need them.

## 2. Stable, constrained output

Every agent-facing result uses a versioned, JSON-Schema-validated envelope.
`structuredContent` is authoritative; text is a deterministic rendering.
Agents preserve status, data, provenance, warnings, errors, metadata, and the
medical disclaimer. Breaking contract changes require a schema-version change.

## 3. Source honesty

Prefer primary official sources and identify jurisdiction and effective date.
Never invent missing facts, erase upstream disagreement, or present merged data
as one authority. Provider failures stay observable. Licensed knowledge bases
are not scraped or represented as enabled without valid rights and credentials.

## 4. Clinical safety

The gateway supplies reference information, not medical advice. Dose,
interaction, prescribing, dispensing, and reimbursement outputs retain their
limitations and should be verified by qualified professionals and approved
clinical systems. Tests use synthetic data and mock external integrations by
default.

## 5. Least privilege and privacy

Credentials are server-side secrets, never tool arguments. Hospital access is
read-only by default. Patient-scoped queries require explicit authorized
context. File, SQL, vector, and web integrations use operator-controlled
allowlists and bounded egress. Production authorization, consent, audit,
retention, and regulatory controls remain deployment responsibilities.

## 6. Layered architecture

Domain defines contracts and pure rules; application owns use cases;
infrastructure performs I/O behind domain ports; presentation owns transports
and rendering. Dependencies point inward and source-specific behavior does not
leak into MCP handlers.

## 7. Reproducible maintenance

Use uv and a committed lockfile. Keep default tests deterministic. Important
work is delivered in reviewable Conventional Commits with matching README/docs,
changelog, and Memory Bank updates. CI and the documentation site must build
from a clean checkout.

Adopted 2025-12-22; modernized for the v0.9 gateway on 2026-07-20.
