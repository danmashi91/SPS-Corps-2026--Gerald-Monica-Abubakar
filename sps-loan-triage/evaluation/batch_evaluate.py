# evaluation/batch_evaluate.py
# Runs the loan triage pipeline against the prepared evaluation dataset.
# Measures accuracy, borderline-case performance, false rates, and latency.
# Produces a structured evaluation report.
# Run prepare_dataset.py first before running this script.

import sys
import os
import json
import time
import pandas as pd
from datetime import datetime, timezone

# Add src directory to path for pipeline imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orchestrator import run_pipeline

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "evaluation_dataset.csv")
RESULTS_DIR  = os.path.join(os.path.dirname(__file__), "results")
REPORT_PATH  = os.path.join(RESULTS_DIR, "evaluation_report.json")
DETAIL_PATH  = os.path.join(RESULTS_DIR, "evaluation_detail.csv")


# ---------------------------------------------------------------------------
# Ground Truth Mapping
# ---------------------------------------------------------------------------
# Kaggle ground truth: 1 = serious delinquency (high risk) → recommend_decline
#                      0 = no delinquency (good applicant) → escalate_to_underwriting

def ground_truth_to_recommendation(ground_truth: int) -> str:
    if ground_truth == 1:
        return "recommend_decline"
    return "escalate_to_underwriting"


# ---------------------------------------------------------------------------
# Batch Runner
# ---------------------------------------------------------------------------

