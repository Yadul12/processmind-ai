"""
EvalGuard Extraction Quality Adapter REST Endpoint.
Provides extraction precision, recall, F1, actor accuracy, dependency accuracy,
decision condition accuracy, schema validation pass rate, and source citation correctness.
"""

from fastapi import APIRouter

from backend.schemas.evaluation import EvalGuardSuiteReport
from backend.services.evalguard_adapter import evalguard_adapter

router = APIRouter(prefix="/api/evaluations", tags=["Evaluations"])

_cached_report: EvalGuardSuiteReport | None = None


@router.get("/report", response_model=EvalGuardSuiteReport)
def get_evaluation_report(refresh: bool = False) -> EvalGuardSuiteReport:
    global _cached_report
    if _cached_report is None or refresh:
        _cached_report = evalguard_adapter.run_full_evaluation_suite()
    return _cached_report
