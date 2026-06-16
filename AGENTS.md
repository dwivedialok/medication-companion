# AGENTS.md

> This file follows the 2026 Kaggle AI Agents Intensive convention.
> It is the primary context file for coding agents (Cursor, Claude Code, Jules, etc.)
> working in this repository. Update it every time agent behaviour changes.

---

## Project overview

**Medication Companion** is a multi-agent AI system (Google ADK + Gemini) that helps patients in India
understand prescriptions and flag drug interactions across multiple visits.

**Stack:** Python 3.11 · Google ADK · FastAPI · Flutter · GCP (Cloud Run, Vertex AI, Firebase)

---

## Hard rules (non-negotiable)

1. Never generate diagnostic language ("you have", "this indicates a condition")
2. Every patient-facing string ends with "Please discuss this with your doctor or pharmacist."
3. Never store prescription images or clinical notes in memory — only resolved generic drug names
4. Never call raw Gemini API — always use `google.adk LlmAgent`
5. Never use `print()` in production paths — use `google.cloud.logging`
6. Never deploy with `--allow-unauthenticated` — both Cloud Run services require auth
7. `patient_id` comes from verified Firebase JWT — never from client body

---

## Workflow

```
backend/agents/    → agent logic (each agent is one file, one responsibility)
backend/tools/     → FunctionTools (one tool per file, fully typed, testable in isolation)
backend/memory/    → session + memory wrappers
backend/evaluation/→ LLM-as-Judge (async, non-blocking)
frontend/lib/      → Flutter app
deploy/            → deployment scripts
scripts/           → GCP setup/teardown
```

---

## Adding a new feature

1. Update this file first with the new rule or boundary
2. Update `.cursor/rules/medication-companion.mdc` if it affects agent/tool behaviour  
3. Write the test in `backend/tests/` before generating the implementation
4. Implement in the appropriate `agents/` or `tools/` file
5. Run `pytest backend/tests/` — all tests must pass before committing

---

## Environment setup

```bash
cd backend
cp ../.env.example .env.local
# Set MEMORY_BACKEND=local for development (no GCP credentials needed)
pip install -r requirements.txt
pytest tests/
```

---

## What not to do

- Do not add a new agent without updating the agent boundary table in `.cursor/rules/`
- Do not add a tool that calls another agent — tools are leaf nodes
- Do not add GCP credentials to `.env.example` — that file is committed
- Do not add new severity levels — only: `HIGH`, `MODERATE`, `LOW`, `INFO`, `NONE`
