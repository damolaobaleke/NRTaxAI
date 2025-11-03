"""
Documents Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.services.document_service import DocumentService
from app.models.user import UserInDB
from app.models.tax_return import Document, DocumentCreate, DocumentUpdate
from app.models.common import DocumentType

import structlog
logger = structlog.get_logger()

router = APIRouter()


@router.post("/upload")
async def request_upload_url(
    doc_type: str,
    return_id: Optional[UUID] = None,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Request pre-signed URL for document upload"""
    
    try:
        # Validate document type
        if doc_type not in [dt.value for dt in DocumentType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type. Must be one of: {[dt.value for dt in DocumentType]}"
            )
        
        document_service = DocumentService(db)

        upload_data = await document_service.request_upload_url(
            user_id=str(current_user.id),
            document_type=doc_type,
            return_id=str(return_id) if return_id else None
        )
        
        return upload_data
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Upload URL generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.post("/{document_id}/confirm")
async def confirm_upload(
    document_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Confirm document upload and initiate processing"""
    
    try:
        document_service = DocumentService(db)
        
        result = await document_service.confirm_upload(
            document_id=str(document_id),
            user_id=str(current_user.id)
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
            detail=f"Failed to confirm upload: {str(e)}"
        )


@router.post("/ingest/callback")
async def document_ingest_callback():
    """S3 event/Textract completion webhook"""
    
    # TODO: Handle S3 events and Textract completion
    return {"message": "Document ingest callback not implemented yet"}


@router.get("/", response_model=List[dict])
async def list_documents(
    return_id: Optional[UUID] = None,
    doc_status: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """List documents for current user"""
    
    try:
        document_service = DocumentService(db)
        
        documents = await document_service.list_documents(
            user_id=str(current_user.id),
            return_id=str(return_id) if return_id else None,
            status=doc_status if doc_status else None
        )
        
        return documents
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get document details"""
    
    try:
        document_service = DocumentService(db)
        
        document = await document_service.get_document(
            document_id=str(document_id),
            user_id=str(current_user.id)
        )
        
        return document
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}"
        )


@router.get("/{document_id}/download")
async def get_download_url(
    document_id: UUID,
    expires_in: int = 3600,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get secure download URL for document"""
    
    try:
        document_service = DocumentService(db)
        
        download_data = await document_service.get_download_url(
            document_id=str(document_id),
            user_id=str(current_user.id),
            expires_in=expires_in
        )
        
        return download_data
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Delete document"""
    
    try:
        document_service = DocumentService(db)
        
        result = await document_service.delete_document(
            document_id=str(document_id),
            user_id=str(current_user.id)
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
            detail=f"Failed to delete document: {str(e)}"
        )


@router.post("/{document_id}/start")
async def start_extraction(
    document_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Start OCR extraction for document"""
    
    try:
        from app.services.document_extraction_pipeline import ExtractionPipeline
        
        extraction_pipeline = ExtractionPipeline(db)
        
        result = await extraction_pipeline.start_extraction(
            document_id=str(document_id),
            user_id=str(current_user.id)
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
            detail=f"Failed to start extraction: {str(e)}"
        )


@router.get("/{document_id}/result")
async def get_extraction_result(
    document_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get extraction result for document"""
    
    try:
        from app.services.document_extraction_pipeline import ExtractionPipeline
        
        extraction_pipeline = ExtractionPipeline(db)
        
        result = await extraction_pipeline.get_extraction_status(
            document_id=str(document_id),
            user_id=str(current_user.id)
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
            detail=f"Failed to get extraction result: {str(e)}"
        )


@router.post("/{document_id}/process")
async def process_extraction_result(
    document_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Process extraction result and normalize data"""
    
    try:
        from app.services.document_extraction_pipeline import ExtractionPipeline
        
        extraction_pipeline = ExtractionPipeline(db)
        
        result = await extraction_pipeline.process_extraction_result(
            document_id=str(document_id),
            user_id=str(current_user.id)
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
            detail=f"Failed to process extraction result: {str(e)}"
        )
