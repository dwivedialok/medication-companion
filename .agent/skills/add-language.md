# Skill: Onboard a new Indian language

Workflow for adding a regional language to Agent 5 localisation + TTS.

## When to use

- Flutter language picker needs a new `xx-IN` option
- TTS voice available in GCP Text-to-Speech for that locale

## Steps

1. **Update the language schema** — [specs/schemas/language_map.yaml](../../specs/schemas/language_map.yaml):
   - Add BCP-47 code (e.g. `ml-IN` for Malayalam)
   - Set `tts_voice` from [GCP TTS voice list](https://cloud.google.com/text-to-speech/docs/voices)
   - Add `severity_tone_phrases` for each severity level
   - Add `disclaimer_translation` (must preserve consult-your-doctor meaning)

2. **Register TTS voice** — [backend/tools/tts.py](../../backend/tools/tts.py):
   - Add entry to `_VOICE_MAP`

3. **Update Agent 5 instruction** — [backend/agents/agent5_localisation.py](../../backend/agents/agent5_localisation.py):
   - List the new code in supported languages
   - After Step 3: use `[[PATIENT_LANGUAGE]]` / `[[DISCLAIMER]]` via ContextResolver

4. **Update Flutter UI** — language selector in `frontend/lib/`:
   - Add display label and code sent to auth broker `/prescription`

5. **Add tests**
   - `tests/unit/test_tts.py` — voice map contains new code
   - Eval case for translation_accuracy (Step 5 judges) when implemented

6. **Run tests**

   ```bash
   uv run pytest tests/unit/test_tts.py tests/unit/test_pipeline_output.py
   ```

## Quality bar

- Translated disclaimer must appear verbatim in meaning, not word-for-word English
- Agent 5 must not add or remove clinical content during translation
- Default fallback remains `en-IN` when language is unknown

## Do not

- Store translated text in long-term memory (memory holds generic names only)
- Use diagnostic or dosing language in tone phrase templates
