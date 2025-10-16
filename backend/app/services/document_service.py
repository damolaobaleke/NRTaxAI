"""
Document Upload and Processing Service
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

from app.core.database import get_database
from app.services.s3_service import s3_service
from app.services.av_scanner import av_scanner
from app.models.tax_return import DocumentCreate, DocumentUpdate
from app.models.common import DocumentType
from sqlalchemy import text

logger = structlog.get_logger()


class DocumentService:
    """Document upload and processing service"""
    
    def __init__(self, db):
        self.db = db
    
    async def request_upload_url(
        self,
        user_id: str,
        document_type: str,
        return_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Request pre-signed URL for document upload
        
        Args:
            user_id: User ID
            document_type: Type of document (W2, 1099INT, etc.)
            return_id: Associated tax return ID
            
        Returns:
            Upload URL and metadata
        """
        try:
            # Validate document type
            if document_type not in [dt.value for dt in DocumentType]:
                raise ValueError(f"Invalid document type: {document_type}")
            
            # Generate unique file extension (default to PDF)
            file_extension = "pdf"
            
            # Generate pre-signed upload URL
            upload_data = await s3_service.generate_presigned_upload_url(
                user_id=user_id,
                document_type=document_type,
                file_extension=file_extension,
                expires_in=3600  # 1 hour
            )
            
            # Create document record in database
            document_id = await self.db.fetch_one(
                """
                INSERT INTO documents (
                    id, user_id, return_id, s3_key, doc_type, status
                )
                VALUES (
                    :id, :user_id, :return_id, :s3_key, :doc_type, 'uploading'
                )
                RETURNING id
                """,
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "return_id": return_id,
                    "s3_key": upload_data["file_key"],
                    "doc_type": document_type
                }
            )
            
            # Log upload request
            logger.info("Upload URL generated", 
                       user_id=user_id, 
                       document_type=document_type,
                       document_id=document_id["id"])
            
            return {
                "document_id": document_id["id"],
                "upload_url": upload_data["upload_url"],
                "fields": upload_data["fields"],
                "file_key": upload_data["file_key"],
                "expires_at": upload_data["expires_at"].isoformat(),
                "document_type": document_type,
                "status": "uploading"
            }
            
        except Exception as e:
            logger.error("Upload URL generation failed", error=str(e), user_id=user_id)
            raise Exception(f"Failed to generate upload URL: {str(e)}")
    
    async def confirm_upload(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Confirm document upload and initiate processing
        
        Args:
            document_id: Document ID
            user_id: User ID for verification
            
        Returns:
            Upload confirmation result
        """
        try:
            # Get document record
            document = await self.db.fetch_one(
                """
                SELECT * FROM documents 
                WHERE id = :document_id AND user_id = :user_id
                """,
                {"document_id": document_id, "user_id": user_id}
            )
            
            if not document:
                raise ValueError("Document not found or access denied")
            
            # Check if file exists in S3
            try:
                file_metadata = await s3_service.get_file_metadata(document["s3_key"])
            except Exception as e:
                logger.error("File not found in S3", error=str(e), document_id=document_id)
                raise Exception("Uploaded file not found")
            
            # Update document status
            await self.db.execute(
                """
                UPDATE documents 
                SET status = 'uploaded', 
                    source = 'user_upload',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :document_id
                """,
                {"document_id": document_id}
            )
            
            # Initiate AV scan
            scan_result = await av_scanner.scan_file(document["s3_key"])
            
            # Update document with scan result
            await self.db.execute(
                """
                UPDATE documents 
                SET status = :status,
                    validation_json = :validation_json
                WHERE id = :document_id
                """,
                {
                    "document_id": document_id,
                    "status": "clean" if scan_result.get("clean") else "quarantined",
                    "validation_json": json.dumps({
                        "av_scan": scan_result,
                        "file_metadata": file_metadata
                    })
                }
            )
            
            # If file is infected, quarantine it
            if not scan_result.get("clean", False) and scan_result.get("threats_detected", 0) > 0:
                quarantine_result = await av_scanner.quarantine_file(
                    document["s3_key"],
                    reason="malware_detected"
                )
                
                await self.db.execute(
                    """
                    UPDATE documents 
                    SET status = 'quarantined',
                        validation_json = :validation_json
                    WHERE id = :document_id
                    """,
                    {
                        "document_id": document_id,
                        "validation_json": json.dumps({
                            "av_scan": scan_result,
                            "quarantine": quarantine_result,
                            "file_metadata": file_metadata
                        })
                    }
                )
                
                logger.warning("Document quarantined", 
                              document_id=document_id, 
                              threats=scan_result.get("threats_detected", 0))
            
            # Log successful upload
            logger.info("Document upload confirmed", 
                       document_id=document_id,
                       file_size=file_metadata.get("size_bytes", 0),
                       clean=scan_result.get("clean", False))
            
            return {
                "document_id": document_id,
                "status": "clean" if scan_result.get("clean") else "quarantined",
                "file_size_bytes": file_metadata.get("size_bytes", 0),
                "av_scan_result": scan_result,
                "ready_for_processing": scan_result.get("clean", False)
            }
            
        except Exception as e:
            logger.error("Upload confirmation failed", error=str(e), document_id=document_id)
            raise Exception(f"Failed to confirm upload: {str(e)}")
    
    async def get_document(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get document information
        
        Args:
            document_id: Document ID
            user_id: User ID for verification
            
        Returns:
            Document information
        """
        try:
            document = await self.db.fetch_one(
                """
                SELECT * FROM documents 
                WHERE id = :document_id AND user_id = :user_id
                """,
                {"document_id": document_id, "user_id": user_id}
            )
            
            if not document:
                raise ValueError("Document not found or access denied")
            
            # Get file metadata from S3
            try:
                file_metadata = await s3_service.get_file_metadata(document["s3_key"])
            except Exception as e:
                logger.warning("File metadata not available", error=str(e))
                file_metadata = {}
            
            # Parse validation JSON
            validation_data = {}
            if document.get("validation_json"):
                try:
                    validation_data = json.loads(document["validation_json"])
                except json.JSONDecodeError:
                    pass
            
            return {
                "document_id": document["id"],
                "user_id": document["user_id"],
                "return_id": document["return_id"],
                "s3_key": document["s3_key"],
                "doc_type": document["doc_type"],
                "status": document["status"],
                "source": document["source"],
                "file_metadata": file_metadata,
                "validation_data": validation_data,
                "created_at": document["created_at"].isoformat() if document["created_at"] else None
            }
            
        except Exception as e:
            logger.error("Document retrieval failed", error=str(e), document_id=document_id)
            raise Exception(f"Failed to get document: {str(e)}")
    
    async def list_documents(
        self,
        user_id: str,
        return_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List documents for user
        
        Args:
            user_id: User ID
            return_id: Filter by return ID
            status: Filter by status
            
        Returns:
            List of documents
        """
        try:
            # Build query
            query = """
                SELECT * FROM documents 
                WHERE user_id = :user_id
            """
            params = {"user_id": user_id}
            
            if return_id:
                query += " AND return_id = :return_id"
                params["return_id"] = return_id
            
            if status:
                query += " AND status = :status"
                params["status"] = status
            
            query += " ORDER BY created_at DESC"
            
            documents = await self.db.fetch_all(query, params)
            
            result = []
            for doc in documents:
                # Parse validation JSON
                validation_data = {}
                if doc.get("validation_json"):
                    try:
                        validation_data = json.loads(doc["validation_json"])
                    except json.JSONDecodeError:
                        pass
                
                result.append({
                    "document_id": doc["id"],
                    "user_id": doc["user_id"],
                    "return_id": doc["return_id"],
                    "s3_key": doc["s3_key"],
                    "doc_type": doc["doc_type"],
                    "status": doc["status"],
                    "source": doc["source"],
                    "validation_data": validation_data,
                    "created_at": doc["created_at"].isoformat() if doc["created_at"] else None
                })
            
            return result
            
        except Exception as e:
            logger.error("Document listing failed", error=str(e), user_id=user_id)
            raise Exception(f"Failed to list documents: {str(e)}")
    
    async def delete_document(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Delete document
        
        Args:
            document_id: Document ID
            user_id: User ID for verification
            
        Returns:
            Deletion result
        """
        try:
            # Get document record
            document = await self.db.fetch_one(
                """
                SELECT * FROM documents 
                WHERE id = :document_id AND user_id = :user_id
                """,
                {"document_id": document_id, "user_id": user_id}
            )
            
            if not document:
                raise ValueError("Document not found or access denied")
            
            # Delete from S3
            await s3_service.delete_file(document["s3_key"])
            
            # Delete from database
            await self.db.execute(
                "DELETE FROM documents WHERE id = :document_id",
                {"document_id": document_id}
            )
            
            logger.info("Document deleted", document_id=document_id, user_id=user_id)
            
            return {
                "deleted": True,
                "document_id": document_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Document deletion failed", error=str(e), document_id=document_id)
            raise Exception(f"Failed to delete document: {str(e)}")
    
    async def get_download_url(
        self,
        document_id: str,
        user_id: str,
        expires_in: int = 3600
    ) -> Dict[str, Any]:
        """
        Get secure download URL for document
        
        Args:
            document_id: Document ID
            user_id: User ID for verification
            expires_in: URL expiration time in seconds
            
        Returns:
            Download URL and metadata
        """
        try:
            # Get document record
            document = await self.db.fetch_one(
                """
                SELECT * FROM documents 
                WHERE id = :document_id AND user_id = :user_id
                """,
                {"document_id": document_id, "user_id": user_id}
            )
            
            if not document:
                raise ValueError("Document not found or access denied")
            
            # Check if document is clean
            if document["status"] == "quarantined":
                raise ValueError("Document is quarantined and cannot be downloaded")
            
            # Generate pre-signed download URL
            download_url = await s3_service.generate_presigned_download_url(
                document["s3_key"],
                expires_in=expires_in
            )
            
            logger.info("Download URL generated", 
                       document_id=document_id, 
                       user_id=user_id,
                       expires_in=expires_in)
            
            return {
                "download_url": download_url,
                "document_id": document_id,
                "doc_type": document["doc_type"],
                "expires_in": expires_in,
                "expires_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Download URL generation failed", error=str(e), document_id=document_id)
            raise Exception(f"Failed to generate download URL: {str(e)}")


async def get_document_service():
    """Get document service instance"""
    db = await get_database()
    return DocumentService(db)
