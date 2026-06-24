# Contributing to Medication Companion

Thank you for your interest in contributing. Medication Companion is an open
source, **educational prototype** — a multi-agent AI system that helps patients
understand prescriptions and flag potential drug interactions. Because the
domain is healthcare-adjacent, we hold contributions to a higher bar than a
typical hobby project, even though this software is **not a medical device** and
**not clinically validated**.

Please read this guide, our [Code of Conduct](CODE_OF_CONDUCT.md), and
[`AGENTS.md`](AGENTS.md) before opening an issue or pull request.

---

## Important disclaimers

- **Not medical advice.** Do not use this repository to diagnose, treat, or
  manage any medical condition. Every patient-facing string must direct users
  back to a doctor or pharmacist.
- **Not a substitute for professional care.** Contributions must not imply
  clinical validation, regulatory approval, or device certification.
- **Your responsibility.** If you deploy a fork, you are responsible for its
  safety, privacy compliance, and regulatory posture in your jurisdiction.

See also [`docs/out_of_scope.md`](docs/out_of_scope.md) for deliberate product
boundaries.

---

## Privacy and sensitive data

**Never include real patient or personal health information** in issues, pull
requests, commit messages, logs, screenshots, or test fixtures.

| Do | Don't |
|----|-------|
| Use `data/sample/smoke_4drug_2interactions.png` and other committed fixtures | Upload real prescription photos |
| Redact or syntheticise any demo screenshots | Share Firebase UIDs, emails, or JWTs |
| Describe bugs with expected vs actual behaviour | Paste production Cloud Logging output containing patient identifiers |
| Run locally with `MEMORY_BACKEND=local` | Point tests at production Memory Bank or GCS buckets with real user data |

If you accidentally commit sensitive data, do **not** open a public issue.
Contact the maintainers immediately so the data can be removed from history.

---

## Code of Conduct

All participants must follow our [Code of Conduct](CODE_OF_CONDUCT.md).
Harassment, discrimination, and sharing others' private information are not
tolerated.

---

## Ways to contribute

You do not need permission to start work on a small fix. For larger changes,
open an issue first so maintainers can confirm direction.

