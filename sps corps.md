# Initial Project Specification
## Local Agentic Loan Triage Decision-Support Tool

---

## 1. Executive Summary

Fintech lending platforms process large volumes of structured loan applications that require preliminary triage before manual underwriting. Risk operations associates must quickly assess applicant financial profiles, apply institutional risk thresholds, and determine whether an application should be escalated for full underwriting review. In practice, borderline cases—those near risk thresholds—are particularly susceptible to inconsistent interpretation, leading to misclassification, unnecessary escalations, or overlooked risk exposure.

This project proposes a local, CPU-compatible, agentic decision-support system that assists fintech risk operations associates in structured loan triage. The system evaluates applicant financial attributes (e.g., income, debt-to-income ratio, credit score, employment duration), applies deterministic risk scoring rules, references internal lending policy constraints, and generates a structured recommendation. The output includes both an assigned risk tier and a recommendation to either escalate to manual underwriting or withhold escalation, accompanied by a transparent justification.

The system is designed as an agentic workflow rather than a simple scoring script. It validates structured inputs, invokes deterministic risk calculation tools, retrieves relevant policy clauses, synthesizes structured reasoning using a local large language model, and logs its decision rationale. All inference and data storage occur locally to ensure offline capability and privacy compliance. The tool does not issue final loan approvals; it supports triage decisions only.

The primary performance objective is to reduce borderline-case misclassification by improving consistency in how near-threshold applications are evaluated. System effectiveness will be measured through controlled scenario testing, including agreement with a predefined decision rubric, consistency under edge-case variations, and latency under CPU-only execution constraints. This initial specification outlines the scope, requirements, architecture, and evaluation framework for a nine-week prototype implementation.

---

## 2. Business Problem Statement

Fintech platforms offering unsecured personal consumer loans process high volumes of structured applications that require preliminary triage before full manual underwriting. Risk operations associates must evaluate key financial indicators—including credit score, monthly income, debt-to-income ratio, recent delinquencies, and requested loan amount—to determine whether an application should proceed to manual underwriting or be withheld at the intake stage.

Borderline applications, particularly those near predefined risk thresholds, present a persistent operational challenge. Over-reliance on a single dominant metric (such as credit score), inconsistent interpretation of policy thresholds, and increasing policy complexity contribute to variability in triage decisions. As a result, similar applicant profiles may receive different escalation outcomes depending on the reviewer, workload conditions, or subjective interpretation of lending guidelines.

Misclassification of borderline cases has measurable business consequences. Unnecessary escalations increase manual review costs and delay processing timelines, while insufficient escalation of higher-risk applicants increases institutional risk exposure. These inconsistencies reduce operational efficiency and introduce avoidable variability into the early-stage risk assessment process.

The core problem addressed by this project is the need for a structured, policy-aware decision-support mechanism that standardizes preliminary triage for unsecured personal loan applications, with particular emphasis on improving consistency in borderline-case evaluation.

---

## 3. Stakeholders

### Primary User
Fintech Risk Operations Associate responsible for preliminary triage of unsecured personal loan applications in a high-volume digital lending environment. This user evaluates structured applicant data and determines whether applications should proceed to manual underwriting review or be declined at intake.

### Secondary Stakeholders
- Manual Underwriting Team: Receives escalated applications and benefits from improved triage consistency and reduced unnecessary workload.
- Compliance and Risk Oversight Team: Monitors adherence to lending policy thresholds and seeks transparent, auditable decision rationale.
- Lending Operations Manager: Responsible for processing efficiency, cost control, and risk exposure management.

### Indirect Stakeholders
- Applicants, who are affected by processing timelines and decision consistency.
- Executive leadership, concerned with portfolio risk and operational scalability.

---

## 4. Decision Being Supported

The system supports fintech risk operations associates in determining whether an unsecured personal consumer loan application should be escalated to manual underwriting review or recommended for decline at intake, while simultaneously assigning a structured risk tier based on predefined financial criteria.

---

## 5. System Scope

### In Scope

- Structured intake of unsecured personal consumer loan application data, including:
  - Credit score
  - Monthly income
  - Debt-to-income ratio
  - Recent delinquencies
  - Loan amount requested
- Deterministic risk scoring based on predefined financial thresholds.
- Assignment of a structured risk tier (e.g., Low, Moderate, High).
- Recommendation to either:
  - Escalate the application to manual underwriting, or
  - Recommend decline at intake.
