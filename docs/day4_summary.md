
### **Summary of Day 4: Vibe Coding Agent Security and Evaluation**

Day 4 pivots away from simply building agents to ensuring they operate safely and actually fulfill the user's intent. It is broken down into two main halves: **Security** and **Evaluation**.

#### **1. Security: The 7-Pillar Harness & Active Defense**

A raw AI model is non-deterministic and cannot be implicitly trusted; it must be wrapped in a secure "harness" . Day 4 establishes a **Context-as-a-Perimeter** model.

* 
**The 7-Pillar Architecture:** This establishes the baseline secure harness, encompassing Infrastructure, Data, Model, Application & Runtime, Identity & Access Management (IAM), Observability, and Governance .


* 
**Execution Isolation & Supply Chain Defense:** Untrusted agent code must run in ephemeral, kernel-level sandboxes that reset their state between runs . Furthermore, CI/CD pipelines must actively verify dependencies to prevent agents from pulling in malware via hallucinated software packages .


* 
**Zero Ambient Authority & JIT Downscoping:** Agents must never inherit broad administrative privileges . They should be issued unique cryptographic identities (like SPIFFE IDs) and receive Just-In-Time (JIT) hyper-restricted tokens that expire immediately after a task is completed .


* 
**Agentic Security Operations (SecOps):** Because natural language attack surfaces change rapidly, manual monitoring is too slow . Systems require an automated triad: Red Teams (injecting "adversarial vibes" to test the agent), Blue Teams (monitoring behavioral analytics), and Green Teams (executing stateful quarantines and auto-refactoring vulnerable code) .



#### **2. Observability & Evaluation: The "Glass Box"**

Security proves the agent did no harm, but evaluation proves it actually delivered value. Evaluating vibe-coded agents is uniquely difficult because there is no rigid specification to test against, users often cannot validate the output themselves, and the environment is highly iterative .

* 
**Observability:** You must track the "Vibe Trajectory" using tools like OpenTelemetry to log the agent's cognitive leaps, tool calls, and API interactions . This helps detect "Intent Drift"—when an agent's internal reasoning begins to diverge maliciously or incorrectly from the user's prompt .


* 
**The 7 Dimensions of Evaluation:** * **User-Facing:** Intent satisfaction, Functional correctness, Visual/behavioral correctness, and Cost/efficiency .


* 
**Internal:** Code quality, Trajectory quality, and Self-repair behavior .


* 
**Transversal:** Safety & Responsible AI, which intersects all other dimensions.




* 
**Evaluation Methods:** Testing requires a mix of standard automated functional testing, static security analysis, LLM-as-a-judge (scoring outputs against derived rubrics), trajectory inspection, and clustering real-world user corrections .



---

### **Applying Day 4 to Your Capstone Project**

Since the Capstone officially went public yesterday (June 19, 2026), you have until **Monday, July 6, 2026** to finalize your work. Your submission must include a Kaggle writeup, a video explanation, your project rationale, and a link to your code.

For your medication companion, your writeup and video **must** strongly emphasize how you tackled these specific Day 4 themes:

* 
**Transversal Safety & Refusal Behavior:** You noted, *"This is not a diagnostic tool."* You must demonstrate how you evaluate your agent's safety constraints. Show how you used Red Teaming or adversarial probing to ensure the agent actively refuses to give direct medical advice and successfully routes the user back to their doctor .


* **Securing the Data Pillar:** Your agent processes prescriptions and medication history, meaning you are handling highly sensitive PII. Your rationale should explain how you secure this context using strict tenant partitioning (ensuring Patient A's RAG data cannot bleed into Patient B's queries) and egress governance to prevent data exfiltration .


* 
**Combating Hallucinations:** Day 4 heavily warns against models hallucinating fake software dependencies . In your domain, a hallucinated drug interaction could be catastrophic. You need to document how you use deterministic hooks and verified internal registries (like a verified medical database) to ground the agent's logic and prevent medical hallucinations.


* 
**Evaluating "Intent Satisfaction":** Since your workflow is complex (scanning $\rightarrow$ resolving $\rightarrow$ cross-referencing $\rightarrow$ translating), you should outline how you use an LLM-as-a-judge . The judge should evaluate if the agent's final plain-language, translated audio output successfully captures the actual clinical severity identified in the initial prescription scan.



Given that your project culminates in translating the explanation into local Indian languages and generating audio, how are you planning to structure your evaluation suite to test the agent's translation accuracy and tone calibration across those different dialects?