| Contribution type | Where to start |
|-------------------|----------------|
| Bug report | [GitHub Issues](https://github.com/3amwave/medication-companion/issues) — use the bug template if available |
| Feature request | Issue first — check [`docs/out_of_scope.md`](docs/out_of_scope.md) and [`docs/BACKLOG.md`](docs/BACKLOG.md) |
| Agent or tool behaviour change | Update [`specs/`](specs/) **before** code — see workflow below |
| Drug data (brands, interactions) | Edit curated CSVs or [`scripts/build_drug_index.py`](scripts/build_drug_index.py); see [`AGENTS.md`](AGENTS.md#drug-data-sources) |
| Documentation | `README.md`, `docs/`, or inline docstrings |
| Tests | `backend/tests/unit/` and `backend/tests/integration/` |
| Frontend (Flutter PWA) | `frontend/lib/` |

---

## Development setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or `pip`
- Flutter 3.x (frontend work only)
- GCP credentials (deploy / Vertex AI / Memory Bank only — not required for unit tests)

### Backend (no GCP credentials)

```bash
cd backend
cp ../.env.example .env.local    # set MEMORY_BACKEND=local
uv sync
uv run pytest tests/unit tests/integration
```

### Local HTTP pipeline

```bash
make local-auth-broker           # http://localhost:8080
```

Uses `USE_LOCAL_RUNNER=true` for an in-process agent pipeline. See
[`README.md`](README.md#quick-start-local-development) and
[`docs/deployment_runbook.md`](docs/deployment_runbook.md) for full details.

### Demo notebook

```bash
jupyter notebook notebooks/medication_companion_demo.ipynb
```

Runs all five agents with `InMemorySessionService` — no GCP credentials required.

---

## Spec-driven workflow

Behaviour changes must flow through the spec layer. This is the contract between
intent, tests, and code.

1. **Update [`specs/`](specs/)** — Gherkin scenarios (`.feature`) or YAML schemas
   under `specs/schemas/`.
2. **Update [`AGENTS.md`](AGENTS.md)** if you are changing a hard rule or agent
   boundary.
3. **Write or update tests** under `backend/tests/` *before* or alongside the
   implementation.
4. **Implement** in the appropriate `backend/agents/` or `backend/tools/` file.
5. **Run the test suite** — all tests must pass before merge.

Instruction hierarchy (most specific first): chat session → `specs/` →
`.agent/skills/` → `backend/agents/GEMINI.md` → `AGENTS.md`.

Mapping of specs to tests: [`specs/README.md`](specs/README.md).

---

## Safety-critical rules

These rules apply to **all** contributions touching agents, tools, memory, policy,
or patient-facing UI. They mirror [`AGENTS.md`](AGENTS.md) and are non-negotiable.

1. **No diagnostic language** — never generate text like "you have …" or "this
   indicates a condition".
2. **Mandatory consult redirect** — every patient-facing string ends with
   *"Please discuss this with your doctor or pharmacist."* (or an approved
   localised equivalent from `specs/schemas/language_map.yaml`).
3. **Memory stores generics only** — never persist prescription images, clinical
   notes, diagnosis text, or raw LLM output to Memory Bank.
4. **Use ADK agents** — do not call the raw Gemini API from production paths;
   use `google.adk` `LlmAgent`.
5. **Structured logging only** — no `print()` in production code; use
   `google.cloud.logging`.
6. **`patient_id` from verified JWT** — never trust client-supplied patient
   identifiers.
7. **Severity levels are fixed** — only `HIGH`, `MODERATE`, `LOW`, `INFO`,
   `NONE`. Do not invent new levels.
8. **Tools are leaf nodes** — a `FunctionTool` must not invoke another agent.
9. **Honest uncertainty** — unresolved drug names must surface as `UNRESOLVED`,
   never guessed into fake generics.

Changes to interaction lookup, drug resolution tiers, or policy gates require
extra scrutiny. Tag your PR with the safety checklist below.

---

## Pull request guidelines

### Before opening a PR

- [ ] Branch from `main` (or the branch the maintainer specifies).
- [ ] Scope is focused — one logical change per PR where possible.
- [ ] `uv run pytest tests/unit tests/integration` passes locally.
- [ ] No secrets, credentials, or real patient data in the diff.
- [ ] If behaviour changed: `specs/` updated and tests added/updated.
- [ ] If a hard rule changed: `AGENTS.md` updated.

### PR description

Include:

- **What** changed (brief summary).
- **Why** (bug, feature, spec alignment).
- **How to test** (commands, fixtures, manual steps).
- **Safety impact** (yes/no — if yes, explain patient-facing or interaction effects).

### Review expectations

Maintainers may request changes, defer large refactors, or ask you to split a PR.
First-time contributors: CI may require maintainer approval before checks run
(GitHub's default for fork PRs).

We aim to review within a few business days; complex agent or safety changes may
take longer.

---

## Safety checklist (agent / tool / policy PRs)

Complete this section in your PR description when touching
`backend/agents/`, `backend/tools/`, `backend/policy/`, `backend/memory/`, or
patient-facing strings:

- [ ] No new diagnostic or dosing language introduced.
- [ ] Mandatory consult disclaimer preserved (all languages touched).
- [ ] Interaction severity comes from deterministic lookup where applicable —
      LLM does not invent or omit `HIGH`/`MODERATE` findings.
- [ ] Memory writes store only allowed fields (generics, timestamp, severity summary).
- [ ] Unresolved brands remain `UNRESOLVED` — no silent guessing.
- [ ] Tests cover the changed behaviour (unit or integration).
- [ ] Eval harness updated if drug lookup tiers or smoke fixture expectations change.

---

## Commit messages

Write clear, descriptive commit messages. A short subject line (≤72 characters)
plus an optional body explaining *why* is sufficient.

Good examples:

```
Fix Gate 1 reject when confidence is exactly 0.75

Add curated interaction override for aspirin + nimesulide

Update specs/pipeline.feature for cross-visit warfarin scenario
```

Avoid vague messages like `fix bug` or `update code`.

---

## Drug data contributions

Curated data (`data/india_brands.csv`, `data/curated_interactions.csv`) is
committed and hand-reviewed. Kaggle source CSVs are **not** committed.

To add or fix brand mappings or interactions:

1. Edit the curated CSV with a cited source (package insert, standard reference,
   or maintainer-verified clinical text — not unsourced LLM output).
2. Run `python scripts/build_drug_index.py` to rebuild `data/drugs.db`.
3. Run `uv run pytest backend/tests/test_drug_lookup_eval.py`.
4. Include the CSV + rebuilt `drugs.db` in your PR.

See [`README.md`](README.md#drug-data-sources) for Kaggle download links.

---

## Security vulnerabilities

**Do not** open public issues for security vulnerabilities.

Report them privately via GitHub **Security → Report a vulnerability** on the
repository, or email the maintainer listed in [`SECURITY.md`](SECURITY.md).

---

## License

By contributing, you agree that your contributions will be licensed under the
same terms as the project — [MIT License](LICENSE). You represent that you have
the right to submit the work and that it does not include third-party material
you are not permitted to license.

---

## Questions?

- Architecture and scope: [`docs/architecture.md`](docs/architecture.md),
  [`docs/out_of_scope.md`](docs/out_of_scope.md)
- Deployment: [`docs/deployment_runbook.md`](docs/deployment_runbook.md)
- Agent conventions: [`AGENTS.md`](AGENTS.md)
- Open a [GitHub Issue](https://github.com/3amwave/medication-companion/issues)
  for questions that are not security-sensitive.

We appreciate thoughtful contributions that improve patient safety *and*
responsible AI engineering. Thank you for helping build Medication Companion.
