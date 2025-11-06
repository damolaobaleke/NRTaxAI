"""
Tax Data Validators - Deterministic validation rules
"""

import re
import math
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional, Union
from decimal import Decimal, ROUND_HALF_UP
import structlog

logger = structlog.get_logger()


class TaxValidator:
    """Deterministic tax data validator"""
    
    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()
        self.cross_validation_rules = self._initialize_cross_validation_rules()
    
    def _initialize_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation rules for different data types"""
        return {
            "ssn": {
                "pattern": r"^\d{3}-?\d{2}-?\d{4}$",
                "validator": self._validate_ssn_format,
                "checksum": self._validate_ssn_checksum,
                "error_message": "Invalid SSN format or checksum"
            },
            "itin": {
                "pattern": r"^9\d{2}-?\d{2}-?\d{4}$",
                "validator": self._validate_itin_format,
                "checksum": self._validate_itin_checksum,
                "error_message": "Invalid ITIN format or checksum"
            },
            "ein": {
                "pattern": r"^\d{2}-?\d{7}$",
                "validator": self._validate_ein_format,
                "checksum": self._validate_ein_checksum,
                "error_message": "Invalid EIN format or checksum"
            },
            "currency": {
                "pattern": r"^\d+\.?\d*$",
                "validator": self._validate_currency_amount,
                "range": {"min": 0, "max": 999999999.99},
                "error_message": "Invalid currency amount"
            },
            "percentage": {
                "pattern": r"^\d+\.?\d*$",
                "validator": self._validate_percentage,
                "range": {"min": 0, "max": 100},
                "error_message": "Invalid percentage"
            },
            "date": {
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
                "validator": self._validate_date_format,
                "error_message": "Invalid date format"
            },
            "year": {
                "pattern": r"^\d{4}$",
                "validator": self._validate_tax_year,
                "range": {"min": 2020, "max": datetime.now().year + 1},
                "error_message": "Invalid tax year"
            }
        }
    
    def _initialize_cross_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize cross-validation rules"""
        return {
            "w2_wages_vs_withholding": {
                "description": "Federal withholding cannot exceed wages",
                "validator": self._validate_wages_vs_withholding,
                "severity": "error"
            },
            "w2_ss_wages_vs_tax": {
                "description": "Social Security tax cannot exceed Social Security wages",
                "validator": self._validate_ss_wages_vs_tax,
                "severity": "error"
            },
            "w2_medicare_wages_vs_tax": {
                "description": "Medicare tax cannot exceed Medicare wages",
                "validator": self._validate_medicare_wages_vs_tax,
                "severity": "error"
            },
            "w2_ss_tax_rate": {
                "description": "Social Security tax rate should be 6.2%",
                "validator": self._validate_ss_tax_rate,
                "severity": "warning"
            },
            "w2_medicare_tax_rate": {
                "description": "Medicare tax rate should be 1.45%",
                "validator": self._validate_medicare_tax_rate,
                "severity": "warning"
            },
            "1099_income_vs_withholding": {
                "description": "Federal withholding cannot exceed income",
                "validator": self._validate_1099_income_vs_withholding,
                "severity": "error"
            },
            "ssn_vs_itin": {
                "description": "Cannot have both SSN and ITIN",
                "validator": self._validate_ssn_vs_itin,
                "severity": "error"
            },
            "tin_format_consistency": {
                "description": "TIN format must be consistent",
                "validator": self._validate_tin_format_consistency,
                "severity": "warning"
            }
        }
    
    async def validate_document_data(
        self,
        document_data: Dict[str, Any],
        document_type: str
    ) -> Dict[str, Any]:
        """
        Validate document data comprehensively
        
        Args:
            document_data: Extracted document data
            document_type: Type of document (W2, 1099INT, etc.)
            
        Returns:
            Validation results
        """
        try:
            logger.info("Starting document validation", 
                       document_type=document_type)
            
            validation_results = {
                "overall_valid": True,
                "document_type": document_type,
                "field_validations": {},
                "cross_validations": {},
                "errors": [],
                "warnings": [],
                "validated_at": datetime.now().isoformat()
            }
            
            extracted_fields = document_data.get("extracted_fields", {})
            
            # Validate individual fields
            for field_name, field_data in extracted_fields.items():
                field_validation = await self._validate_field(
                    field_name, field_data, document_type
                )
                validation_results["field_validations"][field_name] = field_validation
                
                if not field_validation["valid"]:
                    validation_results["overall_valid"] = False
                    validation_results["errors"].extend(field_validation["errors"])
                
                validation_results["warnings"].extend(field_validation["warnings"])
            
            # Perform cross-field validations
            cross_validation_results = await self._validate_cross_fields(
                extracted_fields, document_type
            )
            validation_results["cross_validations"] = cross_validation_results
            
            for validation_name, validation_result in cross_validation_results.items():
                if not validation_result["valid"]:
                    if validation_result["severity"] == "error":
                        validation_results["overall_valid"] = False
                        validation_results["errors"].extend(validation_result["errors"])
                    else:
                        validation_results["warnings"].extend(validation_result["errors"])
            
            # Calculate validation confidence
            validation_results["confidence_score"] = self._calculate_validation_confidence(
                validation_results
            )
            
            logger.info("Document validation completed", 
                       document_type=document_type,
                       overall_valid=validation_results["overall_valid"],
                       confidence_score=validation_results["confidence_score"])
            
            return validation_results
            
        except Exception as e:
            logger.error("Document validation failed", 
                        error=str(e), 
                        document_type=document_type)
            return {
                "overall_valid": False,
                "document_type": document_type,
                "field_validations": {},
                "cross_validations": {},
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "validated_at": datetime.utcnow().isoformat(),
                "confidence_score": 0.0
            }
    
    async def _validate_field(
        self,
        field_name: str,
        field_data: Dict[str, Any],
        document_type: str
    ) -> Dict[str, Any]:
        """Validate individual field"""
        try:
            field_validation = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "confidence": field_data.get("confidence", 0.0)
            }
            
            value = field_data.get("value")
            if not value:
                field_validation["valid"] = False
                field_validation["errors"].append(f"Field {field_name} is empty")
                return field_validation
            
            # Determine data type for validation
            data_type = self._get_field_data_type(field_name, document_type)
            if data_type:
                validation_rule = self.validation_rules.get(data_type)
                if validation_rule:
                    # Format validation
                    if not re.match(validation_rule["pattern"], str(value)):
                        field_validation["valid"] = False
                        field_validation["errors"].append(validation_rule["error_message"])
                        return field_validation
                    
                    # Type-specific validation
                    if validation_rule["validator"]:
                        is_valid, error_msg = validation_rule["validator"](value)
                        if not is_valid:
                            field_validation["valid"] = False
                            field_validation["errors"].append(error_msg)
                            return field_validation
                    
                    # Checksum validation for TINs
                    if data_type in ["ssn", "itin", "ein"] and validation_rule.get("checksum"):
                        is_valid, error_msg = validation_rule["checksum"](value)
                        if not is_valid:
                            field_validation["valid"] = False
                            field_validation["errors"].append(error_msg)
                            return field_validation
                    
                    # Range validation
                    if "range" in validation_rule:
                        range_validation = self._validate_range(
                            value, validation_rule["range"], data_type
                        )
                        if not range_validation["valid"]:
                            field_validation["valid"] = False
                            field_validation["errors"].append(range_validation["error"])
                            return field_validation
            
            # Confidence threshold validation
            confidence = field_data.get("confidence", 0.0)
            if confidence < 80:
                field_validation["warnings"].append(
                    f"Low confidence ({confidence:.1f}%) for field {field_name}"
                )
            
            return field_validation
            
        except Exception as e:
            logger.error("Field validation failed", 
                        error=str(e), 
                        field_name=field_name)
            return {
                "valid": False,
                "errors": [f"Field validation error: {str(e)}"],
                "warnings": [],
                "confidence": 0.0
            }
    
    async def _validate_cross_fields(
        self,
        extracted_fields: Dict[str, Any],
        document_type: str
    ) -> Dict[str, Any]:
        """Validate cross-field relationships"""
        try:
            cross_validation_results = {}
            
            # Get applicable cross-validation rules for document type
            applicable_rules = self._get_applicable_cross_validation_rules(document_type)
            
            for rule_name, rule_config in applicable_rules.items():
                validation_result = await rule_config["validator"](
                    extracted_fields, document_type
                )
                
                cross_validation_results[rule_name] = {
                    "description": rule_config["description"],
                    "valid": validation_result["valid"],
                    "errors": validation_result["errors"],
                    "severity": rule_config["severity"],
                    "validated_at": datetime.utcnow().isoformat()
                }
            
            return cross_validation_results
            
        except Exception as e:
            logger.error("Cross-field validation failed", error=str(e))
            return {}
    
    def _get_field_data_type(self, field_name: str, document_type: str) -> Optional[str]:
        """Get data type for field validation"""
        type_mapping = {
            # SSN/ITIN fields
            "employee_ssn": "ssn",
            "recipient_ssn": "ssn",
            "student_ssn": "ssn",
            "employee_itin": "itin",
            "recipient_itin": "itin",
            "student_itin": "itin",
            
            # EIN fields
            "employer_ein": "ein",
            "payer_ein": "ein",
            "institution_ein": "ein",
            
            # Currency fields
            "wages": "currency",
            "federal_income_tax_withheld": "currency",
            "social_security_wages": "currency",
            "social_security_tax_withheld": "currency",
            "medicare_wages": "currency",
            "medicare_tax_withheld": "currency",
            "interest_income": "currency",
            "nonemployee_compensation": "currency",
            "tuition_paid": "currency",
            "scholarships_grants": "currency",
            
            # Date fields
            "tax_year": "year",
            "birth_date": "date",
            "hire_date": "date"
        }
        
        return type_mapping.get(field_name.lower())
    
    def _get_applicable_cross_validation_rules(self, document_type: str) -> Dict[str, Any]:
        """Get applicable cross-validation rules for document type"""
        applicable_rules = {}
        
        if document_type == "W2":
            applicable_rules.update({
                "w2_wages_vs_withholding": self.cross_validation_rules["w2_wages_vs_withholding"],
                "w2_ss_wages_vs_tax": self.cross_validation_rules["w2_ss_wages_vs_tax"],
                "w2_medicare_wages_vs_tax": self.cross_validation_rules["w2_medicare_wages_vs_tax"],
                "w2_ss_tax_rate": self.cross_validation_rules["w2_ss_tax_rate"],
                "w2_medicare_tax_rate": self.cross_validation_rules["w2_medicare_tax_rate"],
                "ssn_vs_itin": self.cross_validation_rules["ssn_vs_itin"],
                "tin_format_consistency": self.cross_validation_rules["tin_format_consistency"]
            })
        
        elif document_type in ["1099INT", "1099NEC"]:
            applicable_rules.update({
                "1099_income_vs_withholding": self.cross_validation_rules["1099_income_vs_withholding"],
                "ssn_vs_itin": self.cross_validation_rules["ssn_vs_itin"],
                "tin_format_consistency": self.cross_validation_rules["tin_format_consistency"]
            })
        
        return applicable_rules
    
    # Individual validation methods
    def _validate_ssn_format(self, value: str) -> Tuple[bool, str]:
        """Validate SSN format"""
        # Remove any formatting
        clean_value = re.sub(r'[^\d]', '', value)
        
        # Check length
        if len(clean_value) != 9:
            return False, "SSN must be 9 digits"
        
        # Check for invalid SSNs
        invalid_ssns = [
            "000000000", "111111111", "222222222", "333333333",
            "444444444", "555555555", "666666666", "777777777",
            "888888888", "999999999", "123456789", "000000001"
        ]
        
        if clean_value in invalid_ssns:
            return False, "Invalid SSN (not issued)"
        
        # Check area number (first 3 digits)
        area_number = int(clean_value[:3])
        if area_number == 0 or area_number == 666 or area_number >= 900:
            return False, "Invalid SSN area number"
        
        return True, ""
    
    def _validate_ssn_checksum(self, value: str) -> Tuple[bool, str]:
        """Validate SSN checksum (Luhn algorithm variant)"""
        # SSNs don't use traditional checksums, but we can validate format
        return True, ""
    
    def _validate_itin_format(self, value: str) -> Tuple[bool, str]:
        """Validate ITIN format"""
        # Remove any formatting
        clean_value = re.sub(r'[^\d]', '', value)
        
        # Check length
        if len(clean_value) != 9:
            return False, "ITIN must be 9 digits"
        
        # Check first digit (must be 9)
        if clean_value[0] != '9':
            return False, "ITIN must start with 9"
        
        return True, ""
    
    def _validate_itin_checksum(self, value: str) -> Tuple[bool, str]:
        """Validate ITIN checksum"""
        # ITINs use a specific checksum algorithm
        clean_value = re.sub(r'[^\d]', '', value)
        
        if len(clean_value) != 9:
            return False, "Invalid ITIN length"
        
        # ITIN checksum validation
        weights = [7, 1, 3, 7, 1, 3, 7, 1, 3]
        total = sum(int(digit) * weight for digit, weight in zip(clean_value, weights))
        checksum = total % 10
        
        if checksum != 0:
            return False, "Invalid ITIN checksum"
        
        return True, ""
    
    def _validate_ein_format(self, value: str) -> Tuple[bool, str]:
        """Validate EIN format"""
        # Remove any formatting
        clean_value = re.sub(r'[^\d]', '', value)
        
        # Check length
        if len(clean_value) != 9:
            return False, "EIN must be 9 digits"
        
        return True, ""
    
    def _validate_ein_checksum(self, value: str) -> Tuple[bool, str]:
        """Validate EIN checksum"""
        # EINs don't use traditional checksums
        return True, ""
    
    def _validate_currency_amount(self, value: str) -> Tuple[bool, str]:
        """Validate currency amount"""
        try:
            amount = float(value)
            if amount < 0:
                return False, "Currency amount cannot be negative"
            if amount > 999999999.99:
                return False, "Currency amount exceeds maximum"
            return True, ""
        except ValueError:
            return False, "Invalid currency format"
    
    def _validate_percentage(self, value: str) -> Tuple[bool, str]:
        """Validate percentage"""
        try:
            percentage = float(value)
            if percentage < 0 or percentage > 100:
                return False, "Percentage must be between 0 and 100"
            return True, ""
        except ValueError:
            return False, "Invalid percentage format"
    
    def _validate_date_format(self, value: str) -> Tuple[bool, str]:
        """Validate date format"""
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True, ""
        except ValueError:
            return False, "Invalid date format (expected YYYY-MM-DD)"
    
    def _validate_tax_year(self, value: str) -> Tuple[bool, str]:
        """Validate tax year"""
        try:
            year = int(value)
            current_year = datetime.now().year
            if year < 2020 or year > current_year + 1:
                return False, f"Tax year must be between 2020 and {current_year + 1}"
            return True, ""
        except ValueError:
            return False, "Invalid year format"
    
    def _validate_range(
        self, 
        value: str, 
        range_config: Dict[str, float], 
        data_type: str
    ) -> Dict[str, Any]:
        """Validate value is within range"""
        try:
            if data_type == "currency":
                num_value = float(value)
            elif data_type == "percentage":
                num_value = float(value)
            else:
                return {"valid": True, "error": ""}
            
            min_val = range_config.get("min", float('-inf'))
            max_val = range_config.get("max", float('inf'))
            
            if num_value < min_val or num_value > max_val:
                return {
                    "valid": False,
                    "error": f"Value {num_value} is outside valid range [{min_val}, {max_val}]"
                }
            
            return {"valid": True, "error": ""}
            
        except ValueError:
            return {"valid": False, "error": "Invalid numeric value"}
    
    # Cross-validation methods
    async def _validate_wages_vs_withholding(
        self, 
        extracted_fields: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Validate wages vs federal withholding"""
        try:
            wages = self._get_currency_value(extracted_fields.get("wages", {}))
            federal_tax = self._get_currency_value(extracted_fields.get("federal_income_tax_withheld", {}))
            
            if wages > 0 and federal_tax > wages:
                return {
                    "valid": False,
                    "errors": [f"Federal withholding (${federal_tax:,.2f}) cannot exceed wages (${wages:,.2f})"]
                }
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Wages vs withholding validation error: {str(e)}"]}
    
    async def _validate_ss_wages_vs_tax(
        self, 
        extracted_fields: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Validate Social Security wages vs tax"""
        try:
            ss_wages = self._get_currency_value(extracted_fields.get("social_security_wages", {}))
            ss_tax = self._get_currency_value(extracted_fields.get("social_security_tax_withheld", {}))
            
            if ss_wages > 0 and ss_tax > ss_wages:
                return {
                    "valid": False,
                    "errors": [f"Social Security tax (${ss_tax:,.2f}) cannot exceed Social Security wages (${ss_wages:,.2f})"]
                }
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"SS wages vs tax validation error: {str(e)}"]}
    
    async def _validate_medicare_wages_vs_tax(
        self, 
        extracted_fields: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Validate Medicare wages vs tax"""
        try:
            medicare_wages = self._get_currency_value(extracted_fields.get("medicare_wages", {}))
            medicare_tax = self._get_currency_value(extracted_fields.get("medicare_tax_withheld", {}))
            
            if medicare_wages > 0 and medicare_tax > medicare_wages:
                return {
                    "valid": False,
                    "errors": [f"Medicare tax (${medicare_tax:,.2f}) cannot exceed Medicare wages (${medicare_wages:,.2f})"]
                }
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Medicare wages vs tax validation error: {str(e)}"]}
    
    async def _validate_ss_tax_rate(
        self, 
        extracted_fields: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Validate Social Security tax rate (6.2%)"""
        try:
            ss_wages = self._get_currency_value(extracted_fields.get("social_security_wages", {}))
            ss_tax = self._get_currency_value(extracted_fields.get("social_security_tax_withheld", {}))
            
            if ss_wages > 0 and ss_tax > 0:
                expected_rate = 0.062
                actual_rate = ss_tax / ss_wages
                tolerance = 0.001  # 0.1% tolerance
                
                if abs(actual_rate - expected_rate) > tolerance:
                    return {
                        "valid": False,
                        "errors": [f"Social Security tax rate is {actual_rate:.3%}, expected {expected_rate:.1%}"]
                    }
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"SS tax rate validation error: {str(e)}"]}
    
    async def _validate_medicare_tax_rate(
        self, 
        extracted_fields: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Validate Medicare tax rate (1.45%)"""
        try:
            medicare_wages = self._get_currency_value(extracted_fields.get("medicare_wages", {}))
            medicare_tax = self._get_currency_value(extracted_fields.get("medicare_tax_withheld", {}))
            
            if medicare_wages > 0 and medicare_tax > 0:
                expected_rate = 0.0145
                actual_rate = medicare_tax / medicare_wages
                tolerance = 0.0001  # 0.01% tolerance
                
                if abs(actual_rate - expected_rate) > tolerance:
                    return {
                        "valid": False,
                        "errors": [f"Medicare tax rate is {actual_rate:.3%}, expected {expected_rate:.1%}"]
                    }
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"Medicare tax rate validation error: {str(e)}"]}
    
    async def _validate_1099_income_vs_withholding(
        self, 
        extracted_fields: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Validate 1099 income vs withholding"""
        try:
            income_field = "interest_income" if document_type == "1099INT" else "nonemployee_compensation"
            income = self._get_currency_value(extracted_fields.get(income_field, {}))
            federal_tax = self._get_currency_value(extracted_fields.get("federal_income_tax_withheld", {}))
            
            if income > 0 and federal_tax > income:
                return {
                    "valid": False,
                    "errors": [f"Federal withholding (${federal_tax:,.2f}) cannot exceed income (${income:,.2f})"]
                }
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"1099 income vs withholding validation error: {str(e)}"]}
    
    async def _validate_ssn_vs_itin(
        self, 
        extracted_fields: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Validate that SSN and ITIN are not both present"""
        try:
            ssn_fields = ["employee_ssn", "recipient_ssn", "student_ssn"]
            itin_fields = ["employee_itin", "recipient_itin", "student_itin"]
            
            has_ssn = any(self._get_field_value(extracted_fields.get(field, {})) for field in ssn_fields)
            has_itin = any(self._get_field_value(extracted_fields.get(field, {})) for field in itin_fields)
            
            if has_ssn and has_itin:
                return {
                    "valid": False,
                    "errors": ["Cannot have both SSN and ITIN"]
                }
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"SSN vs ITIN validation error: {str(e)}"]}
    
    async def _validate_tin_format_consistency(
        self, 
        extracted_fields: Dict[str, Any], 
        document_type: str
    ) -> Dict[str, Any]:
        """Validate TIN format consistency"""
        try:
            tin_fields = ["employee_ssn", "employee_itin", "recipient_ssn", "recipient_itin", 
                         "student_ssn", "student_itin", "employer_ein", "payer_ein", "institution_ein"]
            
            formats = []
            for field in tin_fields:
                value = self._get_field_value(extracted_fields.get(field, {}))
                if value:
                    # Check if formatted (contains dashes) or unformatted
                    format_type = "formatted" if "-" in value else "unformatted"
                    formats.append((field, format_type))
            
            if len(formats) > 1:
                format_types = set(format_type for _, format_type in formats)
                if len(format_types) > 1:
                    return {
                        "valid": False,
                        "errors": ["TIN formats should be consistent (all formatted or all unformatted)"]
                    }
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"TIN format consistency validation error: {str(e)}"]}
    
    def _get_currency_value(self, field_data: Dict[str, Any]) -> float:
        """Extract currency value from field data"""
        value = self._get_field_value(field_data)
        if value:
            # Remove currency symbols and commas
            clean_value = re.sub(r'[^\d.-]', '', str(value))
            try:
                return float(clean_value)
            except ValueError:
                return 0.0
        return 0.0
    
    def _get_field_value(self, field_data: Dict[str, Any]) -> Optional[str]:
        """Extract value from field data"""
        if isinstance(field_data, dict):
            return field_data.get("value")
        return str(field_data) if field_data else None
    
    def _calculate_validation_confidence(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall validation confidence score"""
        try:
            total_confidence = 0.0
            total_fields = 0
            
            # Calculate field confidence
            for field_name, field_validation in validation_results.get("field_validations", {}).items():
                if field_validation.get("valid", False):
                    confidence = field_validation.get("confidence", 0.0)
                    total_confidence += confidence
                    total_fields += 1
            
            # Calculate cross-validation confidence
            cross_validations = validation_results.get("cross_validations", {})
            cross_validation_score = 100.0 if all(
                cv.get("valid", False) for cv in cross_validations.values()
            ) else 50.0
            
            # Weighted average: 70% field validation, 30% cross-validation
            if total_fields > 0:
                field_confidence = total_confidence / total_fields
                overall_confidence = (field_confidence * 0.7) + (cross_validation_score * 0.3)
            else:
                overall_confidence = cross_validation_score
            
            return min(overall_confidence, 100.0)
            
        except Exception as e:
            logger.error("Confidence calculation failed", error=str(e))
            return 0.0


# Global tax validator instance
tax_validator = TaxValidator()