- Retrieval and reference to locally stored internal lending policy text to support justification.
- Generation of a structured explanation describing the reasoning behind the risk tier and recommendation.
- Local logging of inputs, intermediate decisions, and final outputs for auditability and reproducibility.
- Fully offline, CPU-compatible operation using a locally hosted language model.

### Out of Scope

- Final automated loan approval decisions.
- Integration with external credit bureaus, banking APIs, or live financial systems.
- Real financial deployment or execution authority.
- Model fine-tuning or supervised retraining in the initial prototype phase.
- Support for multiple loan products beyond unsecured personal consumer loans.
- Parsing of unstructured documents such as PDFs or uploaded forms.
- Cloud-based inference or external AI service dependencies.

---

## 6. Functional Requirements

1. The system shall accept a single unsecured personal loan application as structured JSON input via a command-line interface.

2. The system shall validate incoming JSON inputs for required fields (credit score, monthly income, debt-to-income ratio, recent delinquencies, and loan amount requested), correct data types, and allowable value ranges.

3. The system shall return explicit validation error messages when required fields are missing, malformed, or outside defined operational bounds.

4. The system shall compute a deterministic risk score using a predefined scoring function based on the validated structured input features.

5. The system shall assign a discrete risk tier (e.g., Low, Moderate, High) based on the computed risk score and predefined tier thresholds.

6. The system shall determine a triage recommendation of either (a) escalate to manual underwriting or (b) recommend decline at intake, based on the assigned risk tier and defined policy thresholds.

7. The system shall identify borderline cases using a predefined quantitative margin around escalation or decline thresholds and shall explicitly flag outputs as borderline when this condition is met.

8. The system shall retrieve relevant policy statements from a locally stored lending policy document based on triggered rules or threshold conditions.

9. The system shall generate a structured decision explanation that includes:
   - Key input factors influencing the decision,
   - Computed risk score and assigned risk tier,
   - Triage recommendation,
   - References to applicable policy statements.

10. The system shall output results in structured JSON format containing, at minimum:
    - Risk score,
    - Risk tier,
    - Borderline flag,
    - Triage recommendation,
    - Structured explanation,
    - Timestamp.

11. The system shall log each evaluation locally, including input payload, validation outcomes, computed risk score, assigned risk tier, policy references, final recommendation, and timestamp.

12. The system shall provide a deterministic execution mode that bypasses natural-language explanation generation to support debugging, benchmarking, and baseline evaluation.

13. The system shall refuse to produce a recommendation when inputs are incomplete, contradictory, or outside defined operational constraints, and shall return a structured refusal message explaining the reason.

---

## 7. Nonfunctional Requirements

1. The system shall operate entirely offline and shall not require any external API calls or cloud-based inference services.

2. The system shall be compatible with CPU-only environments and shall not require GPU acceleration for core functionality.

3. The system shall execute a single loan triage evaluation within a target latency of under 5 seconds on a standard consumer-grade CPU environment.

4. The system shall store all input data, intermediate computations, and output logs locally, without transmitting or persisting data to external services.

5. The system shall maintain reproducibility such that identical input JSON payloads produce identical risk scores, risk tiers, and triage recommendations when executed in deterministic mode.

6. The system shall maintain auditability by logging all decision inputs, computed intermediate values, policy references, final outputs, and timestamps in a structured local log file.

7. The system shall clearly separate deterministic scoring logic from language model-generated explanations to ensure transparency in decision mechanics.

8. The system shall implement structured error handling and safe failure behavior, ensuring that invalid or incomplete inputs do not produce silent or undefined outputs.

9. The system shall support modular architecture such that input validation, scoring logic, policy retrieval, and language model reasoning components are independently testable.

10. The system shall protect sensitive data by ensuring that no raw applicant information is printed to console beyond structured outputs required for evaluation.

11. The system shall allow execution in a deterministic “no-LLM mode” to support benchmarking and performance comparison.

12. The system shall be documented sufficiently to allow independent reproduction of results by another developer using the same hardware class and local model configuration.

---

## 8. High-Level Agentic Architecture

### Overview

