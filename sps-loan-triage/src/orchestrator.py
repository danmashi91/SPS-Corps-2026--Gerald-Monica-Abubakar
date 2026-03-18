# orchestrator.py
# LangGraph Orchestrator — wires all pipeline components into a conditional graph.
# Implements Path A (non-borderline) and Path B (borderline) routing.
# Manages Mode 2 retry loop and deterministic fallback on LLM failure.

from datetime import datetime, timezone
from langgraph.graph import StateGraph, END

from state import AgentState, initial_state, MAX_RETRIES
from tools.validator import validate_input
from tools.scoring import run_scoring_engine
from tools.policy_retrieval import retrieve_policy_clauses, format_policy_context
from tools.output_handler import assemble_final_output, log_pipeline_record
from agent.reasoning_agent import reasoning_agent_node


# ---------------------------------------------------------------------------
# Node: Mode 1 — Validation and Scoring
# ---------------------------------------------------------------------------

def mode_1_node(state: AgentState) -> AgentState:
    """
    Validates input, runs deterministic scoring engine, detects borderline cases.
    Halts pipeline on validation or scoring failure.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Step 1 — Validate input
    is_valid, validated_input, error_message = validate_input(state["application_input"])

    if not is_valid:
        return {
            **state,
            "timestamp": timestamp,
            "error_flag": True,
            "error_stage": "mode_1",
            "error_message": error_message,
        }

    # Step 2 — Run scoring engine
    try:
        scoring_results = run_scoring_engine(validated_input)
    except Exception as e:
        return {
            **state,
            "timestamp": timestamp,
            "validated_input": validated_input,
            "error_flag": True,
            "error_stage": "mode_1",
            "error_message": f"Scoring engine error: {str(e)}",
        }

    return {
        **state,
        "timestamp": timestamp,
        "validated_input": validated_input,
        "risk_score": scoring_results["risk_score"],
        "risk_tier": scoring_results["risk_tier"],
        "triage_recommendation": scoring_results["triage_recommendation"],
        "borderline_flag": scoring_results["borderline_flag"],
    }


# ---------------------------------------------------------------------------
# Node: Policy Retrieval (Orchestrator Tool)
# ---------------------------------------------------------------------------

def policy_retrieval_node(state: AgentState) -> AgentState:
    """
    Retrieves relevant policy clauses for borderline cases.
    Proceeds without failure if no clauses are found.
    Only called on Path B (borderline cases).
    """
    policy_clauses, retrieval_status = retrieve_policy_clauses(
        risk_tier=state["risk_tier"],
        borderline_flag=state["borderline_flag"],
        validated_input=state["validated_input"],
    )

    policy_context = format_policy_context(policy_clauses)

    return {
        **state,
        "policy_context": policy_context,
        "policy_retrieval_status": retrieval_status,
    }


# ---------------------------------------------------------------------------
# Node: Mode 3 — Output Assembly and Logging
# ---------------------------------------------------------------------------

def mode_3_node(state: AgentState) -> AgentState:
    """
    Assembles final output, validates schema, logs audit record.
    Handles deterministic fallback when Mode 2 failed.
    """
    # Apply deterministic fallback if LLM failed
    if state["llm_status"] == "failed_after_retries":
        state = {
            **state,
            "fallback_used": True,
            "decision_explanation": None,
            "policy_references": [],
        }

    final_output = assemble_final_output(state)
    log_pipeline_record(state, final_output)

    return {**state, "final_output": final_output}


# ---------------------------------------------------------------------------
# Routing Functions
# ---------------------------------------------------------------------------

def route_after_mode_1(state: AgentState) -> str:
    """
    Route after Mode 1 completes:
    - Hard failure → end (error output)
    - Non-borderline → mode_3 (Path A)
    - Borderline → policy_retrieval (Path B)
    """
    if state["error_flag"]:
        return "end_error"
    if state["borderline_flag"]:
        return "policy_retrieval"
    return "mode_3"


def route_after_reasoning(state: AgentState) -> str:
    """
    Route after Mode 2 LLM reasoning attempt:
    - Success → mode_3
    - Retry available → reasoning_agent (retry loop)
    - Retries exhausted → mode_3 (fallback will be applied in mode_3)
    """
    if state["llm_status"] == "success":
        return "mode_3"
    elif state["llm_status"] == "retry" and state["retry_count"] <= MAX_RETRIES:
        return "reasoning_agent"
    else:
        return "mode_3"


# ---------------------------------------------------------------------------
# Error Terminal Node
# ---------------------------------------------------------------------------

def end_error_node(state: AgentState) -> AgentState:
    """
    Terminal node for hard pipeline failures (Mode 1 errors).
    Assembles minimal error output and logs the failure record.
    """
    from tools.output_handler import assemble_final_output, log_pipeline_record
    final_output = assemble_final_output(state)
    log_pipeline_record(state, final_output)
    return {**state, "final_output": final_output}


# ---------------------------------------------------------------------------
# Graph Assembly
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """
    Build and compile the LangGraph pipeline.

    Graph structure:
      mode_1 → [conditional]
        ├── end_error       (Mode 1 failure)
        ├── mode_3          (Path A: non-borderline)
        └── policy_retrieval → reasoning_agent → [conditional]
              ├── reasoning_agent  (retry loop)
              └── mode_3           (Path B complete or fallback)
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("mode_1", mode_1_node)
    graph.add_node("policy_retrieval", policy_retrieval_node)
    graph.add_node("reasoning_agent", reasoning_agent_node)
    graph.add_node("mode_3", mode_3_node)
    graph.add_node("end_error", end_error_node)

    # Entry point
    graph.set_entry_point("mode_1")

    # Conditional routing after Mode 1
    graph.add_conditional_edges(
        "mode_1",
        route_after_mode_1,
        {
            "end_error": "end_error",
            "policy_retrieval": "policy_retrieval",
            "mode_3": "mode_3",
        },
    )

    # Path B: policy retrieval → reasoning agent
    graph.add_edge("policy_retrieval", "reasoning_agent")

    # Conditional routing after reasoning agent (retry loop or proceed)
    graph.add_conditional_edges(
        "reasoning_agent",
        route_after_reasoning,
        {
            "reasoning_agent": "reasoning_agent",
            "mode_3": "mode_3",
        },
    )

    # Terminal edges
    graph.add_edge("mode_3", END)
    graph.add_edge("end_error", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public Run Function
# ---------------------------------------------------------------------------

def run_pipeline(application_input: dict) -> dict:
    """
    Execute the full loan triage pipeline for a single application.

    Args:
        application_input: Raw loan application dict from CLI.

    Returns:
        Final output dict (TriageOutput or ErrorOutput).
    """
    app = build_graph()
    state = initial_state(application_input)
    final_state = app.invoke(state)
    return final_state["final_output"]
