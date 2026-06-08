from typing import Optional

try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False
    print("mlflow not installed — experiment tracking disabled")

from app.core.config import settings

_CONFIDENCE_SCORE = {"High": 1.0, "Medium": 0.5, "Low": 0.0}


def log_triage_run(triage_data: dict, message: str) -> Optional[str]:
    """
    Log a triage result to MLflow as a new experiment run.
    Returns the MLflow run_id, or None if logging is disabled or fails.
    Non-blocking — errors are caught and printed, never raised.
    """
    if not _MLFLOW_AVAILABLE:
        return None

    tracking_uri = settings.MLFLOW_TRACKING_URI
    if not tracking_uri:
        return None

    try:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("customer-triage")

        with mlflow.start_run() as run:
            mlflow.log_params({
                "category": str(triage_data.get("category", ""))[:250],
                "urgency": str(triage_data.get("urgency", ""))[:250],
                "sentiment": str(triage_data.get("sentiment", ""))[:250],
                "suggested_owner": str(triage_data.get("suggested_owner", ""))[:250],
                "confidence": str(triage_data.get("confidence", ""))[:250],
            })
            mlflow.log_metrics({
                "confidence_score": _CONFIDENCE_SCORE.get(
                    triage_data.get("confidence", ""), 0.5
                ),
                "abusive_flag": float(int(triage_data.get("abusive_flag", False))),
                "message_length": float(len(message)),
            })
            mlflow.set_tags({
                "abusive": str(triage_data.get("abusive_flag", False)),
                "category": str(triage_data.get("category", "")),
            })
            return run.info.run_id

    except Exception as exc:
        print(f"MLflow logging failed (non-blocking): {exc}")
        return None