The system will use a two-stage hybrid agentic design to support structured loan triage decisions while maintaining transparency, controllability, and CPU-only feasibility. Stage 1 performs deterministic validation and risk scoring to ensure consistent mechanical decision logic. Stage 2 uses a local LLM as an agentic reasoning layer that reviews computed results, retrieves policy context, applies borderline-case logic, and generates a structured justification suitable for audit and handoff to manual underwriting.

This architecture ensures that the core decision mechanics (risk score, tier assignment, and threshold checks) remain deterministic and testable, while the LLM provides policy-aware interpretation, explanation synthesis, and structured handling of borderline cases.

### Components

1. **CLI Input Handler (JSON)**
   - Accepts a single application record via structured JSON.
   - Normalizes and forwards inputs to validation.

2. **Validation Module**
   - Verifies required fields, types, and allowable ranges.
   - Produces structured validation errors and safe refusals when necessary.

3. **Deterministic Scoring Engine (Stage 1)**
   - Computes risk score using predefined rules/weights.
   - Assigns discrete risk tier using predefined thresholds.
   - Applies base triage recommendation rules (escalate vs recommend decline).

4. **Borderline Detector**
   - Identifies near-threshold applications using a quantitative margin around decision boundaries.
   - Produces a borderline flag and the boundary conditions that triggered it.

5. **Policy Store + Retrieval Tool (Local)**
   - Maintains a locally stored lending policy document and rule reference map.
   - Retrieves relevant policy statements based on triggered rules, tier, and borderline conditions.

6. **LLM Reasoning & Justification Agent (Stage 2)**
   - Consumes structured context: validated inputs, computed score/tier, recommendation, borderline conditions, and retrieved policy statements.
   - Produces a structured explanation and can apply predefined escalation logic for borderline cases (e.g., recommend escalation for manual review if policy requires additional scrutiny near thresholds).
   - Does not override deterministic scoring outputs; any adjustment must be expressed as a documented borderline-handling recommendation consistent with policy constraints.

7. **Decision Output Formatter**
   - Produces structured JSON output containing risk score, risk tier, borderline flag, recommendation, policy references, and explanation.

8. **Local Logger**
   - Records inputs, intermediate outputs, policy retrieval results, final decision artifact, and timestamps for auditability and evaluation.

### Data Flow (End-to-End)

1. User submits loan application JSON via CLI.
2. Validation module checks completeness and correctness.
3. Stage 1 scoring engine computes risk score, assigns tier, and produces an initial recommendation.
4. Borderline detector flags near-threshold cases and captures boundary conditions.
5. Policy retrieval tool selects relevant policy statements for the identified tier/rules/borderline conditions.
6. Stage 2 LLM agent synthesizes a structured decision rationale and applies policy-consistent borderline guidance.
7. Output formatter emits final structured JSON result.
8. Logger stores a complete audit record locally.

### Agentic Behavior Definition

The system is agentic because it executes a multi-step decision workflow that includes tool invocation (validation, scoring, borderline detection, policy retrieval), maintains state across steps (structured intermediate artifacts), and produces justified decisions grounded in policy. The LLM’s role is constrained to policy-aware reasoning, borderline-case interpretation, and explanation generation, while deterministic components maintain decision transparency and reproducibility.

---

## 9. Evaluation Plan

### 9.1 Evaluation Objectives

The evaluation framework is designed to measure whether the system improves consistency and reduces borderline-case misclassification in preliminary loan triage decisions for unsecured personal consumer loans.

The primary evaluation objective is:

- To reduce misclassification rates for near-threshold (borderline) applications while maintaining deterministic consistency for clearly low- and high-risk cases.

---

### 9.2 Dataset Strategy

The evaluation dataset will be constructed using a hybrid approach:

1. A publicly available consumer loan dataset (e.g., Kaggle-based structured lending dataset) adapted to include the selected structured features:
   - Credit score
   - Monthly income
   - Debt-to-income ratio
   - Recent delinquencies
   - Loan amount requested

2. Synthetic augmentation to generate controlled borderline cases by perturbing feature values near defined risk thresholds.

This hybrid approach ensures realism in applicant distribution while enabling controlled stress-testing of threshold sensitivity and borderline-case handling.

---

### 9.3 Ground Truth Definition

Ground truth decisions will be defined using a dual-layer rubric:

Layer 1: Deterministic Scoring Rubric  
- A predefined scoring formula assigns risk scores and risk tiers based on structured feature weights and thresholds.

