# Care Plan Generator — Design Document

**Version**: v0.1  
**Date**: 2026-02-22  
**Client**: CVS Specialty Pharmacy  

---

## 1. Project Background

CVS pharmacists currently spend 20–40 minutes manually authoring a Care Plan for each patient. This is both a compliance requirement and a prerequisite for reimbursement from Medicare and pharmaceutical companies. Due to severe understaffing, the team is significantly backlogged on this task.

This system is intended exclusively for **CVS internal clinical staff** (medical assistants, pharmacists). Patients do not interact with the system. Once a Care Plan is generated, staff print it and hand it to the patient.

---

## 2. Core Business Rules

### 2.1 Care Plan & Order Relationship

- One Care Plan corresponds to one order (one medication).
- Every Care Plan must contain the following four sections:
  - **Problem List** (Drug Therapy Problems)
  - **Goals** (SMART goals)
  - **Pharmacist Interventions**
  - **Monitoring Plan** (lab schedule and follow-up)

### 2.2 Duplicate Detection Rules

| Scenario | Behavior | Rationale |
|----------|----------|-----------|
| Same patient + same medication + same date | ❌ ERROR — hard block, cannot proceed | Definitive duplicate submission |
| Same patient + same medication + different date | ⚠️ WARNING — can proceed after confirmation | Likely a refill |
| Same MRN + different name or DOB | ⚠️ WARNING — can proceed after confirmation | Possible data entry error |
| Same name + same DOB + different MRN | ⚠️ WARNING — can proceed after confirmation | Possibly the same person |
| Same NPI + different Provider name | ❌ ERROR — must be corrected before submitting | NPI is the authoritative unique identifier |

**Behavior Definitions**:
- **ERROR**: Submission is hard-blocked. The user must correct the data before proceeding.
- **WARNING**: An alert is displayed. The user may acknowledge and continue submission.

---

## 3. Functional Requirements

### 3.1 Feature Priority (All MVP — Required)

| Feature | Priority | Notes |
|---------|----------|-------|
| Patient / order duplicate detection | ✅ Required | Must not disrupt existing workflow |
| Care Plan generation | ✅ Required | Core value of the system |
| Provider duplicate detection | ✅ Required | Affects accuracy of pharma reports |
| Care Plan download | ✅ Required | Staff need to print or upload to their system |
| Pharma export report | ✅ Required | Required for pharma reimbursement |

### 3.2 Web Form Input Fields

| Field | Type | Validation Rules |
|-------|------|-----------------|
| Patient First Name | string | Required, non-empty |
| Patient Last Name | string | Required, non-empty |
| Patient MRN | string | Required, unique, 6-digit number with leading zeros *(digit count TBD — see open questions)* |
| Patient DOB | date | Required, format YYYY-MM-DD, must not be a future date |
| Referring Provider | string | Required, non-empty |
| Referring Provider NPI | string | Required, exactly 10 digits, unique per Provider name in the system |
| Primary Diagnosis | string | Required, must pass ICD-10 format check (e.g. `G70.01`) |
| Medication Name | string | Required, non-empty |
| Additional Diagnoses | list of strings | Optional; each item must pass ICD-10 format check |
| Medication History | list of strings | Optional |
| Patient Records | string or PDF | Required; PDF content must be extracted before being passed to the LLM |

### 3.3 Care Plan Generation

- On form submission, the backend calls an LLM (e.g. OpenAI / Anthropic API) to generate the Care Plan.
- **LLM input**: all form fields + extracted Patient Records text.
- **LLM output**: structured text containing the four required sections.
- Once generated, the user can download the Care Plan as a file (format TBD: plain text / Markdown / PDF).
- The Care Plan is archived and linked to its corresponding order.

### 3.4 Pharma Export Report

- The system must support exporting order data for pharmaceutical company reporting and reimbursement.
- Export format TBD (CSV / PDF / pharma-specific template) — requires further confirmation with the client.

---

## 4. Data Model (Draft)

```
Provider
├── id (PK)
├── name
├── npi (unique, 10-digit)
└── created_at

Patient
├── id (PK)
├── mrn (unique)
├── first_name
├── last_name
├── dob
└── created_at

Order
├── id (PK)
├── patient_id (FK → Patient)
├── provider_id (FK → Provider)
├── medication_name
├── primary_diagnosis (ICD-10)
├── additional_diagnoses (JSON array)
├── medication_history (JSON array)
├── patient_records_text (text)
├── order_date
└── created_at

CarePlan
├── id (PK)
├── order_id (FK → Order, unique)
├── content (text / structured JSON)
├── generated_at
└── downloaded_at (nullable)
```

---

## 5. System Architecture (Draft)

```
[Web Form UI]
     │  Form submission
     ▼
[Backend API]
     ├── Validation layer (field formats, ICD-10, NPI)
     ├── Duplicate detection layer (ERROR / WARNING logic)
     ├── Provider deduplication logic
     ├── Order persistence (DB)
     └── LLM integration layer
          │  Care Plan generation
          ▼
     [Care Plan archive + download endpoint]
          │
          ▼
     [Pharma export endpoint]
```

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Validation | Every input field must be validated; error messages must be clear, safe, and must not expose internal system details |
| Data Integrity | Integrity rules enforced at the database level (unique constraints, foreign keys) |
| Modularity | Validation, duplicate detection, LLM integration, and export must be implemented as independent modules |
| Testability | Duplicate detection logic, validation logic, and Care Plan structure checks must be covered by automated tests |
| Ease of Deployment | Project must support one-command startup (e.g. `docker-compose up`), runnable out of the box |
| Compliance | Data includes PHI; HIPAA compliance requirements must be assessed, especially regarding transmission of patient data to third-party LLM APIs |

---

## 7. Open Questions

The following items require final confirmation from the client before development begins:

1. **MRN digit count**: The requirements document states 6 digits, but the sample data shows 8 digits (`00012345`). Which is correct?
2. **Care Plan download format**: Plain text, Markdown, or PDF?
3. **Pharma export format**: CSV, PDF, or a pharma-specific template? Do different pharma companies require different formats?
4. **HIPAA / data compliance**: Is it permissible to send patient PHI to a third-party LLM API? If not, does the solution require a private deployment or a BAA-covered service?
5. **Pharmacist review workflow**: After a Care Plan is generated, does a pharmacist need to review and sign off before it can be archived and downloaded?
6. **Multiple Care Plans per patient**: Can a single patient have multiple historical Care Plans (e.g. different medications or different dates)?

---

*This document will be updated as requirements are confirmed.*