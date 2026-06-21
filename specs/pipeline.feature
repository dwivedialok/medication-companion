# Medication Companion — core pipeline BDD scenarios
# Maps to: backend/agent.py SequentialAgent (A1 → A2 → A3 → A4 → A5)
# Tests: tests/integration/test_agent.py, tests/unit/test_pipeline_output.py
#
# Generative outcomes (translation fidelity, tone, explanation quality) are NOT verified
# by binary pytest string matches. See specs/schemas/evaluation_metrics.yaml — scored
# async via LLM-as-Judge (translation_accuracy_score, tone_calibration_score, etc.).

Feature: Prescription processing pipeline
  As a patient in India
  I want my prescription image analysed safely across visits
  So that I understand interactions without receiving a diagnosis

  Background:
    Given the auth broker has verified a Firebase JWT and derived patient_id from the UID
    And the client has uploaded a prescription image to GCS and sent the gs:// URI
    And the target language is selected in the Flutter UI

  Scenario: Severe cross-visit drug interaction detected
    Given patient memory contains visit "2025-11-01" with resolved_drugs ["warfarin"] and severity_summary "MODERATE"
    And the prescription image contains brand name "Ecosprin" legible at confidence >= 0.75
    When Agent 1 (prescription_reader) extracts the drug and sets status "ok"
    And Agent 2 (medication_resolver) resolves "Ecosprin" to generic "aspirin" with tag "NEW"
    And Agent 3 (medication_safety) calls interaction_lookup("aspirin", "warfarin")
    Then the interaction severity is "HIGH" with source "cross_visit"
    And Agent 4 (patient_education) produces a summary with urgent-but-calm tone
    And the summary ends with "Please discuss this with your doctor or pharmacist before making any changes."
    And Agent 5 (localisation_audio) produces translated_text in the target language
    And translation fidelity is evaluated by LLM-as-judge translation_accuracy_score not by exact string match
    And memory is updated with the new visit after Agent 4 completes

  Scenario: Benign multi-drug prescription with no significant interactions
    Given patient memory is empty
    And the prescription image lists "Crocin" and "Azithral" at confidence >= 0.75
    When the pipeline runs Agents 1 through 5
    Then Agent 2 tags both drugs as "NEW" with resolved generics
    And Agent 3 reports overall_severity "NONE" or "INFO" only
    And Agent 4 produces drug_cards and a neutral summary with the mandatory disclaimer
    And Agent 5 returns translated_text and a signed audio_url

  Scenario: Unresolved brand name is surfaced, not hallucinated
    Given patient memory is empty
    And the prescription image contains brand name "Xyzol999" at confidence >= 0.75
    When Agent 2 calls drug_lookup and combo_splitter without a match
    Then the drug is tagged "UNRESOLVED" with unresolved_count >= 1
    And Agent 3 does not invent interactions for the unresolved generic
    And Agent 4 mentions the unresolved drug honestly without guessing an equivalent
    And the patient-facing output ends with the consult-your-doctor redirect

  Scenario: Gate 1 rejects unreadable prescription image
    Given the prescription image is blurry or contains no legible drug names
    When Agent 1 assigns confidence below 0.75 for all drug names
    Then Agent 1 sets status "gate1_reject" with a Gate1Reject reason
    And Agents 2 through 5 do not run
    And the client receives a retake-photo message ending with a consult redirect

  Scenario: Localisation handoff preserves disclaimer and severity tone
    Given Agent 4 produced an EducationOutput with overall_severity "HIGH"
    And the user selected target_language "hi-IN"
    When Agent 5 receives the English explanation and severity context
    Then Agent 5 produces translated_text in Hindi
    And the Hindi text includes the consult-your-doctor disclaimer from language_map.yaml
    And Agent 5 calls text_to_speech with language_code "hi-IN"
    And the response includes audio_url and language_code "hi-IN"
    And translation_accuracy_score from LLM-as-judge is at least 8 out of 10 versus the English source
    And tone_calibration_score reflects HIGH severity as urgent but calm per language_map.yaml