Layer 2: Borderline Handling Rules  
- Explicit decision rules for applications within a predefined margin around escalation/decline thresholds.
- These rules determine whether borderline cases should escalate to manual underwriting or be declined.

This dual-layer ground truth enables measurement of both mechanical scoring accuracy and borderline-case consistency.

---

### 9.4 Evaluation Metrics

The system will be evaluated using the following quantitative metrics:

1. Overall Decision Accuracy  
   - Percentage agreement between system output and ground truth rubric.

2. Borderline-Case Accuracy  
   - Agreement rate specifically for applications flagged within the borderline margin.

3. False Escalation Rate  
   - Percentage of cases escalated that ground truth defines as decline.

4. False Decline Rate  
   - Percentage of cases declined that ground truth defines as escalation.

5. Consistency Score  
   - Deterministic repeatability of decisions for identical inputs.

6. Latency  
   - Average execution time per application under CPU-only execution.

---

### 9.5 Baseline Comparison

The system will be compared against a deterministic-only baseline (Stage 1 scoring without LLM borderline interpretation). Improvement in borderline-case accuracy relative to the deterministic baseline will be used to evaluate the value added by the agentic reasoning layer.

---

### 9.6 Test Scenario Suite

In addition to dataset-level evaluation, a curated scenario suite will be constructed including:

- Clearly low-risk applications
- Clearly high-risk applications
- Near-threshold borderline cases
- Edge-case input errors

Each scenario will include predefined expected outputs to validate system behavior and failure handling.

---

## 10. 9-Week Implementation Plan

### Week 1 – Finalize Specification and Evaluation Framework
- Finalize business scope and feature definitions.
- Define deterministic scoring formula and tier thresholds.
- Formalize borderline margin definition.
- Identify and acquire Kaggle dataset.
- Draft synthetic borderline case generation plan.
- Deliverable: Locked specification + initial dataset schema + scoring rubric.

---

### Week 2 – Repository Structure and Core Infrastructure
- Implement project structure and modular architecture.
- Implement JSON CLI input handler.
- Implement validation module with structured error handling.
- Create logging framework.
- Deliverable: Validated JSON intake + logging + test harness.

---

### Week 3 – Deterministic Scoring Engine (Stage 1)
- Implement scoring formula.
- Implement risk tier assignment.
- Implement base triage recommendation logic.
- Implement borderline detection logic.
- Write unit tests for scoring determinism.
- Deliverable: Fully functional deterministic baseline system.

---

### Week 4 – Vertical Slice Prototype (End-to-End, No LLM Yet)
- Connect validation → scoring → borderline → output formatter.
- Implement deterministic execution mode.
- Run first evaluation on subset of dataset.
- Measure baseline accuracy and borderline-case performance.
- Deliverable: End-to-end working triage engine without LLM reasoning.

---

### Week 5 – Policy Store and Retrieval Layer
- Create local lending policy document.
- Implement rule-to-policy mapping.
- Implement local policy retrieval function.
- Integrate retrieval into pipeline.
- Deliverable: Deterministic + policy retrieval integrated.

---

### Week 6 – LLM Integration (Stage 2 Agent Layer)
- Integrate local CPU-compatible LLM.
- Design structured prompt template.
- Implement explanation synthesis logic.
- Ensure LLM does not override deterministic scoring.
- Deliverable: Two-stage hybrid system producing structured explanations.

---

### Week 7 – Borderline Logic Refinement and Stability
- Stress-test borderline cases.
- Refine borderline detection margin if necessary.
- Improve explanation clarity and policy citation consistency.
- Implement deterministic vs LLM comparison harness.
- Deliverable: Stable borderline-case reasoning behavior.

---

### Week 8 – Systematic Evaluation and Ablation Study
- Run full dataset evaluation.
- Measure overall accuracy, borderline-case accuracy, latency.
- Compare deterministic baseline vs hybrid agent.
- Document failure modes and edge cases.
- Deliverable: Evaluation report draft + metrics tables.

---

### Week 9 – Finalization, Documentation, and Demo Preparation
- Final code cleanup and modularization.
- Prepare reproducibility instructions.
- Prepare demo script with scenario walkthrough.
- Document limitations and future improvements.
- Deliverable: Final system, evaluation summary, and demonstration-ready artifact.
