# NRTaxAI: Agentic AI Tax Preparer (Non-Resident) — System Design & Architecture

### Scope

- Conversational assistant for non-resident taxpayers (H1B, F‑1, O‑1, OPT, J‑1, TN, E‑2, etc.).
- Intake chat + document uploads; OCR extraction; deterministic validation; tax rules engine; human-in-the-loop (HITL); PDF generation (1040NR, W‑8BEN, 8843, 1040‑V); e‑file later. PTIN(Preparer Tax Identification Number)
- Frontend: React + Material UI. Backend: FastAPI (Python). Infra: AWS (RDS Postgres, S3, Textract, ECS/Lambda, SQS, CloudWatch, KMS, Secrets Manager, ElastiCache Redis).

### Architecture (High Level)

### Diagram Suite (ASCII + Mermaid-style)

#### 1) Context Overview

```
+-----------------+        +--------------------+        +-------------------------------+
|     End User    | -----> |  CloudFront + WAF  | -----> |  ALB / API Gateway (Routing)  |
+-----------------+        +--------------------+        +-------------------------------+
                                                             |
                                                             v
                                                +-----------------------------+
                                                |  FastAPI API (ECS Fargate) |
                                                +-----------------------------+
                                                             |
         +----------------------+        +-------------------+---------------------+        +-------------------+
         | React Web (MUI) UI  |<------>|      S3 (Static Assets & Uploads)       |<------>|  Route 53 DNS     |
         +----------------------+        +-----------------------------------------+        +-------------------+
```

#### 2) Core Services & Data Stores

```
+-------------------------------+                 +------------------------------+
|  FastAPI API Service          |  tool calls --> |  OpenAI Chat (LLM)           |
|  - Auth, Users, Chat, Docs    |                 +------------------------------+
|  - Rules, Validation, Forms   |
+-------------------+-----------+
                    |
                    | enqueue jobs
                    v
            +---------------+           poll/cb           +-------------------+
            |   SQS Queues  | --------------------------> |  Async Workers    |
            | (OCR, Rules,  |                             | (OCR/Rules/PDF/AV)|
            |  PDF, AV)     | <-------------------------- |                   |
            +-------+-------+         results/status      +---------+---------+
                    |                                              |
                    |                                              |
          +---------v----------+                           +-------v---------+
          |   RDS Postgres     |<--------------------------|  S3 Buckets     |
          |  (ACID data)       |        store metadata     | (Uploads/PDFs)  |
          +---------+----------+                           +-----------------+
                    |
                    v
              +-----------+     metrics/logs     +-------------------+
              |  Redis    | <------------------- | CloudWatch / OTel |
              +-----------+                      +-------------------+
```

#### 3) Deployment Topology

```
                +-------------------+      +-------------------+
Internet  --->  | CloudFront (CDN)  | ---> |  AWS WAF (Rules)  |
                +-------------------+      +-------------------+
                               |                  
                               v                  
                           +--------+              
                           |  ALB   | ---------------> +-----------------------------------+
                           +--------+                 | ECS Service: FastAPI (Fargate)     |
                               |                      +-----------------------------------+
                               |                              |
                               |                              v
                               |                        +-----------+
                               |                        |  SQS/DLQ |
                               |                        +-----+-----+
                               |                              |
                               |                     +--------v---------+
                               |                     | ECS Workers/Lmbd |
                               |                     +--------+---------+
                               |                              |
             +-----------------v---------------+     +--------v---------+      +-----------------+
             |   RDS Postgres (Multi-AZ)       |     |   S3 (Docs/PDFs) |      | ElastiCache     |
             +---------------------------------+     +-------------------+      +-----------------+
                          |                                |                         
                          v                                v                         
                    +-----------+                    +------------+            +------------------+
                    |   KMS     |                    |  Secrets   |            | CloudWatch/OTel  |
                    +-----------+                    |  Manager   |            +------------------+
                                                     +------------+
```

#### 4) Document Intake → OCR → Validation (Swimlane)

