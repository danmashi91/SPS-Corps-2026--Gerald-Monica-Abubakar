# tools/scoring.py
# Mode 1 — Deterministic Scoring Engine
# Computes risk score, assigns risk tier, determines base triage recommendation,
# and detects borderline cases. All logic is rule-based and fully reproducible.

# ---------------------------------------------------------------------------
# Scoring Configuration
# These thresholds should be tuned during Week 1 of implementation.
# They are defined here as named constants — never use magic numbers in scoring logic.
# ---------------------------------------------------------------------------

# Feature weights for risk score computation (must sum to 1.0)
WEIGHT_CREDIT_SCORE = 0.45
WEIGHT_DTI_RATIO = 0.30
WEIGHT_DELINQUENCIES = 0.25
WEIGHT_INCOME_TO_LOAN = 0.00

ESCALATION_THRESHOLD = 38.0
BORDERLINE_MARGIN = 10.0
TIER_LOW_MAX = 22.0
TIER_MODERATE_MAX = 55.0     # i.e., scores in range [37, 53] are borderline


# ---------------------------------------------------------------------------
# Scoring Functions
# ---------------------------------------------------------------------------

def _normalize_credit_score(credit_score: int) -> float:
    """
    Convert credit score (300–850) to a risk contribution (0–100).
    Higher credit score = lower risk contribution.
    """
    # Invert: 850 (best) → 0 risk, 300 (worst) → 100 risk
    return ((850 - credit_score) / (850 - 300)) * 100


def _normalize_dti(dti_ratio: float) -> float:
    """
    Convert DTI ratio (0.0–1.0) to a risk contribution (0–100).
    Higher DTI = higher risk.
    """
    return dti_ratio * 100


def _normalize_delinquencies(recent_delinquencies: int) -> float:
    """
    Convert delinquency count to a risk contribution (0–100).
    Capped at 5 delinquencies = maximum risk.
    """
    return min(recent_delinquencies / 5, 1.0) * 100


def _normalize_income_to_loan(monthly_income: float, loan_amount_requested: float) -> float:
    """
    Compute loan-to-income risk contribution (0–100).
    Higher loan relative to income = higher risk.
    Assumes monthly income; annualizes for ratio computation.
    """
    annual_income = monthly_income * 12
    if annual_income <= 0:
        return 100.0
    ratio = loan_amount_requested / annual_income
    # Cap at ratio of 5x annual income = maximum risk
    return min(ratio / 5.0, 1.0) * 100


def compute_risk_score(validated_input: dict) -> float:
    """
    Compute a weighted risk score (0–100) from validated input fields.
    Higher score = higher risk.

    Args:
        validated_input: Cleaned input dict from validator.py

    Returns:
        Float risk score between 0.0 and 100.0
    """
    credit_risk = _normalize_credit_score(validated_input["credit_score"])
    dti_risk = _normalize_dti(validated_input["debt_to_income_ratio"])
    delinquency_risk = _normalize_delinquencies(validated_input["recent_delinquencies"])
    income_loan_risk = _normalize_income_to_loan(
        validated_input["monthly_income"],
        validated_input["loan_amount_requested"]
    )

    risk_score = (
        WEIGHT_CREDIT_SCORE * credit_risk +
        WEIGHT_DTI_RATIO * dti_risk +
        WEIGHT_DELINQUENCIES * delinquency_risk +
        WEIGHT_INCOME_TO_LOAN * income_loan_risk
    )

    return round(risk_score, 2)


def assign_risk_tier(risk_score: float) -> str:
    """
    Assign a discrete risk tier based on computed risk score.

    Returns:
        "Low" / "Moderate" / "High"
    """
    if risk_score <= TIER_LOW_MAX:
        return "Low"
    elif risk_score <= TIER_MODERATE_MAX:
        return "Moderate"
    else:
        return "High"


def determine_base_recommendation(risk_score: float) -> str:
    """
    Determine base triage recommendation using the escalation threshold.

    Returns:
        "escalate_to_underwriting" / "recommend_decline"
    """
    if risk_score <= ESCALATION_THRESHOLD:
        return "escalate_to_underwriting"
    else:
        return "recommend_decline"


def detect_borderline(risk_score: float) -> bool:
    """
    Flag applications that fall within the borderline margin around
    the escalation threshold. These are routed to Mode 2 (LLM reasoning).

    Returns:
        True if borderline, False otherwise
    """
    lower = ESCALATION_THRESHOLD - BORDERLINE_MARGIN
    upper = ESCALATION_THRESHOLD + BORDERLINE_MARGIN
    return lower <= risk_score <= upper


def run_scoring_engine(validated_input: dict) -> dict:
    """
    Run the full Mode 1 scoring pipeline on validated input.
    Returns a dict containing all scoring outputs for the AgentState.

    Args:
        validated_input: Cleaned input dict from validator.py

    Returns:
        Dict with keys: risk_score, risk_tier, triage_recommendation, borderline_flag
    """
    risk_score = compute_risk_score(validated_input)
    risk_tier = assign_risk_tier(risk_score)
    triage_recommendation = determine_base_recommendation(risk_score)
    borderline_flag = detect_borderline(risk_score)

    return {
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "triage_recommendation": triage_recommendation,
        "borderline_flag": borderline_flag,
    }