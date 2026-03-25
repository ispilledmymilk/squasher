# backend/api/routes/metrics.py

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import client_error_detail, verify_api_key
from data.metrics_store import MetricsStore
from utils.config import config
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(dependencies=[Depends(verify_api_key)])

metrics_store = MetricsStore()


class MetricsResponse(BaseModel):
    file_path: str
    timestamp: datetime
    cyclomatic_complexity: Optional[float]
    lines_of_code: Optional[int]
    maintainability_index: Optional[float]
    change_frequency: Optional[int]


@router.get(
    "/file/{file_path:path}",
    response_model=List[MetricsResponse],
)
async def get_file_metrics(file_path: str, limit: int = 10):
    """Get historical metrics for a file"""
    if len(file_path) > config.MAX_PATH_LENGTH:
        raise HTTPException(status_code=400, detail="Path too long")
    try:
        metrics = metrics_store.get_file_history(file_path, limit=limit)
        return [
            MetricsResponse(
                file_path=m.file_path,
                timestamp=m.timestamp,
                cyclomatic_complexity=m.cyclomatic_complexity,
                lines_of_code=m.lines_of_code,
                maintainability_index=m.maintainability_index,
                change_frequency=m.change_frequency,
            )
            for m in metrics
        ]
    except Exception as e:
        logger.exception("Error fetching metrics")
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Failed to fetch metrics", e),
        )


@router.get("/high-risk")
async def get_high_risk_files(threshold: float = 70.0):
    """Get files with high decay scores"""
    try:
        predictions = metrics_store.get_high_risk_files(threshold=threshold)
        results = []
        for pred in predictions:
            results.append(
                {
                    "file_path": pred.file_path,
                    "decay_score": pred.decay_score,
                    "risk_level": pred.risk_level,
                    "timestamp": pred.timestamp.isoformat(),
                    "predicted_issues": pred.predicted_issues,
                    "recommendations": pred.recommendations or [],
                }
            )
        return {
            "threshold": threshold,
            "count": len(results),
            "files": results,
        }
    except Exception as e:
        logger.exception("Error fetching high-risk files")
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Failed to fetch high-risk files", e),
        )


@router.get("/summary")
async def get_summary():
    """Get overall metrics summary"""
    try:
        high_risk = metrics_store.get_high_risk_files(threshold=60.0)
        total_files = len(high_risk)
        critical_count = sum(
            1 for p in high_risk if p.risk_level == "critical"
        )
        high_count = sum(1 for p in high_risk if p.risk_level == "high")
        medium_count = sum(1 for p in high_risk if p.risk_level == "medium")
        avg_decay_score = (
            sum(p.decay_score for p in high_risk) / total_files
            if total_files > 0
            else 0
        )
        return {
            "total_files_analyzed": total_files,
            "risk_distribution": {
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
            },
            "average_decay_score": round(avg_decay_score, 2),
        }
    except Exception as e:
        logger.exception("Error generating summary")
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Failed to generate summary", e),
        )