```
User      UI (React)       API (FastAPI)        S3            SQS         Worker         Textract         DB
 |            |                 |                |             |             |              |             |
 | Upload --> | presign URL --> |                |             |             |              |             |
 | PUT file   | --------------> |                |  PUT obj    |             |              |             |
 |            |                 |                | ----------> | enqueue job |              |             |
 |            |     poll status |                |             | --------->  | start job -->|             |
 |            | <-------------- |                |             |             | <--- results |             |
 |            |                 |                |             |             | normalize -> | insert rows |
 |            |                 |                |             |             | validate  -> | validations |
 |            |  status/result  |                |             |             | update ----> | extracted   |
```

#### 5) Chat with Tool Calls

```
React UI --> FastAPI /chat --> OpenAI Chat
                         \-> Rules Engine (deterministic)
                         \-> DB (fetch context)
                         \-> S3 (doc links)
Return streaming message -> UI
```

#### 6) HITL Review & Authorization

```
+------------------+      +---------------------+      +--------------------------+
| Operator (PTIN)  | ---> | Admin Frontend (UI) | ---> | FastAPI Review Endpoints |
+------------------+      +---------------------+      +------------+-------------+
                                                           |  approve/reject
                                                           v
                                                +-----------------------+
                                                | Immutable Audit Logs  |
                                                +-----------------------+
                                                           |
                                                           v
                                                +-----------------------+
                                                | PDF Generation Queue  |
                                                +-----------------------+
```

#### 7) Security & Compliance Controls Map

```
[Edge]
  - CloudFront + WAF (rate limit, IP block, bot ctl)
[Transport]
  - TLS 1.2+, HSTS
[App]
  - JWT + refresh + optional TOTP; RBAC; CSRF on uploads
[Data]
  - KMS envelope encryption; S3 Object Lock; RDS backups/PITR
[Ops]
  - Least-privilege IAM; Secrets Manager; CloudWatch Alarms; IR playbooks
[Audit]
  - Hash-chained logs; export bundles; access recertification
```

#### 8) Forms Generation Pipeline

```
Rules Output ---> PDF Service -----> Fill 1040NR/8843/W-8BEN/1040-V -----> S3 (versioned)
      |                 |                      |                                   |
      +-> Cross-checks  +-> Metadata (hash)    +-> Failure -> DLQ                  +-> Links to user
```

#### 9) Future: E-file Integration Staging (placeholder)

```
PDFs + Metadata -> E-file Adapter -> Conformance Validator -> IRS MeF (later phase)
```

#### Context (C4 Level 1)

```
[End User]
   |
   v
[Web App: React + MUI]
   |
   v
[CloudFront + WAF] -> [ALB/API Gateway] -> [FastAPI API Service (ECS Fargate)]
                                                |\
                                                | \-> [SQS + DLQ] -> [Async Workers (ECS Fargate/Lambda)]
                                                |              |           |-> Textract (OCR)
                                                |              |           |-> PDF Generator
                                                |              |           |-> Validation & Rules
                                                |              v
                                                |          [EventBridge]
                                                | 
                                                |-> [RDS Postgres]
                                                |-> [ElastiCache Redis]
                                                |-> [S3: Uploads, Extracts, PDFs]
                                                |-> [OpenAI API]
                                                |-> [KMS, Secrets Manager]
                                                |-> [CloudWatch Logs & Metrics]
```

#### Containers (C4 Level 2)

- Web Client (React + MUI)
                - Auth screens, chat widget/modal, uploader, return summary, forms download, operator console
- API Service (FastAPI on ECS)
                - Modules: auth, users, documents, extraction, validation, rules, chat, forms, review, audit, admin
                - Responsibilities: request authN/Z, orchestration, persistence, presigned URLs, audit logging
- Async Workers (ECS Fargate or Lambda)
                - Jobs: Textract OCR, canonical mapping, validation, rules compute, PDF rendering, AV scan
                - Triggered via SQS; idempotent, retry with DLQ
