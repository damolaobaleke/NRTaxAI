"""
Monitoring and Health Check Endpoints
"""

from fastapi import APIRouter, Depends
from datetime import datetime, timezone
import structlog
from sqlalchemy import text

from app.core.database import get_database
from app.monitoring.metrics import metrics_collector

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check(db = Depends(get_database)):
    """Detailed health check with dependency status"""
    
    health_status = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "dependencies": {}
    }
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health_status["dependencies"]["database"] = {"status": "ok"}
    except Exception as e:
        health_status["dependencies"]["database"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    return {
        "metrics": metrics_collector.get_metrics_summary(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

