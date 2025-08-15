from __future__ import annotations

from typing import Dict, Any, Iterable


def compute_weighted_progress(
    tasks: Iterable[dict],
    kpis: Iterable[dict],
) -> Dict[str, Any]:
    """
    Compute KPI-weighted progress. Inputs are simple dicts to keep it testable.

    tasks: iterable of { 'final_score': float, 'kpi_id': int, 'completion_date': str|None }
    kpis: iterable of { 'id': int, 'name': str, 'weight': float }
    """
    kpi_by_id = {k['id']: k for k in kpis}
    grouped: Dict[int, list] = {}
    for t in tasks:
        kpi_id = t.get('kpi_id')
        if not kpi_id or kpi_id not in kpi_by_id:
            continue
        if t.get('final_score') is None:
            continue
        grouped.setdefault(kpi_id, []).append(float(t['final_score']))

    breakdown = {}
    total_weighted = 0.0
    total_weight = 0.0

    for kpi in kpis:
        scores = grouped.get(kpi['id'], [])
        if scores:
            avg = sum(scores) / len(scores)
            weighted = (avg * kpi['weight']) / 100.0
            breakdown[kpi['name']] = {
                'kpi_id': kpi['id'],
                'weight': kpi['weight'],
                'task_count': len(scores),
                'average_score': round(avg, 2),
                'weighted_score': round(weighted, 2),
            }
            total_weighted += weighted
            total_weight += kpi['weight']
        else:
            breakdown[kpi['name']] = {
                'kpi_id': kpi['id'],
                'weight': kpi['weight'],
                'task_count': 0,
                'average_score': 0,
                'weighted_score': 0,
            }
            total_weight += kpi['weight']

    total_progress = (total_weighted / total_weight) * 100 if total_weight > 0 else 0.0

    return {
        'total_progress_score': round(total_progress, 2),
        'progress_breakdown': breakdown,
        'total_weight': total_weight,
    }