- Data Stores & External Services
                - RDS Postgres (primary DB), Redis (cache/session), S3 (docs/PDFs), Textract (OCR), OpenAI API (chat), KMS/Secrets, CloudWatch, EventBridge

#### Deployment (C4 Level 3)

```
[Route 53]
   -> [CloudFront CDN]
       -> [AWS WAF]
           -> [ALB]
               -> [ECS Service: fastapi-web (Fargate, private subnets)]
               -> [ECS Service: workers (Fargate) / Lambda for batch]

[VPC]
  - Private Subnets: ECS tasks, RDS (Multi-AZ), ElastiCache Redis
  - Public Subnets: ALB, NAT Gateways
  - Security Groups: least-privilege between tiers

[Data Plane]
  - RDS Postgres (Multi-AZ, backups/PITR)
  - S3 (uploads, extracted JSON, PDFs) with Object Lock for audit bundles
  - SQS Queues (+ DLQ) for asynchronous jobs
  - EventBridge for domain events
  - KMS CMKs for envelope encryption; Secrets Manager for credentials
  - CloudWatch Logs, Metrics, Alarms; OpenTelemetry traces
```

#### Core Sequence Flows

- Document Upload → OCR → Validation
```
Web -> API: request presigned URL (doc type)
Web -> S3: PUT document
S3 -> EventBridge: ObjectCreated event
API/Worker -> Textract: start job
Textract -> Worker (poll/callback): results
Worker: map to canonical schema, run validators (SSN/ITIN, totals, thresholds)
Worker -> DB: store extracted_json, validation_json; emit events; enqueue follow-ups if needed
API -> Web: status/result endpoints reflect progress
```

- Chat with Tool Calls (RAG + Rules)
```
Web -> API: POST /chat/message
API -> OpenAI: chat with function/tool schema
OpenAI -> API: tool call (e.g., fetch missing fields, compute residency)
API -> Rules/DB: perform deterministic computations
API -> OpenAI: function results to finalize response
API -> Web: streaming answer + next steps
```

- Tax Compute → HITL Review → PDF Generation
```
API -> Worker: compute tax (ruleset versioned)
Worker -> DB: computations, summaries
Operator Web -> API: review queue & diffs, add comments
Operator -> API: approve/reject; API records immutable audit log
API -> Worker: generate PDFs (1040NR, 8843, W-8BEN, 1040-V)
Worker -> S3: store PDFs; update forms table with checksum & metadata
Web -> API: download links (authorized)
```


### Key Components

- Chat Orchestrator: Routes user prompts; supports tool calls to: document intake, extraction, rules calculations, checklist generation, status
- Document Intake Service: Upload → S3 → Textract → normalized JSON → deterministic validators
- Tax Rules Engine: Pure code (no LLM) for residency tests, treaty articles, income sourcing, credits, withholdings, state rules; versioned rules; full unit tests
- HITL Review Console: Admin app for PTIN/EFIN operators to approve, annotate, and e‑sign (Form 8879 equivalent) before release
- PDF Generation Service: Templates for 1040NR, W‑8BEN, 8843, 1040‑V with deterministic population, cross-field checks
- Audit/Explainability: Immutable logs, decision traces, data lineage across steps; exportable audit bundle

### Data Flow

1) User registers/authenticates (JWT)

2) Upload W‑2/1099/1098‑T → S3; job enqueued → Textract → field normalization → validation

3) Chat intents drive intake, missing fields, and clarifications via RAG to curated IRS guidance

4) Rules engine computes residency, treaty application, tax; discrepancies flagged for HITL

5) Operator reviews, requests changes; user authorizes; PDFs generated; ready for file (later e‑file)

### APIs (FastAPI)

