"""
AWS Textract Document Normalizer
Works with native Textract output to extract structured data
"""

import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import structlog

logger = structlog.get_logger()


class TextractNormalizer:
    """Normalizes AWS Textract output to structured tax document data"""
    
    def __init__(self):
        self.field_mappings = self._initialize_field_mappings()
    
    def _initialize_field_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize field mappings for different document types"""
        return {
            "W2": {
                "employer_name": {
                    "patterns": [r"employer\s*name", r"company\s*name"],
                    "confidence_threshold": 80
                },
                "employee_name": {
                    "patterns": [r"employee\s*name", r"your\s*name"],
                    "confidence_threshold": 80
                },
                "wages": {
                    "patterns": [r"box\s*1", r"wages.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?wages"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "federal_income_tax_withheld": {
                    "patterns": [r"box\s*2", r"federal\s*income\s*tax.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?federal\s*income\s*tax"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "social_security_wages": {
                    "patterns": [r"box\s*3", r"social\s*security\s*wages.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?social\s*security\s*wages"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "social_security_tax_withheld": {
                    "patterns": [r"box\s*4", r"social\s*security\s*tax.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?social\s*security\s*tax"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "medicare_wages": {
                    "patterns": [r"box\s*5", r"medicare\s*wages.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?medicare\s*wages"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "medicare_tax_withheld": {
                    "patterns": [r"box\s*6", r"medicare\s*tax.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?medicare\s*tax"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "employee_ssn": {
                    "patterns": [r"(\d{3}-\d{2}-\d{4})", r"(\d{9})"],
                    "confidence_threshold": 95,
                    "data_type": "ssn"
                },
                "employer_ein": {
                    "patterns": [r"(\d{2}-\d{7})", r"(\d{9})"],
                    "confidence_threshold": 95,
                    "data_type": "ein"
                }
            },
            
            "1099INT": {
                "payer_name": {
                    "patterns": [r"payer\s*name", r"company\s*name"],
                    "confidence_threshold": 80
                },
                "recipient_name": {
                    "patterns": [r"recipient\s*name", r"your\s*name"],
                    "confidence_threshold": 80
                },
                "interest_income": {
                    "patterns": [r"box\s*1", r"interest.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?interest"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "federal_income_tax_withheld": {
                    "patterns": [r"box\s*4", r"federal\s*income\s*tax.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?federal\s*income\s*tax"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "recipient_tin": {
                    "patterns": [r"(\d{3}-\d{2}-\d{4})", r"(\d{9})"],
                    "confidence_threshold": 95,
                    "data_type": "ssn"
                },
                "payer_tin": {
                    "patterns": [r"(\d{2}-\d{7})", r"(\d{9})"],
                    "confidence_threshold": 95,
                    "data_type": "ein"
                }
            },
            
            "1099NEC": {
                "payer_name": {
                    "patterns": [r"payer\s*name", r"company\s*name"],
                    "confidence_threshold": 80
                },
                "recipient_name": {
                    "patterns": [r"recipient\s*name", r"your\s*name"],
                    "confidence_threshold": 80
                },
                "nonemployee_compensation": {
                    "patterns": [r"box\s*1", r"nonemployee\s*compensation.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?nonemployee\s*compensation"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "federal_income_tax_withheld": {
                    "patterns": [r"box\s*4", r"federal\s*income\s*tax.*?(\d+\.?\d*)", r"(\d+\.?\d*).*?federal\s*income\s*tax"],
                    "confidence_threshold": 85,
                    "data_type": "currency"
                },
                "recipient_tin": {
                    "patterns": [r"(\d{3}-\d{2}-\d{4})", r"(\d{9})"],
                    "confidence_threshold": 95,
                    "data_type": "ssn"
                },
                "payer_tin": {
                    "patterns": [r"(\d{2}-\d{7})", r"(\d{9})"],
                    "confidence_threshold": 95,
                    "data_type": "ein"
                }
            }
        }
    
    async def normalize_textract_result(
        self,
        textract_result: Dict[str, Any],
        document_type: str
    ) -> Dict[str, Any]:
        """
        Normalize AWS Textract result to structured document data
        
        Args:
            textract_result: Raw Textract API response
            document_type: Type of document (W2, 1099INT, etc.)
            
        Returns:
            Normalized document data
        """
        try:
            logger.info("Starting Textract result normalization", 
                       document_type=document_type)
            
            # Extract forms and tables from Textract result
            forms = self._extract_forms(textract_result)
            tables = self._extract_tables(textract_result)
            lines = self._extract_lines(textract_result)
            
            # Get field mappings for document type
            field_mappings = self.field_mappings.get(document_type, {})
            
            # Extract fields using mappings
            extracted_fields = await self._extract_fields_from_textract(
                forms, tables, lines, field_mappings
            )
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(extracted_fields)
            
            # Generate normalized output
            normalized_data = {
                "document_type": document_type,
                "extracted_fields": extracted_fields,
                "confidence_scores": confidence_scores,
                "textract_metadata": {
                    "forms_count": len(forms),
                    "tables_count": len(tables),
                    "lines_count": len(lines)
                },
                "normalized_at": datetime.utcnow().isoformat()
            }
            
            logger.info("Textract normalization completed", 
                       document_type=document_type,
                       fields_extracted=len(extracted_fields),
                       overall_confidence=confidence_scores.get("overall_confidence", 0))
            
            return normalized_data
            
        except Exception as e:
            logger.error("Textract normalization failed", 
                        error=str(e), 
                        document_type=document_type)
            raise Exception(f"Failed to normalize Textract result: {str(e)}")
    
    def _extract_forms(self, textract_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract form data from Textract result"""
        forms = []
        blocks = textract_result.get("Blocks", [])
        
        # Group blocks by form
        form_blocks = {}
        for block in blocks:
            if block.get("BlockType") == "KEY_VALUE_SET":
                if block.get("EntityTypes", [{}])[0] == "KEY":
                    key_text = block.get("Text", "")
                    if key_text:
                        form_blocks[key_text] = block
        
        # Extract key-value pairs
        for key_text, key_block in form_blocks.items():
            # Find associated value block
            relationships = key_block.get("Relationships", [])
            for rel in relationships:
                if rel.get("Type") == "VALUE":
                    value_ids = rel.get("Ids", [])
                    for value_id in value_ids:
                        value_block = next(
                            (b for b in blocks if b.get("Id") == value_id), None
                        )
                        if value_block:
                            forms.append({
                                "key": key_text,
                                "value": value_block.get("Text", ""),
                                "confidence": value_block.get("Confidence", 0),
                                "geometry": value_block.get("Geometry", {})
                            })
        
        return forms
    
    def _extract_tables(self, textract_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract table data from Textract result"""
        tables = []
        blocks = textract_result.get("Blocks", [])
        
        # Find table blocks
        table_blocks = [b for b in blocks if b.get("BlockType") == "TABLE"]
        
        for table_block in table_blocks:
            table_data = {
                "id": table_block.get("Id"),
                "confidence": table_block.get("Confidence", 0),
                "cells": [],
                "rows": []
            }
            
            # Get table cells
            relationships = table_block.get("Relationships", [])
            for rel in relationships:
                if rel.get("Type") == "CHILD":
                    cell_ids = rel.get("Ids", [])
                    for cell_id in cell_ids:
                        cell_block = next(
                            (b for b in blocks if b.get("Id") == cell_id), None
                        )
                        if cell_block:
                            table_data["cells"].append({
                                "text": cell_block.get("Text", ""),
                                "confidence": cell_block.get("Confidence", 0),
                                "geometry": cell_block.get("Geometry", {})
                            })
            
            # Organize cells into rows
            if table_data["cells"]:
                table_data["rows"] = self._organize_table_cells(table_data["cells"])
            
            tables.append(table_data)
        
        return tables
    
    def _extract_lines(self, textract_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract line data from Textract result"""
        lines = []
        blocks = textract_result.get("Blocks", [])
        
        for block in blocks:
            if block.get("BlockType") == "LINE":
                lines.append({
                    "text": block.get("Text", ""),
                    "confidence": block.get("Confidence", 0),
                    "geometry": block.get("Geometry", {})
                })
        
        return lines
    
    def _organize_table_cells(self, cells: List[Dict[str, Any]]) -> List[List[str]]:
        """Organize table cells into rows and columns"""
        # Group cells by Y coordinate (row)
        rows = {}
        for cell in cells:
            y_pos = cell.get("geometry", {}).get("BoundingBox", {}).get("Top", 0)
            row_key = round(y_pos, 3)
            
            if row_key not in rows:
                rows[row_key] = []
            rows[row_key].append(cell)
        
        # Sort rows by Y position
        sorted_rows = sorted(rows.items(), key=lambda x: x[0])
        
        # Organize into table structure
        table_rows = []
        for _, row_cells in sorted_rows:
            # Sort cells in row by X position
            sorted_cells = sorted(row_cells, 
                                key=lambda x: x.get("geometry", {}).get("BoundingBox", {}).get("Left", 0))
            table_rows.append([cell["text"] for cell in sorted_cells])
        
        return table_rows
    
    async def _extract_fields_from_textract(
        self,
        forms: List[Dict[str, Any]],
        tables: List[Dict[str, Any]],
        lines: List[Dict[str, Any]],
        field_mappings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract fields using Textract data and field mappings"""
        extracted_fields = {}
        
        # Combine all text for pattern matching
        all_text = []
        
        # Add form text
        for form in forms:
            all_text.append(f"{form['key']}: {form['value']}")
        
        # Add table text
        for table in tables:
            for row in table.get("rows", []):
                all_text.extend(row)
        
        # Add line text
        for line in lines:
            all_text.append(line["text"])
        
        combined_text = " ".join(all_text)
        
        # Extract fields using patterns
        for field_name, field_config in field_mappings.items():
            patterns = field_config.get("patterns", [])
            best_match = None
            best_confidence = 0
            
            for pattern in patterns:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                
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
    
    def _calculate_match_confidence(
        self, 
        match: re.Match, 
        pattern: str, 
        field_config: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for a field match"""
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
            value = match.group(1) if match.groups() else match.group(0)
            if re.match(r"^\d{3}-\d{2}-\d{4}$", value) or re.match(r"^\d{9}$", value):
                base_confidence *= 1.0
            else:
                base_confidence *= 0.5
        
        elif data_type == "currency":
            value = match.group(1) if match.groups() else match.group(0)
            if re.match(r"^\d+\.?\d*$", value):
                base_confidence *= 1.0
            else:
                base_confidence *= 0.3
        
        return min(base_confidence, 100.0)
    
    def _calculate_confidence_scores(self, extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate confidence scores for extracted fields"""
        total_confidence = 0.0
        valid_fields = 0
        
        for field_name, field_data in extracted_fields.items():
            if field_data.get("value"):
                total_confidence += field_data.get("confidence", 0.0)
                valid_fields += 1
        
        overall_confidence = total_confidence / valid_fields if valid_fields > 0 else 0.0
        
        return {
            "overall_confidence": overall_confidence,
            "valid_fields": valid_fields,
            "total_fields": len(extracted_fields),
            "confidence_level": self._get_confidence_level(overall_confidence)
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


# Global Textract normalizer instance
textract_normalizer = TextractNormalizer()
