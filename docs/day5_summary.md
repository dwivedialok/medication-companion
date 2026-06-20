## Key Points Taught in Day 5

### 1. Spec-Driven Development (SDD) & BDD

* **Code is Disposable, Specs are Permament:** In an agentic workflow, code can be completely regenerated or flipped to a new stack in an afternoon. The true source of truth is a rock-solid specification file (Markdown/YAML) checked into version control.
* **Behavior-Driven Development (BDD):** To prevent "Rogue Agent" incidents where an autonomous system guesses, you must use Gherkin syntax (Scenario / Given / When / Then) to force the LLM to think in strict terms of State $\rightarrow$ Action $\rightarrow$ Outcome.
* **The "Format Tax":** Research shows LLM agents face significant performance drops when using unoptimized instruction formats. For Gemini-powered applications, narrative instructions belong in Markdown, but deeply nested structures (nesting depth $> 3$) operate with the best token economics and parsing accuracy when rendered in flat YAML blocks.

### 2. Instruction Hierarchy & Execution Modes

* **Where Instructions Live:** To avoid context fragmentation, instructions are layered across a strict hierarchy:
* **Chat Interface:** Short-lived, session-specific orchestration.
* **Spec Folder:** Static, task-specific blueprints and schemas.
* **Agent Skills:** Reusable, feature-focused workflows in the `.agent/skills/` directory.
* **System Prompts:** Global project DNA via `AGENTS.md` and local `GEMINI.md` overrides.


* **Forensic Specialist Mode:** When fixing application bugs, prompts must transition from vague symptoms to evidence-driven inputs (e.g., feeding raw stack traces or terminal outputs directly to the agent).

### 3. The Runtime Safety Net: Policy Servers & Context Hygiene

* **Hybrid Policy Servers:** Hardcoded prompts are brittle and vulnerable to injections. Production systems use external, tamper-proof policy engines operating on two layers:
* **Structural Gating:** Binary, rule-based role/environment checks (e.g., a "viewer" role cannot execute mutations).
* **Semantic Gating:** A secondary, independent LLM evaluates the *intent* of the primary agent's proposed action against guidelines to catch leaks or rule violations before execution.


* **Context Hygiene:** To eliminate "Context Hallucination" risks, developers must implement string-sanitization middleware (like a `ContextResolver`) to dynamically swap out structural templates (using `[[VARIABLE_NAME]]` syntax) with validated environment variables at runtime.

---

## What Should Be Covered in Your Capstone Project

To make your medication companion production-grade according to "Day_5_v3.pdf", your project submission should explicitly address these implementation steps:

### Define Your Multi-Agent BDD Scenarios

Your `specs/` folder must explicitly outline the multi-agent handoff behavior using Gherkin syntax. This prevents the processing loops from mixing up context. For instance:

> **Scenario:** Severe drug interaction detected across separate doctor visits.
> **Given** the Patient Profile contains a history of Drug A from Doctor X.
> **When** the Prescription Reader extracts a brand name that resolves to Drug B from Doctor Y.
> **Then** route the execution to the Interaction Flagger tool, halt the translation pipeline, and mandate a severe-tier warning block.

### Structure Data Schemas in Optimized YAML

Do not pass complex, multi-visit patient records or chemical interaction matrices as loose paragraphs or chaotic JSON blocks. Implement the hybrid formatting guidelines taught on Day 5: express your medication history variables, drug conflict tables, and regional language mapping variables in structured YAML to keep Gemini operating with optimal token efficiency.

### Build a Policy Server for Action Gates

Your system is explicitly *not* a diagnostic tool. You must show how you implement external structural and semantic gating to protect the patient. If an agent attempts to dynamically suggest an alternative over-the-counter drug patch or self-correct an invalid dosage calculation, your Policy Server must intercept that tool call, flag a "Policy Violation", and force the system to fallback to directing the user to their medical practitioner.

### Implement a Dynamic ContextResolver for Audio Generation

When generating the localized audio explanation, your prompt templates should maintain strict context hygiene. Use placeholder syntax like `[[PATIENT_LANGUAGE]]` and `[[SEVERITY_TONE]]`. Your core application middleware should dynamically resolve these tags into verified system targets right before execution, guaranteeing that sensitive history boundaries do not leak into the generic translation agent's context window.

### Leverage the `google-agents-cli` Workflow

In your documentation and video presentation, show how you manage your deployment lifecycle using Google's standardized infrastructure. Highlight how you use `agents-cli scaffold` for initial blueprinting, run verification via `agents-cli eval run`, and execute sandboxed deployment directly to a cloud architecture via `agents-cli deploy`.

---

How are you planning to structure the background database execution for matching brand-to-generic drugs—will you be utilizing a local file system transport mapping or exposing it via a remote Model Context Protocol (MCP) server?