- Auth
- POST `/auth/register` — email/password + TOTP opt-in
- POST `/auth/login` — returns JWT
- POST `/auth/refresh`
- POST `/auth/verify-email`
- POST `/auth/setup-mfa` / `/auth/verify-mfa`
- User & Profile
- GET `/users/me`
- PUT `/users/me` — demographics, visa class, presence days, country of residence
- Documents
- POST `/documents/upload` — pre-signed URL; metadata (type: W2, 1099INT, 1099NEC, 1098T)
- POST `/documents/ingest/callback` — S3 event/Textract completion webhook
- GET `/documents` — list; GET `/documents/{id}` — details
- Extraction & Validation
- POST `/extraction/{documentId}/start`
- GET `/extraction/{documentId}/result`
- GET `/validation/{returnId}` — validation status & issues
- Chat
- POST `/chat/session` — start session
- POST `/chat/message` — { sessionId, message } → streaming response + tool calls
- GET `/chat/history?sessionId=`
- Tax Engine
- POST `/tax/compute` — { returnId } → computations, line items, schedules
- GET `/tax/{returnId}/summary`
- POST `/tax/what-if` — scenario analysis
- Forms & PDFs
- POST `/forms/{returnId}/generate` — 1040NR, W‑8BEN, 8843, 1040‑V
- GET `/forms/{returnId}/download?form=1040NR`
- Review & Authorization (HITL)
- GET `/review/queue` — operator view
- GET `/review/{returnId}` — diffs, evidence, comments
- POST `/review/{returnId}/decision` — approve/reject with reason
- POST `/authorization/{returnId}/request` — user e-sign request (8879-like)
- POST `/authorization/{returnId}/confirm` — user confirmation
- Admin/Rules
- GET `/admin/rulesets` — versioned list
- POST `/admin/rulesets` — publish new ruleset (feature-flagged)
- Audit & Logs
- GET `/audit/{returnId}` — export audit bundle (admin)

### Database Schema (PostgreSQL)

- users(id, email, password_hash, mfa_enabled, created_at)
- user_profiles(user_id FK, first_name, last_name, dob, residency_country, visa_class, itin, ssn_last4, address_json, phone)
- chat_sessions(id, user_id, status, created_at)
- chat_messages(id, session_id, role, content, tool_calls_json, created_at)
- tax_returns(id, user_id, tax_year, status, ruleset_version, residency_result_json, treaty_json, totals_json, created_at, updated_at)
- documents(id, user_id, return_id, s3_key, doc_type, source, status, textract_job_id, extracted_json, validation_json, created_at)
- validations(id, return_id, severity, field, code, message, data_path, created_at)
- computations(id, return_id, line_code, description, amount, source, created_at)
- forms(id, return_id, form_type, s3_key_pdf, status, checksum, created_at)
- reviews(id, return_id, operator_id, decision, comments, diffs_json, created_at)
- authorizations(id, return_id, method, status, signed_at, evidence_json)
- operators(id, email, ptin, roles, status, created_at)
- audit_logs(id, actor_type, actor_id, return_id, action, payload_json, hash, created_at)
- api_keys(id, owner_id, key_hash, scopes, created_at)
- feature_flags(key, value_json, updated_at)

Indexes: email unique; (user_id,tax_year); documents(return_id,doc_type); audit_logs(return_id,created_at desc).

Row-level encryption at app layer for PII (SSN/ITIN) with AWS KMS envelope; field separation where possible.

### Security & Compliance

- Pub 4557 controls: encryption in transit (TLS), encryption at rest (KMS); least-privilege IAM; device/endpoint hardening; incident response runbook
- PII segregation: SSN/ITIN stored encrypted with per-record data keys; rotate keys; secret management via Secrets Manager
- Auth: JWT (short-lived) + refresh tokens; optional TOTP MFA; IP/device risk signals
- Access control: RBAC for operators; data scoping by user/tenant; immutable audit logs with hash chaining
- Secure uploads: pre-signed S3 URLs; AV scanning (Lambda)
- Rate limiting & WAF: API Gateway/ALB + AWS WAF rules
- Backups: RDS automated backups + PITR; S3 versioning + object lock for audit bundles

### OCR/Extraction Strategy

