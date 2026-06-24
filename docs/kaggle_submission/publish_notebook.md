# Publish the Kaggle notebook

Follow these steps to publish `notebooks/medication_companion_demo.ipynb` on Kaggle.

## 1. Create a Kaggle dataset (recommended)

1. Zip the repo root **or** upload these paths as a Kaggle dataset:
   - `backend/` (agents, tools, memory, requirements.txt)
   - `data/india_brands.csv`
   - `data/drugs.db`
   - `specs/` (optional, for reference)
2. Title suggestion: **medication-companion-source**
3. Set visibility to **Public**.

## 2. Create a new Kaggle notebook

1. Go to [kaggle.com/code](https://www.kaggle.com/code) → **New Notebook**.
2. **File → Upload Notebook** → select `notebooks/medication_companion_demo.ipynb`.
3. **Add data** → attach your `medication-companion-source` dataset.
4. In the setup cell, set `REPO_ROOT` if needed:

```python
import os
from pathlib import Path
# Kaggle mounts datasets under /kaggle/input/<dataset-name>/
REPO_ROOT = Path("/kaggle/input/medication-companion-source")
```

## 3. Add API key secret

1. Notebook → **Add-ons → Secrets**.
2. Add `GEMINI_API_KEY` with your Google AI Studio or Vertex key.
3. In the first code cell, expose it:

```python
from kaggle_secrets import UserSecretsClient
os.environ["GEMINI_API_KEY"] = UserSecretsClient().get_secret("GEMINI_API_KEY")
```

## 4. Verify Run All

Expected output:
- Section 2: cross-visit memory demo prints warfarin from prior visit
- Section 4: Azee → azithromycin, Pantocid DSR → combo split
- Section 5: full pipeline (requires API key)
- Section 6: Hindi translation sample

## 5. Publish

1. **Save Version** → **Save & Run All (Commit)**.
2. Set visibility to **Public**.
3. Copy the notebook URL into `docs/kaggle_submission/SUBMISSION.md` and the writeup.

## Local verification (before upload)

```bash
cd backend
MEMORY_BACKEND=local ENVIRONMENT=local GEMINI_API_KEY=your-key \
  jupyter nbconvert --to notebook --execute ../notebooks/medication_companion_demo.ipynb
```

Or open in VS Code / Jupyter and run all cells with `MEMORY_BACKEND=local`.
