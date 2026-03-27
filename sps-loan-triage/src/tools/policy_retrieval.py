# tools/policy_retrieval.py
# Orchestrator Tool — Policy Retrieval
# Retrieves relevant lending policy clauses from a local policy store
# based on triggered conditions (risk tier, borderline flag, rule violations).
# This tool is called by the orchestrator, not by the LLM agent directly.

import json
import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Path to local policy store — JSON file containing policy rules
POLICY_STORE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "lending_policy.json"
)


# ---------------------------------------------------------------------------
# Policy Store Structure (expected JSON format)
# ---------------------------------------------------------------------------
# lending_policy.json should follow this structure:
#
# {
#   "policies": [
#     {
#       "id": "POL-001",
#       "trigger_tiers": ["High"],
#       "trigger_conditions": ["high_dti", "borderline"],
#       "clause": "Applications with a DTI ratio exceeding 43% require mandatory escalation."
#     },
#     ...
#   ]
# }


# ---------------------------------------------------------------------------
# Retrieval Functions
# ---------------------------------------------------------------------------

def load_policy_store() -> list[dict]:
    """
    Load the local policy store from JSON file.
    Returns an empty list if file is not found or malformed.
    """
    try:
        with open(POLICY_STORE_PATH, "r") as f:
            data = json.load(f)
            return data.get("policies", [])
    except FileNotFoundError:
        # Policy store not yet created — return empty during early development
        return []
    except json.JSONDecodeError:
        return []


def retrieve_policy_clauses(
    risk_tier: str,
    borderline_flag: bool,
    validated_input: dict,
) -> tuple[list[str], str]:
    """
    Retrieve relevant policy clauses based on triggered conditions.

    Args:
        risk_tier:        Assigned risk tier ("Low" / "Moderate" / "High")
        borderline_flag:  True if application is near a decision threshold
        validated_input:  Validated input fields for condition checking

    Returns:
        Tuple of (policy_clauses: list[str], retrieval_status: str)
        - policy_clauses: List of relevant policy clause strings
        - retrieval_status: "found" or "none_found"
    """
    policies = load_policy_store()

    if not policies:
        return [], "none_found"

    # Determine triggered conditions from input and scoring results
    triggered_conditions = _get_triggered_conditions(
        risk_tier, borderline_flag, validated_input
    )

    matched_clauses = []
    for policy in policies:
        tier_match = risk_tier in policy.get("trigger_tiers", [])
        condition_match = any(
            c in triggered_conditions for c in policy.get("trigger_conditions", [])
        )
        if tier_match or condition_match:
            matched_clauses.append(f"{policy['id']}: {policy['clause']}")

    if matched_clauses:
        return matched_clauses, "found"
    else:
        return [], "none_found"


def _get_triggered_conditions(
    risk_tier: str,
    borderline_flag: bool,
    validated_input: dict,
) -> list[str]:
    """
    Identify which policy trigger conditions apply to this application.
    Extend this list as policy rules grow during Week 5.
    """
    conditions = []

    if borderline_flag:
        conditions.append("borderline")

    if validated_input.get("debt_to_income_ratio", 0) > 0.43:
        conditions.append("high_dti")

    if validated_input.get("credit_score", 850) < 580:
        conditions.append("low_credit_score")

    if validated_input.get("recent_delinquencies", 0) >= 2:
        conditions.append("recent_delinquencies")

    if risk_tier == "High":
        conditions.append("high_risk_tier")

    if risk_tier == "Moderate":
        conditions.append("moderate_risk_tier")

    return conditions


def format_policy_context(policy_clauses: list[str]) -> str:
    """
    Format retrieved policy clauses into a single context string
    for injection into the Mode 2 LLM prompt.

    Returns:
        Formatted policy context string, or empty string if no clauses.
    """
    if not policy_clauses:
        return ""

    lines = ["Relevant Lending Policy Clauses:"]
    for clause in policy_clauses:
        lines.append(f"- {clause}")

    return "\n".join(lines)
