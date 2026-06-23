# Evaluation Datasets

This directory contains evaluation datasets for testing agent behavior.

## Running Evaluations

### Default Dataset
```bash
# 1. Upload smoke PNG once (Agent Runtime vision needs gs://, not inline base64)
export GCS_BUCKET=medication-companion-uploads
gsutil cp data/sample/smoke_4drug_2interactions.png \
  gs://${GCS_BUCKET}/eval/smoke_4drug_2interactions.png

# 2. Rebuild dataset with file_data URI (after changing the PNG or prompt text)
uv run python scripts/build_smoke_eval_dataset.py \
  --gcs-uri gs://${GCS_BUCKET}/eval/smoke_4drug_2interactions.png

# 3. Generate traces, then grade with our custom metrics
export GOOGLE_CLOUD_PROJECT=medication-companion-dev
agents-cli eval generate --dataset tests/eval/datasets/basic-dataset.json
agents-cli eval grade --config tests/eval/eval_config.yaml

# Or one-shot (uses tests/eval/eval_config.yaml when --config is passed):
agents-cli eval run --config tests/eval/eval_config.yaml
```

**Why gs://?** Production and `agents-cli run --file` send images as GCS URIs. Eval datasets
with `inline_data` often fail on deployed Runtime — Agent 1 reports "image not transmitted"
and `drug_safety_score` on the smoke case drops to 0. See `scripts/build_smoke_eval_dataset.py`.

**When `eval generate` still cannot read the smoke image** (even with `file_data` gs://), use
the production Runtime path and grade that trace instead (see
[smoke_test_cheatsheet.md Step 2a](../../docs/smoke_test_cheatsheet.md#step-2--custom-metrics-eval-drug_safety_score-patient_clarity_score)):

```bash
uv run python scripts/run_vision_eval_trace.py --skip-upload --grade
# grades artifacts/traces/vision_eval_<timestamp>.json only — not the whole traces/ folder
```

Smoke pass: `drug_safety_score` ≥ 8 when the trace shows 3 dataset interactions
(`aspirin+nimesulide`, `aspirin+warfarin`, `metronidazole+warfarin`). The rubric grades
only `check_prescription_interactions` output — not external pharmacology.

**Verify step 1 (dataset only, no Gemini):**
```bash
uv run python scripts/build_smoke_eval_dataset.py
python3 -c "
import json
d=json.load(open('tests/eval/datasets/basic-dataset.json'))
ids=[c['eval_case_id'] for c in d['eval_cases']]
assert 'smoke_4drug_2interactions' in ids
print('OK:', ids)
"
```

**Verify step 1 (full eval against deployed Runtime):**
```bash
export GCP_PROJECT=medication-companion-dev
export GOOGLE_CLOUD_PROJECT=$GCP_PROJECT
agents-cli eval generate --dataset tests/eval/datasets/basic-dataset.json
agents-cli eval grade --config tests/eval/eval_config.yaml
open artifacts/grade_results/results_*.html   # macOS
```
Graded traces land in `artifacts/grade_results/`; Agent Platform **Evaluation → Experiments** updates after `generate`/`grade`, not after `agents-cli run` smoke tests.

### Custom Dataset
```bash
# Generate traces for a custom dataset
agents-cli eval generate --dataset tests/eval/datasets/custom-dataset.json --output custom_traces/
agents-cli eval grade --metrics general_quality --traces custom_traces/
```

## Dataset Format

Each dataset file follows the Gemini Enterprise Agent Platform Evaluation
dataset format. An eval case may use **either** of two shapes — both are
valid input to `agents-cli eval generate`:

**Shape A — single-prompt case:**

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "prompt": {
        "role": "user",
        "parts": [{"text": "User message"}]
      }
    }
  ]
}
```

**Shape B — continued-conversation case (the "N+1" pattern):**
The case carries prior turns in `agent_data` and the last turn ends with a
user message; `eval generate` appends the next agent response.

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "agent_data": {
        "turns": [
          {
            "turn_index": 0,
            "events": [
              {"author": "user",  "content": {"role": "user",  "parts": [{"text": "First user message"}]}},
              {"author": "agent", "content": {"role": "model", "parts": [{"text": "First agent reply"}]}},
              {"author": "user",  "content": {"role": "user",  "parts": [{"text": "Follow-up user message"}]}}
            ]
          }
        ]
      }
    }
  ]
}
```

## Key Fields

- `eval_cases`: Array of evaluation cases.
- `eval_case_id`: Unique identifier for the evaluation case (optional).
- `prompt`: A single user message — Shape A.
- `agent_data.turns`: Prior conversation turns ending with a user message — Shape B.

## Creating Custom Datasets

You can create custom datasets in two ways:

1. **By Hand**: Copy `basic-dataset.json` as a template and manually add evaluation cases.
2. **Synthesize**: Use the synthetic dataset generation command to generate conversation scenarios:
   ```bash
   agents-cli eval dataset synthesize --count 10
   ```

## Discovering Metrics

You can discover available out-of-the-box evaluation metrics by running:

```bash
agents-cli eval metric list
```

## Beyond Generate and Grade

Once you have a baseline, the eval surface has a few more commands worth knowing about:

- `agents-cli eval compare BASE CAND` — diff two grade-results files (regression check).
- `agents-cli eval analyze RESULTS` — cluster failure modes from a grade-results file.
- `agents-cli eval optimize` — auto-tune your agent's prompts using eval data.

See the [Evaluation Guide](https://google.github.io/agents-cli/guide/evaluation/) for the full surface and metric reference.
