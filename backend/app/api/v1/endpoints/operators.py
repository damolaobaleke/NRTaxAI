"""
Operator Endpoints for PTIN Holders
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_database
from app.services.operator_service import get_operator_service
from app.models.operator import OperatorInDB
from sqlalchemy import text

router = APIRouter()


class ReviewSubmission(BaseModel):
    decision: str  # approved, rejected, needs_revision
    comments: Optional[str] = None
    diffs: Optional[dict] = None


class RevisionRequest(BaseModel):
    revision_items: List[dict]
    comments: str


# Dependency to get current operator
async def get_current_operator(
    operator_id: str,  # In production, extract from JWT token
    db = Depends(get_database)
) -> OperatorInDB:
    """Get current authenticated operator"""
    # TODO: Implement proper operator authentication
    # For now, simple lookup
    result = await db.execute(
    text("SELECT * FROM operators WHERE id = :operator_id"),
    {"operator_id": operator_id}
    )
    operator = result.fetchone()
    
    if not operator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operator not found"
        )
    
    return OperatorInDB(**operator)


@router.get("/queue")
async def get_review_queue(
    status_filter: Optional[str] = None,
    operator_id: str = "dummy-operator-id"  # TODO: Get from auth token
):
    """Get review queue for operator"""
    
    try:
        operator_service = await get_operator_service()
        
        queue = await operator_service.get_review_queue(
            operator_id=operator_id,
            status_filter=status_filter
        )
        
        return {
            "queue": queue,
            "total_items": len(queue)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review queue: {str(e)}"
        )


@router.get("/returns/{return_id}")
async def get_return_for_review(
    return_id: UUID,
    operator_id: str = "dummy-operator-id"  # TODO: Get from auth token
):
    """Get complete tax return for review"""
    
    try:
        operator_service = await get_operator_service()
        
        return_data = await operator_service.get_return_for_review(
            return_id=str(return_id),
            operator_id=operator_id
        )
        
        return return_data
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get return for review: {str(e)}"
        )


@router.post("/returns/{return_id}/review")
async def submit_review(
    return_id: UUID,
    review: ReviewSubmission,
    operator_id: str = "dummy-operator-id"  # TODO: Get from auth token
):
    """Submit review decision"""
    
    try:
        operator_service = await get_operator_service()
        
        result = await operator_service.submit_review(
            return_id=str(return_id),
            operator_id=operator_id,
            decision=review.decision,
            comments=review.comments,
            diffs=review.diffs
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review: {str(e)}"
        )


@router.post("/returns/{return_id}/approve")
async def approve_return(
    return_id: UUID,
    comments: Optional[str] = None,
    operator_id: str = "dummy-operator-id"  # TODO: Get from auth token
):
    """Approve tax return and generate Form 8879"""
    
    try:
        operator_service = await get_operator_service()
        
        result = await operator_service.approve_return(
            return_id=str(return_id),
            operator_id=operator_id,
            comments=comments
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve return: {str(e)}"
        )


@router.post("/returns/{return_id}/request-revision")
async def request_revision(
    return_id: UUID,
    request: RevisionRequest,
    operator_id: str = "dummy-operator-id"  # TODO: Get from auth token
):
    """Request revisions to tax return"""
    
    try:
        operator_service = await get_operator_service()
        
        result = await operator_service.request_revision(
            return_id=str(return_id),
            operator_id=operator_id,
            revision_items=request.revision_items,
            comments=request.comments
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to request revision: {str(e)}"
        )


@router.get("/stats")
async def get_operator_stats(
    operator_id: str = "dummy-operator-id"  # TODO: Get from auth token
):
    """Get operator statistics"""
    
    try:
        operator_service = await get_operator_service()
        
        stats = await operator_service.get_operator_stats(operator_id)
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get operator stats: {str(e)}"
        )
