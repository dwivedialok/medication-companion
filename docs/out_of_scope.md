# Out of Scope — Medication Companion

Judges value clear scope decisions. This document states explicitly what is NOT in this capstone,
and why each exclusion is a deliberate engineering decision rather than an oversight.

---

## Explicitly excluded

### Clinical interaction database
**Excluded:** No DrugBank, OpenFDA adverse event data, or structured pharmacological database.  
**Why:** LLM pharmacological knowledge (Gemini) is sufficient for a POC. Production would integrate DrugBank or similar. Using a structured DB would add 2-3 days of data pipeline work with diminishing returns for demonstrating agent capabilities.

### Image pre-processing / OCR enhancement
**Excluded:** No deskewing, contrast enhancement, or binarisation pipeline before Agent 1.  
**Why:** Gemini Vision handles typical mobile prescription photos adequately. Gate 1 rejection handles the failure case. A full OCR pipeline is a separate product concern.

### Full prescription history storage
**Excluded:** Memory stores drug names + severity summary only — not full prescription images or clinical notes.  
**Why:** Privacy by design. Storing only resolved generic names gives Agent 3 what it needs for cross-visit interaction checking without creating a medical records system.

### Pharmacy / dispensing integration
**Excluded:** No e-prescription, pharmacy API, or drug availability lookup.  
**Why:** This adds regulated commerce scope entirely outside the agent AI demonstration. Out of scope for any POC.

### Doctor-facing interface
**Excluded:** No dashboard, alert system, or report generation for healthcare providers.  
**Why:** The patient is the protagonist. A doctor-facing product is a different product with different regulatory requirements.

### Dose adjustment advice
**Excluded:** The system never suggests changing a dose, timing, or stopping a medication.  
**Why:** This is a hard safety boundary. Any dosing advice crosses into medical practice. The guardrails enforce this.

### Refill reminders / adherence tracking
**Excluded:** No push notifications, refill scheduling, or adherence monitoring.  
**Why:** These features require a persistent background service, notification infrastructure, and regulatory consideration. Entirely separate from the agent safety-checking value proposition.

### Drug pricing / availability
**Excluded:** No pharmacy price lookup or drug availability by location.  
**Why:** Requires commercial data partnerships, not relevant to the safety checking demonstration.

### Clinical trial matching
**Excluded:** No integration with ClinicalTrials.gov or trial eligibility checking.  
**Why:** This is a separate project (see OncFlow). Combining clinical trial matching with prescription safety checking creates an unfocused scope.

---

## What the POC does demonstrate

- 5-agent pipeline with strict single-responsibility boundaries
- Real cross-visit memory (Vertex AI MemoryBankService) enabling interaction checking across visits
- A2A protocol between two independently deployed Cloud Run services
- FunctionTools with real external API calls (RxNav)
- Input/output guardrails as ADK callbacks (not baked into prompts)
- LLM-as-Judge async evaluation writing to BigQuery
- Spec-driven development via `.cursor/rules/` governing all generated code
- Full GCP deployment with automated scripts
- Indian brand name handling with 200+ FDC mappings
