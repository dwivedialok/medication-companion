# Technical Specification: Medication Resolver & Reconciliation Engine

## 1. System Overview

This document outlines the architecture and implementation details for upgrading the Medication Resolver (Agent 2) and the Medication Reconciliation Agent (Agent 3) within the Medication Companion multi-agent system.

The core upgrade replaces static CSV lookups with an embedded, serverless vector database (**LanceDB**). This approach utilizes semantic search to map OCR-extracted Indian brand names to their generic compositions, dynamically handling handwriting transcription errors (e.g., extracting "Azee5O0" instead of "Azee 500"). Furthermore, it introduces a unified data schema that surfaces known drug interactions to power longitudinal continuity checks.

---

## 2. Data Strategy & Schema Pipeline

To achieve production-grade accuracy and comprehensive interaction data, the system will fuse two distinct datasets prior to database ingestion.

### 2.1 Dataset Fusion Strategy

1. **Primary Index (Coverage):** The *All India Drug Bank Database* ($\sim$250,000 rows) serves as the primary base, providing expansive coverage of `Brand Name`, `Generic Composition`, and `Manufacturer`.
2. **Enrichment Layer (Interactions):** The *Indian Medicine Data* dataset provides the critical `drug_interactions` and `side_effects` columns.
3. **The Join:** A preprocessing script will map the `Generic Composition` from the primary index to the interaction data in the enrichment layer, creating a unified JSON/Parquet payload for ingestion.

### 2.2 LanceDB Schema Definition

The database utilizes `pydantic` to enforce strict schema validation.

```python
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry

# Initialize local embedding model optimized for semantic text matching
func = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")

class IndianMedicineSchema(LanceModel):
    # The vector representation of the brand name
    vector: Vector(func.ndims()) = func.VectorField()
    brand_name: str = func.TextField()
    generic_composition: str
    manufacturer: str
    known_interactions: str  # Extracted from the enrichment dataset
    drug_type: str           # e.g., Allopathic, Ayurvedic

```

---

## 3. Tool Specification: Agent 2 (Medication Resolver)

Agent 2 relies on an external tool to query the LanceDB vector store. This tool must abstract the database logic and return a strictly formatted JSON payload.

### 3.1 Function Signature & Logic

```python
import lancedb

def resolve_medication(ocr_extracted_text: str, similarity_threshold: float = 0.85) -> dict:
    """
    Searches the local LanceDB index for the closest matching drug brand.
    
    Args:
        ocr_extracted_text (str): The raw string extracted by Agent 1.
        similarity_threshold (float): The maximum allowed L2 distance for a valid match.
    """
    db = lancedb.connect(".lancedb")
    table = db.open_table("indian_medicines")
    
    # Execute semantic vector search
    results = table.search(ocr_extracted_text).limit(3).to_pandas()
    
    if results.empty:
        return {"status": "UNKNOWN", "message": "No registry match found."}
    
    best_match = results.iloc[0]
    distance = float(best_match['_distance'])
    
    # Guardrail against hallucinated/wild matches
    if distance > similarity_threshold:
        return {"status": "UNKNOWN", "message": "Match confidence too low."}
        
    return {
        "status": "SUCCESS",
        "brand_name": best_match['brand_name'],
        "generic_composition": best_match['generic_composition'],
        "known_interactions": best_match['known_interactions'],
        "confidence_score": round((1.0 - distance), 2)
    }

```

### 3.2 Output Handling & Agent Handoff

Agent 2 parses the tool's output and updates the session's JSON state. If the status is `SUCCESS`, it appends the `generic_composition` and `known_interactions`. If `UNKNOWN`, it flags the item so downstream agents do not attempt dangerous clinical comparisons.

---

## 4. Conflict Resolution Logic: Agent 3 (Reconciliation)

Agent 3 operates entirely on the structured output of Agent 2 and the hydrated Longitudinal Memory Layer (historical visit data).

### 4.1 Evaluation Vectors

Agent 3 performs two distinct evaluation passes:

1. **Intra-Prescription (NEW vs NEW):** * Iterates through all newly uploaded medications.
* Cross-references the `generic_composition` of Drug A against the `known_interactions` text block of Drug B.
* *Goal:* Detect FDC (Fixed-Dose Combination) overlaps or immediate contraindications prescribed during the current visit.


2. **Longitudinal (NEW vs EXISTING):**
* Retrieves active medications from the memory layer.
* Compares new generic compositions against existing active compositions.
* *Goal:* Detect duplications (e.g., patient prescribed a new generic by a specialist while already taking a different brand of the same generic from a GP).



### 4.2 Interaction Prompting Strategy

Agent 3 is strictly bound by non-diagnostic language. It synthesizes the data hits into structured flags for Agent 4 (Patient Education).

**Input to Agent 3 (Example):**

> *New:* Azithromycin (Antibiotic)
> *Existing:* Metoprolol XR (Beta-blocker)
> *DB Interaction Hit:* Azithromycin may interact with certain heart rate controlling medications.

**Expected Agent 3 Structured Output Payload:**

```json
{
  "reconciliation_flags": [
    {
      "severity": "Informational",
      "flag_type": "Potential Interaction",
      "involved_drugs": ["Azithromycin", "Metoprolol XR"],
      "context": "The database notes that Azithromycin has known interactions with beta-blockers. Since the patient has a historical prescription for Metoprolol XR, this overlap requires verification.",
      "action_directive": "Draft a question for the doctor regarding the concurrent use of these two medications."
    }
  ]
}

```

---

## 5. Fallback & Edge Case Architecture

To ensure system resilience in a production environment, the database integration must gracefully handle inevitable data gaps.

### 5.1 The Ayurvedic / Alternative Medicine Edge Case

Many Indian prescriptions feature a mix of allopathic and homeopathic/ayurvedic remedies (e.g., *Liv.52* alongside *Pantocid*).

* **System Action:** If LanceDB matches an ayurvedic compound, the `generic_composition` field will often be a list of herbs. Agent 3 must be programmed to categorize these as `Needs Clarification` rather than attempting a chemical interaction check, prompting the patient to mention the herbal supplement explicitly to their allopathic doctor.

### 5.2 Zero-Hit Isolation (`UNKNOWN` State)

When LanceDB returns an `UNKNOWN` status (due to a completely illegible OCR string or a brand-new market drug not yet in the Kaggle dataset), the system must isolate the failure to protect the integrity of the reconciliation process.

* **System Action:** Agent 3 bypasses the interaction loop for the `UNKNOWN` string.
* **Downstream Routing:** Agent 4 is forced by its system prompt to prioritize this unknown item, generating a primary fallback instruction: *"We could not verify the composition of [String]. Please confirm its exact ingredients with your pharmacist before taking it with your other medications."*