"""
Document Extraction Pipeline Service
"""

import json
import re
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

from app.core.database import get_database
from app.services.textract_service import textract_service
from app.services.textract_normalizer_service import textract_normalizer
from app.services.tax_validators import tax_validator
from app.models.tax_return import DocumentUpdate
from sqlalchemy import text

logger = structlog.get_logger()


class ExtractionPipeline:
    """Orchestrates the complete document extraction pipeline"""
    
    def __init__(self, db):
        self.db = db
    
    async def start_extraction(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Start document extraction pipeline
        
        Args:
            document_id: Document ID
            user_id: User ID for verification
            
        Returns:
            Extraction start result
        """
        try:
            logger.info("Starting extraction pipeline", 
                       document_id=document_id, 
                       user_id=user_id)
            
            # Get document record
            result = await self.db.execute(
                text("""
                SELECT * FROM documents 
                WHERE id = :document_id AND user_id = :user_id
                """),
                {"document_id": document_id, "user_id": user_id}
            )
            document_row = result.fetchone()
            
            if not document_row:
                raise ValueError("Document not found or access denied")
            
            # Convert to dict if needed
            if hasattr(document_row, '_asdict'):
                document = document_row._asdict()
            else:
                # Fallback for tuples
                field_names = ['id', 'user_id', 'return_id', 's3_key', 'doc_type', 'source', 
                              'status', 'extracted_json', 'validation_json', 'created_at', 
                              'updated_at', 'textract_job_id']
                document = dict(zip(field_names, document_row))
            
            if document["status"] != "clean":
                raise ValueError(f"Document status is {document['status']}, cannot extract")
            
            # Update document status
            await self.db.execute(
                text("""
                UPDATE documents 
                SET status = 'processing',
                    textract_job_id = :job_id
                WHERE id = :document_id
                """),
                {
                    "document_id": document_id,
                    "job_id": None  # Will be updated when Textract job starts
                }
            )
            
            # Start Textract analysis
            textract_result = await textract_service.start_document_analysis(
                s3_key=document["s3_key"],
                document_type=document["doc_type"]
            )
            
            # Update document with job ID
            await self.db.execute(
                text("""
                UPDATE documents 
                SET textract_job_id = :job_id
                WHERE id = :document_id
                """),
                {
                    "document_id": document_id,
                    "job_id": textract_result["job_id"]
                }
            )
            
            logger.info("Extraction pipeline started", 
                       document_id=document_id,
                       textract_job_id=textract_result["job_id"])
            
            return {
                "document_id": document_id,
                "textract_job_id": textract_result["job_id"],
                "status": "processing",
                "started_at": textract_result["started_at"]
            }
            
        except Exception as e:
            logger.error("Extraction pipeline start failed", 
                        error=str(e), 
                        document_id=document_id)
            
            # Update document status to failed
            await self.db.execute(
                text("""
                UPDATE documents 
                SET status = 'failed'
                WHERE id = :document_id
                """),
                {"document_id": document_id}
            )
            
            raise Exception(f"Failed to start extraction: {str(e)}")
    
    async def process_extraction_result(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process extraction result and normalize data
        
        Args:
            document_id: Document ID
            user_id: User ID for verification
            
        Returns:
            Processing result
        """
        try:
            logger.info("Processing extraction result", 
                       document_id=document_id, 
                       user_id=user_id)
            
            # Get document record
            result = await self.db.execute(
                text("""
                SELECT * FROM documents 
                WHERE id = :document_id AND user_id = :user_id
                """),
                {"document_id": document_id, "user_id": user_id}
            )
            document_row = result.fetchone()
            
            if not document_row:
                raise ValueError("Document not found or access denied")
            
            # Convert to dict if needed
            if hasattr(document_row, '_asdict'):
                document = document_row._asdict()
            else:
                # Fallback for tuples
                field_names = ['id', 'user_id', 'return_id', 's3_key', 'doc_type', 'source', 
                              'status', 'extracted_json', 'validation_json', 'created_at', 
                              'updated_at', 'textract_job_id']
                document = dict(zip(field_names, document_row))
            
            if not document["textract_job_id"]:
                raise ValueError("No Textract job ID found")
            
            # Get Textract result
            textract_result = await textract_service.get_document_analysis_result(
                job_id=document["textract_job_id"]
            )
            
            if textract_result["status"] == "IN_PROGRESS":
                return {
                    "document_id": document_id,
                    "status": "processing",
                    "message": "Extraction still in progress"
                }
            
            if textract_result["status"] == "FAILED":
                # Update document status to failed
                await self.db.execute(
                    text("""
                    UPDATE documents 
                    SET status = 'failed',
                        extracted_json = :error_data
                    WHERE id = :document_id
                    """),
                    {
                        "document_id": document_id,
                        "error_data": json.dumps({
                            "error": textract_result.get("error", "Unknown error"),
                            "failed_at": datetime.utcnow().isoformat()
                        })
                    }
                )
                
                raise Exception(f"Textract analysis failed: {textract_result.get('error', 'Unknown error')}")
            
            if textract_result["status"] == "SUCCEEDED":
                # Normalize extracted data using Textract normalizer
                normalized_data = await textract_normalizer.normalize_textract_result(
                    textract_result=textract_result,
                    document_type=document["doc_type"]
                )
                
                # Validate normalized data using tax validators
                validation_results = await tax_validator.validate_document_data(
                    document_data=normalized_data,
                    document_type=document["doc_type"]
                )
                
                # Update document with extracted data
                await self.db.execute(
                    text("""
                    UPDATE documents 
                    SET status = :status,
                        extracted_json = :extracted_data,
                        validation_json = :validation_data
                    WHERE id = :document_id
                    """),
                    {
                        "document_id": document_id,
                        "status": "extracted" if validation_results["overall_valid"] else "validation_failed",
                        "extracted_data": json.dumps(normalized_data),
                        "validation_data": json.dumps(validation_results)
                    }
                )
                
                logger.info("Extraction pipeline completed", 
                           document_id=document_id,
                           status="extracted" if validation_results["overall_valid"] else "validation_failed",
                           fields_extracted=len(normalized_data.get("extracted_fields", {})),
                           confidence=normalized_data.get("confidence_scores", {}).get("overall_confidence", 0))
                
                return {
                    "document_id": document_id,
                    "status": "extracted" if validation_results["overall_valid"] else "validation_failed",
                    "extracted_data": normalized_data,
                    "validation_results": validation_results,
                    "completed_at": datetime.utcnow().isoformat()
                }
            
            return {
                "document_id": document_id,
                "status": textract_result["status"],
                "message": f"Textract status: {textract_result['status']}"
            }
            
        except Exception as e:
            logger.error("Extraction result processing failed", 
                        error=str(e), 
                        document_id=document_id)
            
            # Update document status to failed
            await self.db.execute(
                text("""
                UPDATE documents 
                SET status = 'failed'
                WHERE id = :document_id
                """),
                {"document_id": document_id}
            )
            
            raise Exception(f"Failed to process extraction result: {str(e)}")
    
    async def get_extraction_status(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get extraction status for document
        
        Args:
            document_id: Document ID
            user_id: User ID for verification
            
        Returns:
            Extraction status
        """
        try:
            # Get document record
            result = await self.db.execute(
                text("""
                SELECT * FROM documents 
                WHERE id = :document_id AND user_id = :user_id
                """),
                {"document_id": document_id, "user_id": user_id}
            )
            document_row = result.fetchone()
            
            if not document_row:
                raise ValueError("Document not found or access denied")
            
            # Convert to dict if needed
            if hasattr(document_row, '_asdict'):
                document = document_row._asdict()
            else:
                # Fallback for tuples
                field_names = ['id', 'user_id', 'return_id', 's3_key', 'doc_type', 'source', 
                              'status', 'extracted_json', 'validation_json', 'created_at', 
                              'updated_at', 'textract_job_id']
                document = dict(zip(field_names, document_row))
            
            status_info = {
                "document_id": document_id,
                "status": document["status"],
                "doc_type": document["doc_type"],
                "textract_job_id": document["textract_job_id"],
                "created_at": document["created_at"].isoformat() if document["created_at"] else None
            }
            
            # If processing, get Textract status
            if document["status"] == "processing" and document["textract_job_id"]:
                textract_result = await textract_service.get_document_analysis_result(
                    job_id=document["textract_job_id"]
                )
                status_info["textract_status"] = textract_result["status"]
                
                # If Textract completed, process the result
                if textract_result["status"] == "SUCCEEDED":
                    await self.process_extraction_result(document_id, user_id)
                    # Refresh document status
                    result = await self.db.execute(
                        text("""
                        SELECT status, extracted_json, validation_json 
                        FROM documents 
                        WHERE id = :document_id
                        """),
                        {"document_id": document_id}
                    )
                    updated_document_row = result.fetchone()
                    
                    # Convert to dict if needed
                    if hasattr(updated_document_row, '_asdict'):
                        updated_document = updated_document_row._asdict()
                    else:
                        # Fallback for tuples
                        field_names = ['status', 'extracted_json', 'validation_json']
                        updated_document = dict(zip(field_names, updated_document_row))
                    
                    status_info["status"] = updated_document["status"]
                
                elif textract_result["status"] == "FAILED":
                    status_info["status"] = "failed"
                    status_info["error"] = textract_result.get("error", "Unknown error")
            
            # Add extracted data if available
            if document.get("extracted_json"):
                try:
                    extracted_data = json.loads(document["extracted_json"])
                    status_info["extracted_data"] = extracted_data
                except json.JSONDecodeError:
                    pass
            
            # Add validation data if available
            if document.get("validation_json"):
                try:
                    validation_data = json.loads(document["validation_json"])
                    status_info["validation_data"] = validation_data
                except json.JSONDecodeError:
                    pass
            
            return status_info
            
        except Exception as e:
            logger.error("Extraction status retrieval failed", 
                        error=str(e), 
                        document_id=document_id)
            raise Exception(f"Failed to get extraction status: {str(e)}")
    
    async def _validate_extracted_data(
        self, 
        normalized_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate extracted data for completeness and accuracy
        
        Args:
            normalized_data: Normalized document data
            
        Returns:
            Validation results
        """
        try:
            validation_results = {
                "overall_valid": True,
                "validation_checks": {},
                "errors": [],
                "warnings": [],
                "validated_at": datetime.utcnow().isoformat()
            }
            
            extracted_fields = normalized_data.get("extracted_fields", {})
            confidence_scores = normalized_data.get("confidence_scores", {})
            
            # Check required fields
            required_fields = self._get_required_fields(normalized_data.get("document_type", ""))
            for field in required_fields:
                if field not in extracted_fields or not extracted_fields[field].get("value"):
                    validation_results["overall_valid"] = False
                    validation_results["errors"].append(f"Required field {field} is missing")
                    validation_results["validation_checks"][field] = {
                        "required": True,
                        "present": False,
                        "valid": False
                    }
                else:
                    validation_results["validation_checks"][field] = {
                        "required": True,
                        "present": True,
                        "valid": True
                    }
            
            # Check confidence thresholds
            overall_confidence = confidence_scores.get("overall_confidence", 0)
            if overall_confidence < 70:
                validation_results["warnings"].append(
                    f"Low overall confidence: {overall_confidence:.1f}%"
                )
            
            # Check individual field confidences
            field_confidences = confidence_scores.get("field_confidences", {})
            for field_name, field_confidence in field_confidences.items():
                if field_confidence.get("confidence", 0) < 50:
                    validation_results["warnings"].append(
                        f"Very low confidence for field {field_name}: {field_confidence.get('confidence', 0):.1f}%"
                    )
            
            # Cross-field validation
            cross_field_errors = await self._validate_cross_fields(extracted_fields)
            validation_results["errors"].extend(cross_field_errors)
            if cross_field_errors:
                validation_results["overall_valid"] = False
            
            return validation_results
            
        except Exception as e:
            logger.error("Data validation failed", error=str(e))
            return {
                "overall_valid": False,
                "validation_checks": {},
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "validated_at": datetime.utcnow().isoformat()
            }
    
    def _get_required_fields(self, document_type: str) -> List[str]:
        """Get list of required fields for document type"""
        required_fields_map = {
            "W2": ["employer_name", "employee_name", "wages", "federal_income_tax_withheld", 
                   "social_security_wages", "social_security_tax_withheld", 
                   "medicare_wages", "medicare_tax_withheld", "employee_ssn", "employer_ein"],
            "1099INT": ["payer_name", "recipient_name", "interest_income", 
                       "recipient_tin", "payer_tin"],
            "1099NEC": ["payer_name", "recipient_name", "nonemployee_compensation", 
                       "recipient_tin", "payer_tin"],
            "1098T": ["institution_name", "student_name", "tuition_paid", 
                     "student_ssn", "institution_ein"]
        }
        return required_fields_map.get(document_type, [])
    
    async def _validate_cross_fields(self, extracted_fields: Dict[str, Any]) -> List[str]:
        """Validate cross-field relationships"""
        errors = []
        
        try:
            # W-2 specific validations
            if "wages" in extracted_fields and "federal_income_tax_withheld" in extracted_fields:
                wages = self._parse_currency(extracted_fields["wages"].get("value", "0"))
                federal_tax = self._parse_currency(extracted_fields["federal_income_tax_withheld"].get("value", "0"))
                
                if wages > 0 and federal_tax > wages:
                    errors.append("Federal income tax withheld cannot exceed wages")
            
            # SSN/EIN format validation
            for field_name, field_data in extracted_fields.items():
                if field_name.endswith("_ssn") or field_name.endswith("_ein"):
                    value = field_data.get("value", "")
                    if value and not self._is_valid_tin_format(value):
                        errors.append(f"Invalid format for {field_name}: {value}")
            
            return errors
            
        except Exception as e:
            logger.error("Cross-field validation failed", error=str(e))
            return [f"Cross-field validation error: {str(e)}"]
    
    def _parse_currency(self, value: str) -> float:
        """Parse currency value to float"""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.-]', '', str(value))
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _is_valid_tin_format(self, value: str) -> bool:
        """Check if TIN (SSN/EIN) has valid format"""
        import re
        # Accept both formatted (XXX-XX-XXXX) and unformatted (XXXXXXXXX) formats
        return bool(re.match(r'^\d{3}-?\d{2}-?\d{4}$', value))


async def get_extraction_pipeline():
    """Get extraction pipeline instance"""
    db = await get_database()
    return ExtractionPipeline(db)
