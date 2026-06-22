# Sample prescription images

## Committed smoke fixture

`smoke_4drug_2interactions.png` — synthetic Rx (no real patient data) for deterministic
interaction testing. See [docs/smoke_test_cheatsheet.md](../../docs/smoke_test_cheatsheet.md).

```bash
export RX_IMAGE=data/sample/smoke_4drug_2interactions.png
uv run python scripts/verify_smoke_fixture.py          # offline pair/interaction check
uv run python scripts/test_prescription.py "$RX_IMAGE" --url http://localhost:8080
```

Regenerate: `uv run python scripts/generate_smoke_prescription.py`

## Your own images (local only)

Real prescription photos stay gitignored:

```bash
cp ~/Downloads/my-prescription.jpg data/sample/prescription.jpg
export RX_IMAGE=data/sample/prescription.jpg
```
