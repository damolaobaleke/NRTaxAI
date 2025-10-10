"""
Document Normalization Service
"""

import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import structlog

logger = structlog.get_logger()


class DocumentType(Enum):
    W2 = "W2"
    FORM_1099_INT = "1099INT"
    FORM_1099_NEC = "1099NEC"
    FORM_1098_T = "1098T"
    FORM_1042_S = "1042S"
    FORM_1099_DIV = "1099DIV"
    FORM_1099_B = "1099B"
    FORM_1099_MISC = "1099MISC"


class DocumentNormalizer:
    """Service for normalizing extracted document data"""
    
    def __init__(self):
        self.field_patterns = self._initialize_field_patterns()
        self.validation_rules = self._initialize_validation_rules()
    
    def _initialize_field_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize field extraction patterns for different document types"""
        return {
            DocumentType.W2.value: {
                "employer_name": {
                    "patterns": [r"employer\s*name", r"company\s*name", r"^[A-Z][A-Za-z\s&,\.]+$"],
                    "required": True,
                    "confidence_threshold": 80
                },
                "employee_name": {
                    "patterns": [r"employee\s*name", r"your\s*name"],
                    "required": True,
                    "confidence_threshold": 80
                },
                "wages": {
                    "patterns": [r"wages.*?(\d+\.?\d*)", r"box\s*1.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "federal_income_tax_withheld": {
                    "patterns": [r"federal\s*income\s*tax.*?(\d+\.?\d*)", r"box\s*2.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "social_security_wages": {
                    "patterns": [r"social\s*security\s*wages.*?(\d+\.?\d*)", r"box\s*3.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "social_security_tax_withheld": {
                    "patterns": [r"social\s*security\s*tax.*?(\d+\.?\d*)", r"box\s*4.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "medicare_wages": {
                    "patterns": [r"medicare\s*wages.*?(\d+\.?\d*)", r"box\s*5.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "medicare_tax_withheld": {
                    "patterns": [r"medicare\s*tax.*?(\d+\.?\d*)", r"box\s*6.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "employee_ssn": {
                    "patterns": [r"(\d{3}-\d{2}-\d{4})", r"(\d{9})"],
                    "required": True,
                    "confidence_threshold": 95,
                    "data_type": "ssn"
                },
                "employer_ein": {
                    "patterns": [r"(\d{2}-\d{7})", r"(\d{9})"],
                    "required": True,
                    "confidence_threshold": 95,
                    "data_type": "ein"
                }
            },
            
            DocumentType.FORM_1099_INT.value: {
                "payer_name": {
                    "patterns": [r"payer\s*name", r"company\s*name"],
                    "required": True,
                    "confidence_threshold": 80
                },
                "recipient_name": {
                    "patterns": [r"recipient\s*name", r"your\s*name"],
                    "required": True,
                    "confidence_threshold": 80
                },
                "interest_income": {
                    "patterns": [r"interest.*?(\d+\.?\d*)", r"box\s*1.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "federal_income_tax_withheld": {
                    "patterns": [r"federal\s*income\s*tax.*?(\d+\.?\d*)", r"box\s*4.*?(\d+\.?\d*)"],
                    "required": False,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "recipient_tin": {
                    "patterns": [r"(\d{3}-\d{2}-\d{4})", r"(\d{9})"],
                    "required": True,
                    "confidence_threshold": 95,
                    "data_type": "ssn"
                },
                "payer_tin": {
                    "patterns": [r"(\d{2}-\d{7})", r"(\d{9})"],
                    "required": True,
                    "confidence_threshold": 95,
                    "data_type": "ein"
                }
            },
            
            DocumentType.FORM_1099_NEC.value: {
                "payer_name": {
                    "patterns": [r"payer\s*name", r"company\s*name"],
                    "required": True,
                    "confidence_threshold": 80
                },
                "recipient_name": {
                    "patterns": [r"recipient\s*name", r"your\s*name"],
                    "required": True,
                    "confidence_threshold": 80
                },
                "nonemployee_compensation": {
                    "patterns": [r"nonemployee\s*compensation.*?(\d+\.?\d*)", r"box\s*1.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "federal_income_tax_withheld": {
                    "patterns": [r"federal\s*income\s*tax.*?(\d+\.?\d*)", r"box\s*4.*?(\d+\.?\d*)"],
                    "required": False,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "recipient_tin": {
                    "patterns": [r"(\d{3}-\d{2}-\d{4})", r"(\d{9})"],
                    "required": True,
                    "confidence_threshold": 95,
                    "data_type": "ssn"
                },
                "payer_tin": {
                    "patterns": [r"(\d{2}-\d{7})", r"(\d{9})"],
                    "required": True,
                    "confidence_threshold": 95,
                    "data_type": "ein"
                }
            },
            
            DocumentType.FORM_1098_T.value: {
                "institution_name": {
                    "patterns": [r"institution\s*name", r"school\s*name", r"university"],
                    "required": True,
                    "confidence_threshold": 80
                },
                "student_name": {
                    "patterns": [r"student\s*name", r"your\s*name"],
                    "required": True,
                    "confidence_threshold": 80
                },
                "tuition_paid": {
                    "patterns": [r"tuition.*?(\d+\.?\d*)", r"box\s*1.*?(\d+\.?\d*)"],
                    "required": True,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "scholarships_grants": {
                    "patterns": [r"scholarships.*?(\d+\.?\d*)", r"grants.*?(\d+\.?\d*)", r"box\s*5.*?(\d+\.?\d*)"],
                    "required": False,
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "student_ssn": {
                    "patterns": [r"(\d{3}-\d{2}-\d{4})", r"(\d{9})"],
                    "required": True,
                    "confidence_threshold": 95,
                    "data_type": "ssn"
                },
                "institution_ein": {
                    "patterns": [r"(\d{2}-\d{7})", r"(\d{9})"],
                    "required": True,
                    "confidence_threshold": 95,
                    "data_type": "ein"
                }
            }
        }
    
    def _initialize_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation rules for extracted data"""
        return {
            "ssn": {
                "pattern": r"^\d{3}-\d{2}-\d{4}$",
                "validator": self._validate_ssn,
                "error_message": "Invalid SSN format"
            },
            "ein": {
                "pattern": r"^\d{2}-\d{7}$",
                "validator": self._validate_ein,
                "error_message": "Invalid EIN format"
            },
            "currency": {
                "pattern": r"^\d+\.?\d*$",
                "validator": self._validate_currency,
                "error_message": "Invalid currency amount"
            },
            "date": {
                "pattern": r"^\d{2}/\d{2}/\d{4}$",
                "validator": self._validate_date,
                "error_message": "Invalid date format"
            }
        }
    
    async def normalize_document_data(
        self,
        textract_result: Dict[str, Any],
        document_type: str
    ) -> Dict[str, Any]:
        """
        Normalize extracted document data
        
        Args:
            textract_result: Textract analysis result
            document_type: Type of document being processed
            
        Returns:
            Normalized document data
        """
        try:
            logger.info("Starting document normalization", 
                       document_type=document_type)
            
            # Extract text from Textract result
            extracted_text = self._extract_text_from_textract(textract_result)
            
            # Get field patterns for document type
            field_patterns = self.field_patterns.get(document_type, {})
            
            # Extract fields using patterns
            extracted_fields = await self._extract_fields_from_text(
                extracted_text, field_patterns
            )
            
            # Validate extracted data
            validation_results = await self._validate_extracted_data(
                extracted_fields, field_patterns
            )
            
            # Calculate confidence scores
            confidence_scores = await self._calculate_field_confidence(
                extracted_fields, field_patterns
            )
            
            # Generate normalized output
            normalized_data = {
                "document_type": document_type,
                "extracted_fields": extracted_fields,
                "validation_results": validation_results,
                "confidence_scores": confidence_scores,
                "raw_text": extracted_text,
                "textract_result": textract_result,
                "normalized_at": datetime.utcnow().isoformat()
            }
            
            logger.info("Document normalization completed", 
                       document_type=document_type,
                       fields_extracted=len(extracted_fields),
                       validation_passed=validation_results.get("overall_valid", False))
            
            return normalized_data
            
        except Exception as e:
            logger.error("Document normalization failed", 
                        error=str(e), 
                        document_type=document_type)
            raise Exception(f"Failed to normalize document: {str(e)}")
    
    def _extract_text_from_textract(self, textract_result: Dict[str, Any]) -> str:
        """Extract text from Textract result"""
        try:
            pages = textract_result.get("processed_data", {}).get("pages", {})
            all_text = []
            
            for page_num, page_data in pages.items():
                # Extract text from lines
                for line in page_data.get("lines", []):
                    text = line.get("text", "")
                    if text.strip():
                        all_text.append(text.strip())
                
                # Extract text from forms
                for form_key, form_data in page_data.get("forms", {}).items():
                    all_text.append(form_key)
                
                # Extract text from tables
                for table_id, table_data in page_data.get("tables", {}).items():
                    for row in table_data.get("data", {}).get("rows", []):
                        all_text.extend(row)
            
            return " ".join(all_text)
            
        except Exception as e:
            logger.error("Text extraction failed", error=str(e))
            return ""
    
    async def _extract_fields_from_text(
        self, 
        text: str, 
        field_patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract fields from text using patterns"""
        try:
            extracted_fields = {}
            
            for field_name, field_config in field_patterns.items():
                patterns = field_config.get("patterns", [])
                best_match = None
                best_confidence = 0
                
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        # Calculate confidence based on match quality
                        confidence = self._calculate_match_confidence(
                            match, pattern, field_config
                        )
                        
                        if confidence > best_confidence:
                            best_match = {
                                "value": match.group(1) if match.groups() else match.group(0),
                                "confidence": confidence,
                                "pattern": pattern,
                                "position": match.span()
                            }
                            best_confidence = confidence
                
                if best_match and best_confidence >= field_config.get("confidence_threshold", 0):
                    extracted_fields[field_name] = best_match
                else:
                    extracted_fields[field_name] = {
                        "value": None,
                        "confidence": best_confidence,
                        "pattern": None,
                        "position": None,
                        "status": "not_found"
                    }
            
            return extracted_fields
            
        except Exception as e:
            logger.error("Field extraction failed", error=str(e))
            return {}
    
    def _calculate_match_confidence(
        self, 
        match: re.Match, 
        pattern: str, 
        field_config: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for a field match"""
        try:
            base_confidence = 100.0
            
            # Reduce confidence for partial matches
            if match.groups():
                base_confidence *= 0.9
            
            # Reduce confidence for case mismatches
            if match.group(0).lower() != match.group(0):
                base_confidence *= 0.95
            
            # Reduce confidence for complex patterns
            if len(pattern) > 50:
                base_confidence *= 0.9
            
            # Apply data type specific confidence adjustments
            data_type = field_config.get("data_type")
            if data_type == "ssn":
                # SSN should be exactly 9 digits or formatted
                value = match.group(1) if match.groups() else match.group(0)
                if re.match(r"^\d{3}-\d{2}-\d{4}$", value) or re.match(r"^\d{9}$", value):
                    base_confidence *= 1.0
                else:
                    base_confidence *= 0.5
            
            elif data_type == "currency":
                # Currency should be numeric
                value = match.group(1) if match.groups() else match.group(0)
                if re.match(r"^\d+\.?\d*$", value):
                    base_confidence *= 1.0
                else:
                    base_confidence *= 0.3
            
            return min(base_confidence, 100.0)
            
        except Exception as e:
            logger.error("Confidence calculation failed", error=str(e))
            return 0.0
    
    async def _validate_extracted_data(
        self, 
        extracted_fields: Dict[str, Any], 
        field_patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate extracted field data"""
        try:
            validation_results = {
                "overall_valid": True,
                "field_validations": {},
                "errors": [],
                "warnings": []
            }
            
            for field_name, field_data in extracted_fields.items():
                field_config = field_patterns.get(field_name, {})
                field_validation = {
                    "valid": True,
                    "errors": [],
                    "warnings": []
                }
                
                # Check if required field is missing
                if field_config.get("required", False) and not field_data.get("value"):
                    field_validation["valid"] = False
                    field_validation["errors"].append(f"Required field {field_name} is missing")
                    validation_results["overall_valid"] = False
                
                # Validate field value if present
                if field_data.get("value"):
                    data_type = field_config.get("data_type")
                    if data_type:
                        validation_rule = self.validation_rules.get(data_type)
                        if validation_rule:
                            is_valid, error_msg = validation_rule["validator"](field_data["value"])
                            if not is_valid:
                                field_validation["valid"] = False
                                field_validation["errors"].append(error_msg)
                                validation_results["overall_valid"] = False
                
                # Check confidence threshold
                confidence = field_data.get("confidence", 0)
                threshold = field_config.get("confidence_threshold", 0)
                if confidence < threshold:
                    field_validation["warnings"].append(
                        f"Low confidence ({confidence:.1f}%) for field {field_name}"
                    )
                
                validation_results["field_validations"][field_name] = field_validation
            
            return validation_results
            
        except Exception as e:
            logger.error("Data validation failed", error=str(e))
            return {
                "overall_valid": False,
                "field_validations": {},
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": []
            }
    
    async def _calculate_field_confidence(
        self, 
        extracted_fields: Dict[str, Any], 
        field_patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate confidence scores for extracted fields"""
        try:
            confidence_scores = {
                "overall_confidence": 0.0,
                "field_confidences": {},
                "confidence_level": "unknown"
            }
            
            total_confidence = 0.0
            valid_fields = 0
            
            for field_name, field_data in extracted_fields.items():
                confidence = field_data.get("confidence", 0.0)
                confidence_scores["field_confidences"][field_name] = {
                    "confidence": confidence,
                    "threshold": field_patterns.get(field_name, {}).get("confidence_threshold", 0),
                    "meets_threshold": confidence >= field_patterns.get(field_name, {}).get("confidence_threshold", 0)
                }
                
                if field_data.get("value"):
                    total_confidence += confidence
                    valid_fields += 1
            
            if valid_fields > 0:
                confidence_scores["overall_confidence"] = total_confidence / valid_fields
                confidence_scores["confidence_level"] = self._get_confidence_level(
                    confidence_scores["overall_confidence"]
                )
            
            return confidence_scores
            
        except Exception as e:
            logger.error("Confidence calculation failed", error=str(e))
            return {
                "overall_confidence": 0.0,
                "field_confidences": {},
                "confidence_level": "unknown"
            }
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level based on score"""
        if confidence >= 90:
            return "high"
        elif confidence >= 75:
            return "medium"
        elif confidence >= 50:
            return "low"
        else:
            return "very_low"
    
    # Validation methods
    def _validate_ssn(self, value: str) -> Tuple[bool, str]:
        """Validate SSN format"""
        if re.match(r"^\d{3}-\d{2}-\d{4}$", value):
            return True, ""
        elif re.match(r"^\d{9}$", value):
            return True, ""
        else:
            return False, "Invalid SSN format"
    
    def _validate_ein(self, value: str) -> Tuple[bool, str]:
        """Validate EIN format"""
        if re.match(r"^\d{2}-\d{7}$", value):
            return True, ""
        elif re.match(r"^\d{9}$", value):
            return True, ""
        else:
            return False, "Invalid EIN format"
    
    def _validate_currency(self, value: str) -> Tuple[bool, str]:
        """Validate currency amount"""
        if re.match(r"^\d+\.?\d*$", value):
            amount = float(value)
            if amount >= 0:
                return True, ""
            else:
                return False, "Currency amount cannot be negative"
        else:
            return False, "Invalid currency format"
    
    def _validate_date(self, value: str) -> Tuple[bool, str]:
        """Validate date format"""
        if re.match(r"^\d{2}/\d{2}/\d{4}$", value):
            try:
                datetime.strptime(value, "%m/%d/%Y")
                return True, ""
            except ValueError:
                return False, "Invalid date"
        else:
            return False, "Invalid date format"


# Global document normalizer instance
document_normalizer = DocumentNormalizer()