- Primary: AWS Textract (forms + table extraction)
- Normalization: map Textract blocks to canonical schema per document type (W‑2, 1099INT/NEC, 1098‑T)
- Deterministic validation: regex + checksum for SSN/ITIN; numeric tolerances; cross-field reconciliation (sum of boxes, withholding ≤ wages, etc.)
- Confidence thresholds + exception queues to HITL when below threshold

### Tax Rules Engine

- Deterministic, versioned, test-heavy Python package:
- Residency (Substantial Presence Test, exceptions for F‑1/J‑1, treaty tie-breakers)
- Income sourcing rules (wages, interest, NEC, scholarships)
- Treaty benefits by country/article
- Standard deductions/credits rules (as applicable to 1040NR)
- Withholding reconciliation and underpayment/penalties
- Data-driven rule tables (YAML/JSON) compiled into functions; rigorous unit + property tests
- Explainability: capture rationales and inputs per decision for audit

### LLM Usage Policy

- LLM for conversation, guidance, checklisting, summarization; NOT for final calculations or field values
- RAG over curated IRS publications/FAQs (non-resident scope) + internal rules docs
- Guardrails: tool calling only to safe operations; PII redaction in prompts; content filters; refusal for tax “advice” beyond rules
- Training: do not fine-tune on IRS texts initially; prefer RAG. Consider small supervised fine-tunes on support conversation style only (no calculations) after privacy review.

### Frontend (React + MUI)

- App shell with auth flows, secure session storage, CSRF for uploads
- Components: Chat widget/modal, Document uploader with drag‑and‑drop, Document review viewer (extracted fields + confidence), Return summary, Forms download, Operator dashboard
- Accessibility (WCAG AA), responsive design, error boundaries; i18n-ready

### Backend (FastAPI)

- Modular services: auth, documents, extraction, rules, chat, forms, review, audit
- Async I/O (uvicorn + httpx); Pydantic models; dependency injection for security
- Background processing via SQS + workers; idempotent handlers; retries with DLQ

### PDF Generation

- Deterministic population via Jinja2 + AcroForm/FDF or 

programmatic writers (ReportLab/PyPDF)

- Cross-form consistency checks; embedded metadata; hashing & timestamping

### Observability & QA

- Metrics: request latency, extraction confidence, validation failures, review turnaround, compute duration
- Tracing: OpenTelemetry
- Testing: unit (rules >90% coverage), integration (OCR pipelines with fixtures), e2e (Cypress/Playwright), adversarial document set
- Red-teaming for prompt injection, PII exfiltration

### AWS Deployment

- ECS Fargate (FastAPI + workers), RDS Postgres (Multi-AZ), S3 (uploads, PDFs), Textract, SQS + DLQ, ElastiCache Redis, CloudFront + WAF, KMS, Secrets Manager, CloudWatch, EventBridge
- IaC: Terraform
- CI/CD: GitHub Actions

### Data Retention

- Configurable retention; right to deletion; audit bundles retained per legal requirements with object lock

### Milestones

1) Intake MVP: Auth, upload, Textract, normalized extraction, chat

2) Validation + Rules v1, basic PDFs (1040NR, 8843)

3) HITL console, operator workflows, authorization

4) Additional forms (W‑8BEN, 1040‑V), treaty engine

5) Hardening: security, audit exports, adversarial testing

6) E‑file integration (direct IRS or partner)

## Summary System Flow
```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER PREPARES RETURN                                         │
│    - Uploads documents (W-2, 1099s)                             │
│    - AI chat assists with questions                              │
│    - System computes tax liability                               │
│    - Forms generated (1040-NR, 8843, W-8BEN, 1040-V)            │
│    - Status: "review"                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. OPERATOR REVIEW (HITL - Human in the Loop)                   │
│    - Operator receives notification                              │
│    - Reviews all generated forms                                 │
│    - Checks source documents vs. return                          │
│    - Validates tax calculations                                  │
│    - Checks treaty benefits application                          │
│                                                                  │
│    Operator Actions:                                             │
│    a) APPROVE → Status: "approved"                              │
│    b) REQUEST REVISION → Status: "needs_revision" + comments    │
│    c) REJECT → Status: "rejected" + reason                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. AUTHORIZATION (Form 8879)                                     │
│    - System generates Form 8879                                  │
│    - User signs electronically (e-signature, PIN, or phone)     │
│    - Operator signs as preparer (PTIN required)                 │
│    - Status: "authorized"                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. E-FILE SUBMISSION                                             │
│    - System submits to IRS via e-file                           │
│    - IRS acknowledgment received                                 │
│    - Status: "filed"                                             │
└─────────────────────────────────────────────────────────────────┘
```

