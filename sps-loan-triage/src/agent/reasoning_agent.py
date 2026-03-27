# agent/reasoning_agent.py
# Mode 2 — Policy-Aware Reasoning and Justification Agent
# This is the only LLM agent in the pipeline.
# Triggered only for borderline cases (borderline_flag = True).
# Receives pre-processed context from Mode 1 and retrieved policy text.
# Does not call tools directly — all context is injected by the orchestrator.

from state import AgentState
from llm_client import call_llm, PRIMARY_MODEL, FALLBACK_MODEL
from schemas import ReasoningAgentOutput

# ---------------------------------------------------------------------------
# System Prompt — Mode 2
# ---------------------------------------------------------------------------

REASONING_AGENT_SYSTEM_PROMPT = """You are a policy-aware loan triage reasoning assistant.

Your role is to review a borderline loan application and generate a structured, 
policy-aligned justification for the triage recommendation that has already been 
determined by the deterministic scoring engine.

CRITICAL RULES:
- You must NOT override or contradict the deterministic risk score, risk tier, 
  or triage recommendation provided to you. These are fixed outputs from the 
  scoring engine and are not subject to your interpretation.
- Your job is to EXPLAIN and JUSTIFY the recommendation using the input factors 
  and retrieved policy clauses.
- You must ONLY cite policy clauses that appear in the provided policy context. 
  Do not invent or hallucinate policy rules.
- When listing policy_references, copy the EXACT full text of each policy clause 
  you cited, including its ID prefix (e.g. "POL-002: Applications with a DTI..."). 
  Do not use numbers, abbreviations, or short labels.
  Example: "Applications with a debt-to-income ratio exceeding 43% require mandatory escalation."
- If no policy clauses were retrieved, generate a justification based solely on 
  the scoring factors without citing policy.
- Be concise. Your explanation should be 2–4 sentences suitable for audit review 
  by a risk operations associate.
- Output valid JSON matching the required schema exactly."""


# ---------------------------------------------------------------------------
# User Message Builder
# ---------------------------------------------------------------------------

def _build_user_message(state: AgentState) -> str:
    """
    Construct the user message injected into the Mode 2 LLM prompt.
    Combines Mode 1 outputs and retrieved policy context.
    """
    validated = state["validated_input"]
    policy_context = state["policy_context"] or "No policy clauses retrieved."

    return f"""LOAN APPLICATION DATA:
- Credit Score: {validated.get('credit_score')}
- Monthly Income: ${validated.get('monthly_income'):,.2f}
- Debt-to-Income Ratio: {validated.get('debt_to_income_ratio') * 100:.1f}%
- Recent Delinquencies: {validated.get('recent_delinquencies')}
- Loan Amount Requested: ${validated.get('loan_amount_requested'):,.2f}

SCORING ENGINE RESULTS:
- Risk Score: {state['risk_score']:.1f}/100
- Risk Tier: {state['risk_tier']}
- Borderline Case: Yes
- Base Recommendation: {state['triage_recommendation'].replace('_', ' ').title()}

POLICY CONTEXT:
{policy_context}

Generate a structured justification explaining why this borderline application 
received the recommendation above, referencing the relevant input factors and 
any applicable policy clauses."""


# ---------------------------------------------------------------------------
# Reasoning Agent Node
# ---------------------------------------------------------------------------

def reasoning_agent_node(state: AgentState) -> AgentState:
    """
    Mode 2 LLM reasoning node.
    Takes AgentState, calls the LLM, returns updated AgentState.

    This function is called by the orchestrator only when borderline_flag is True.
    Handles retry logic externally via the orchestrator's retry loop.
    """
    user_message = _build_user_message(state)

    # Attempt with primary model first; fall back if primary is unavailable
    model_to_use = PRIMARY_MODEL

    try:
        output: ReasoningAgentOutput = call_llm(
            system_prompt=REASONING_AGENT_SYSTEM_PROMPT,
            user_message=user_message,
            response_schema=ReasoningAgentOutput,
            model=model_to_use,
            temperature=0.3,
        )

        return {
            **state,
            "decision_explanation": output.decision_explanation,
            "policy_references": output.policy_references,
            "llm_status": "success",
        }

    except Exception as e:
        # Return failure signal — orchestrator handles retry or fallback
        new_retry_count = state["retry_count"] + 1
        llm_status = (
            "retry"
            if new_retry_count <= state["max_retries"]
            else "failed_after_retries"
        )

        return {
            **state,
            "retry_count": new_retry_count,
            "llm_status": llm_status,
            "error_flag": llm_status == "failed_after_retries",
            "error_stage": "mode_2" if llm_status == "failed_after_retries" else state["error_stage"],
            "error_message": str(e) if llm_status == "failed_after_retries" else state["error_message"],
        }