def run_batch_evaluation(
    max_rows: int = 100,
    no_llm: bool = True,
    verbose: bool = True
) -> dict:
    """
    Run pipeline against evaluation dataset and compute metrics.

    Args:
        max_rows: Maximum number of rows to evaluate (keep small for speed)
        no_llm:   If True, run deterministic mode only (faster for bulk eval)
        verbose:  Print progress to console

    Returns:
        Evaluation report dict
    """
    print(f"\n{'='*60}")
    print(f"  LOAN TRIAGE BATCH EVALUATION")
    print(f"{'='*60}")
    print(f"  Dataset:  {DATASET_PATH}")
    print(f"  Max rows: {max_rows}")
    print(f"  LLM mode: {'disabled (deterministic only)' if no_llm else 'enabled'}")
    print(f"{'='*60}\n")

    # Load dataset
    if not os.path.exists(DATASET_PATH):
        print("ERROR: Dataset not found. Run prepare_dataset.py first.")
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH).head(max_rows)
    print(f"Loaded {len(df)} cases for evaluation\n")

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # ---------------------------------------------------------------------------
    # Run pipeline for each case
    # ---------------------------------------------------------------------------
    results = []
    latencies = []

    for i, row in df.iterrows():
        application_input = {
            "credit_score": int(row["credit_score"]),
            "monthly_income": float(row["monthly_income"]),
            "debt_to_income_ratio": float(row["debt_to_income_ratio"]),
            "recent_delinquencies": int(row["recent_delinquencies"]),
            "loan_amount_requested": float(row["loan_amount_requested"]),
        }

        if no_llm:
            application_input["_no_llm_mode"] = True

        expected = ground_truth_to_recommendation(int(row["ground_truth"]))

        start = time.time()
        try:
            output = run_pipeline(application_input)
            latency = time.time() - start

            predicted = output.get("triage_recommendation", "error")
            borderline = output.get("borderline_flag", False)
            error = output.get("error_flag", False)
            risk_tier = output.get("risk_tier", "unknown")
            risk_score = output.get("risk_score", 0)

            correct = predicted == expected and not error

            results.append({
                "case_id": i,
                "credit_score": application_input["credit_score"],
                "monthly_income": application_input["monthly_income"],
                "debt_to_income_ratio": application_input["debt_to_income_ratio"],
                "recent_delinquencies": application_input["recent_delinquencies"],
                "loan_amount_requested": application_input["loan_amount_requested"],
                "ground_truth": row["ground_truth"],
                "expected_recommendation": expected,
                "predicted_recommendation": predicted,
                "risk_score": risk_score,
                "risk_tier": risk_tier,
                "borderline_flag": borderline,
                "correct": correct,
                "error_flag": error,
                "latency_seconds": round(latency, 3),
            })
            latencies.append(latency)

        except Exception as e:
            latency = time.time() - start
            results.append({
                "case_id": i,
                "ground_truth": row["ground_truth"],
                "expected_recommendation": expected,
                "predicted_recommendation": "error",
                "correct": False,
                "error_flag": True,
                "latency_seconds": round(latency, 3),
                "error_message": str(e),
            })

        if verbose and (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(df)} cases...")

    # ---------------------------------------------------------------------------
    # Compute Metrics
    # ---------------------------------------------------------------------------
    results_df = pd.DataFrame(results)
    results_df.to_csv(DETAIL_PATH, index=False)

    total = len(results_df)
    correct = results_df["correct"].sum()
    errors = results_df["error_flag"].sum()

    # Overall accuracy
    overall_accuracy = correct / total if total > 0 else 0

    # Borderline case accuracy
    borderline_df = results_df[results_df.get("borderline_flag", False) == True]
    borderline_accuracy = (
        borderline_df["correct"].sum() / len(borderline_df)
        if len(borderline_df) > 0 else None
    )

    # False escalation rate (escalated when should have declined)
    should_decline = results_df[results_df["expected_recommendation"] == "recommend_decline"]
    false_escalations = should_decline[
        should_decline["predicted_recommendation"] == "escalate_to_underwriting"
    ]
    false_escalation_rate = (
        len(false_escalations) / len(should_decline)
        if len(should_decline) > 0 else 0
    )

    # False decline rate (declined when should have escalated)
    should_escalate = results_df[results_df["expected_recommendation"] == "escalate_to_underwriting"]
    false_declines = should_escalate[
        should_escalate["predicted_recommendation"] == "recommend_decline"
    ]
    false_decline_rate = (
        len(false_declines) / len(should_escalate)
        if len(should_escalate) > 0 else 0
    )

    # Latency
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0

    # Tier distribution
    tier_dist = results_df["risk_tier"].value_counts().to_dict() if "risk_tier" in results_df else {}

    # ---------------------------------------------------------------------------
    # Build Report
    # ---------------------------------------------------------------------------
    report = {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "total_cases": total,
            "llm_enabled": not no_llm,
            "dataset": DATASET_PATH,
        },
        "metrics": {
            "overall_accuracy": round(overall_accuracy, 4),
            "borderline_case_accuracy": round(borderline_accuracy, 4) if borderline_accuracy is not None else "N/A",
            "false_escalation_rate": round(false_escalation_rate, 4),
            "false_decline_rate": round(false_decline_rate, 4),
            "error_rate": round(errors / total, 4) if total > 0 else 0,
            "borderline_cases_count": len(borderline_df),
        },
        "latency": {
            "average_seconds": round(avg_latency, 3),
            "max_seconds": round(max_latency, 3),
        },
        "distribution": {
            "risk_tiers": tier_dist,
            "correct": int(correct),
            "incorrect": int(total - correct - errors),
            "errors": int(errors),
        }
    }

    # Save report
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    # ---------------------------------------------------------------------------
    # Print Summary
    # ---------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"  EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"  Total Cases:            {total}")
    print(f"  Overall Accuracy:       {overall_accuracy:.1%}")
    print(f"  Borderline Accuracy:    {borderline_accuracy:.1%}" if borderline_accuracy is not None else "  Borderline Accuracy:    N/A")
    print(f"  False Escalation Rate:  {false_escalation_rate:.1%}")
    print(f"  False Decline Rate:     {false_decline_rate:.1%}")
    print(f"  Avg Latency:            {avg_latency:.3f}s")
    print(f"  Borderline Cases:       {len(borderline_df)}")
    print(f"  Errors:                 {errors}")
    print(f"{'='*60}")
    print(f"  Report saved to: {REPORT_PATH}")
    print(f"  Detail saved to: {DETAIL_PATH}")
    print(f"{'='*60}\n")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch evaluate the loan triage pipeline")
    parser.add_argument("--rows", type=int, default=100, help="Number of cases to evaluate")
    parser.add_argument("--llm", action="store_true", help="Enable LLM reasoning (slower)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    report = run_batch_evaluation(
        max_rows=args.rows,
        no_llm=not args.llm,
        verbose=not args.quiet
    )