### What Operators See in Dashboard:

Review Queue:
```
┌────────────────────────────────────────────────────────────────┐
│ Tax Return Review Queue                                        │
├────────────────────────────────────────────────────────────────┤
│ Return ID    │ Taxpayer    │ Year │ Status  │ Assigned        │
│ TR-001       │ John Doe    │ 2024 │ Review  │ CPA Smith       │
│ TR-002       │ Jane Smith  │ 2024 │ Review  │ Unassigned      │
└────────────────────────────────────────────────────────────────┘
```

Individual Return Review Screen:
```
┌────────────────────────────────────────────────────────────────┐
│ Tax Return TR-001 - John Doe (H1B, India)                     │
├────────────────────────────────────────────────────────────────┤
│ TAXPAYER INFO:                                                 │
│ - Name: John Doe                                               │
│ - Visa: H1B                                                    │
│ - Country: India                                               │
│ - Residency: Non-Resident (Substantial Presence Test)         │
│                                                                │
│ SOURCE DOCUMENTS:                                              │
│ ✓ W-2: ABC Company - $80,000 wages                           │
│ ✓ 1099-INT: Bank of America - $250 interest                  │
│                                                                │
│ COMPUTED TAX:                                                  │
│ - US Source Income: $80,250                                   │
│ - Treaty Exemptions: $0 (H1B not eligible)                    │
│ - Taxable Income: $80,250                                     │
│ - Federal Tax: $12,458                                        │
│ - Withheld: $15,000                                           │
│ - Refund Due: $2,542                                          │
│                                                                │
│ GENERATED FORMS:                                               │
│ 📄 1040-NR [Download] [Preview]                               │
│ 📄 8843 [Download] [Preview]                                  │
│                                                                │
│ OPERATOR ACTIONS:                                              │
│ [✓ Approve]  [📝 Request Revision]  [✗ Reject]              │
│                                                                │
│ Comments: ____________________________________________         │
└────────────────────────────────────────────────────────────────┘
```

### Key Points:
1. Operators DON'T review Form 8879 - they review the actual tax returns (1040-NR, etc.)
2. Form 8879 is for authorization - it's generated AFTER operator approval
3. Dual signature required: User signs 8879, then operator signs as preparer
3. PTIN required: Operators must have valid PTIN to sign returns
5. Audit trail: Every review action is logged with operator ID, timestamp, and comments

### Database Flow: (Operator (HITL))

```sql
-- Return submitted for review
UPDATE tax_returns SET status = 'review' WHERE id = :return_id;

-- Operator reviews and approves
INSERT INTO reviews (return_id, operator_id, decision, comments)
VALUES (:return_id, :operator_id, 'approved', 'Reviewed and approved');

UPDATE tax_returns SET status = 'approved' WHERE id = :return_id;

-- Generate Form 8879
INSERT INTO authorizations (return_id, user_id, form_type, status)
VALUES (:return_id, :user_id, '8879', 'pending');

-- User signs Form 8879
UPDATE authorizations SET status = 'user_signed', signature_data = :user_sig WHERE id = :auth_id;

-- Operator signs Form 8879
UPDATE authorizations SET status = 'signed', signature_data = :operator_sig WHERE id = :auth_id;

-- Submit to IRS
UPDATE tax_returns SET status = 'filed' WHERE id = :return_id;
```