from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from django.utils import timezone
from core.utils.dates import business_localdate
from typing import Optional, Dict, Any
import logging


@dataclass(frozen=True)
class TaskEvaluationInput:
    quality_percentage: Optional[float]
    priority_multiplier: Optional[float]
    completion_date: Optional[date]
    target_date: Optional[date]
    percentage_completion: Optional[float]


@dataclass(frozen=True)
class EvaluationSettings:
    use_quality_score: bool
    use_priority_multiplier: bool
    use_time_bonus_penalty: bool
    use_manager_closure_penalty: bool
    early_completion_bonus_per_day: float
    max_early_completion_bonus: float
    late_completion_penalty_per_day: float
    max_late_completion_penalty: float
    manager_closure_penalty: float


def compute_status(percentage_completion: Optional[float], target_date: Optional[date]) -> str:
    if (percentage_completion or 0) >= 100:
        return 'closed'
    if target_date and target_date < business_localdate():
        return 'due'
    return 'open'


def compute_automatic_evaluation(
    data: TaskEvaluationInput,
    settings: EvaluationSettings,
    manager_closure: bool = False,
) -> Optional[Dict[str, Any]]:
    if data.quality_percentage is None:
        return None

    # Quality score
    quality_score = data.quality_percentage if settings.use_quality_score else 0

    # Priority multiplier
    priority_multiplier = data.priority_multiplier if (settings.use_priority_multiplier and data.priority_multiplier) else 1.0

    # Time bonus/penalty
    time_bonus_penalty = 0.0
    if settings.use_time_bonus_penalty and data.completion_date and data.target_date:
        completion = data.completion_date
        target = data.target_date
        if completion < target:
            days_early = (target - completion).days
            time_bonus_penalty = min(days_early * settings.early_completion_bonus_per_day, settings.max_early_completion_bonus)
        elif completion > target:
            days_late = (completion - target).days
            time_bonus_penalty = -min(days_late * settings.late_completion_penalty_per_day, settings.max_late_completion_penalty)

    manager_closure_penalty_applied = False
    if settings.use_manager_closure_penalty and manager_closure and (data.percentage_completion or 0) < 100:
        time_bonus_penalty -= settings.manager_closure_penalty
        manager_closure_penalty_applied = True

    base_score = quality_score * priority_multiplier
    final_score = max(0.0, min(100.0, base_score + time_bonus_penalty))

    result = {
        'quality_score': quality_score,
        'priority_multiplier': priority_multiplier,
        'time_bonus_penalty': time_bonus_penalty,
        'final_score': final_score,
        'manager_closure_penalty_applied': manager_closure_penalty_applied,
    }

    # --- Audit logging (non-invasive) ---
    try:
        audit_logger = logging.getLogger('core.audit')
        audit_logger.info(
            'task_eval_computed manager_closure=%s quality_score=%s priority_multiplier=%s '
            'time_bonus_penalty=%s final_score=%s completion_date=%s target_date=%s percentage_completion=%s',
            bool(manager_closure),
            result['quality_score'],
            result['priority_multiplier'],
            result['time_bonus_penalty'],
            result['final_score'],
            getattr(data, 'completion_date', None),
            getattr(data, 'target_date', None),
            getattr(data, 'percentage_completion', None),
        )
    except Exception:
        pass

    return result


