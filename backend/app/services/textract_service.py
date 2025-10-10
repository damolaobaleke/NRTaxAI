"""
AWS Textract Service for Document OCR
"""

import boto3
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from botocore.exceptions import ClientError
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class TextractService:
    """AWS Textract service for document OCR and text extraction"""
    
    def __init__(self):
        self.textract_client = boto3.client(
            'textract',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.s3_client = boto3.client('s3')
        self.s3_bucket = settings.S3_BUCKET_UPLOADS
        
        # Document type to Textract feature mapping
        self.document_features = {
            "W2": ["TABLES", "FORMS"],
            "1099INT": ["TABLES", "FORMS"],
            "1099NEC": ["TABLES", "FORMS"],
            "1098T": ["TABLES", "FORMS"],
            "1042S": ["TABLES", "FORMS"],
            "1099DIV": ["TABLES", "FORMS"],
            "1099B": ["TABLES", "FORMS"],
            "1099MISC": ["TABLES", "FORMS"]
        }
    
    async def start_document_analysis(
        self,
        s3_key: str,
        document_type: str,
        bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start asynchronous document analysis using AWS Textract SDK
        
        Args:
            s3_key: S3 object key
            document_type: Type of document (W2, 1099INT, etc.)
            bucket: S3 bucket name
            
        Returns:
            Job result with job ID
        """
        try:
            bucket = bucket or self.s3_bucket
            
            # Get appropriate features for document type
            feature_types = self.document_features.get(document_type, ["TABLES", "FORMS"])
            
            # Start document analysis job
            response = self.textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': s3_key
                    }
                },
                FeatureTypes=feature_types
            )
            
            job_id = response['JobId']
            
            logger.info("Textract analysis started", 
                       job_id=job_id, 
                       s3_key=s3_key,
                       bucket=bucket,
                       document_type=document_type,
                       feature_types=feature_types)
            
            return {
                "job_id": job_id,
                "status": "IN_PROGRESS",
                "s3_key": s3_key,
                "bucket": bucket,
                "document_type": document_type,
                "feature_types": feature_types,
                "started_at": datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            logger.error("Textract start analysis error", error=str(e), s3_key=s3_key)
            raise Exception(f"Failed to start Textract analysis: {str(e)}")
    
    async def get_document_analysis_result(
        self,
        job_id: str,
        max_pages: int = 1000
    ) -> Dict[str, Any]:
        """
        Get document analysis result
        
        Args:
            job_id: Textract job ID
            max_pages: Maximum pages to process
            
        Returns:
            Analysis result
        """
        try:
            # Get job status
            response = self.textract_client.get_document_analysis(JobId=job_id)
            
            status = response['JobStatus']
            
            if status == 'IN_PROGRESS':
                return {
                    "job_id": job_id,
                    "status": status,
                    "message": "Analysis in progress"
                }
            
            if status == 'FAILED':
                error_message = response.get('StatusMessage', 'Unknown error')
                logger.error("Textract analysis failed", 
                           job_id=job_id, 
                           error=error_message)
                return {
                    "job_id": job_id,
                    "status": status,
                    "error": error_message
                }
            
            if status == 'SUCCEEDED':
                # Get all pages of results
                blocks = response.get('Blocks', [])
                
                # Handle pagination
                next_token = response.get('NextToken')
                while next_token and len(blocks) < max_pages:
                    next_response = self.textract_client.get_document_analysis(
                        JobId=job_id,
                        NextToken=next_token
                    )
                    blocks.extend(next_response.get('Blocks', []))
                    next_token = next_response.get('NextToken')
                
                # Process blocks into structured data
                processed_data = await self._process_textract_blocks(blocks)
                
                logger.info("Textract analysis completed", 
                           job_id=job_id, 
                           blocks_count=len(blocks),
                           pages_processed=processed_data.get('pages', 0))
                
                return {
                    "job_id": job_id,
                    "status": status,
                    "blocks": blocks,
                    "processed_data": processed_data,
                    "pages_processed": processed_data.get('pages', 0),
                    "completed_at": datetime.utcnow().isoformat()
                }
            
            return {
                "job_id": job_id,
                "status": status,
                "message": f"Analysis status: {status}"
            }
            
        except ClientError as e:
            logger.error("Textract get result error", error=str(e), job_id=job_id)
            raise Exception(f"Failed to get Textract result: {str(e)}")
    
    async def _process_textract_blocks(self, blocks: List[Dict]) -> Dict[str, Any]:
        """
        Process Textract blocks into structured data
        
        Args:
            blocks: List of Textract blocks
            
        Returns:
            Processed document data
        """
        try:
            # Initialize data structures
            pages = {}
            forms = {}
            tables = {}
            lines = {}
            
            # Group blocks by page
            for block in blocks:
                page_num = block.get('Page', 1)
                
                if page_num not in pages:
                    pages[page_num] = {
                        'blocks': [],
                        'forms': {},
                        'tables': {},
                        'lines': []
                    }
                
                pages[page_num]['blocks'].append(block)
                
                # Process different block types
                block_type = block.get('BlockType')
                
                if block_type == 'LINE':
                    line_text = block.get('Text', '')
                    if line_text:
                        pages[page_num]['lines'].append({
                            'text': line_text,
                            'confidence': block.get('Confidence', 0),
                            'geometry': block.get('Geometry', {})
                        })
                
                elif block_type == 'KEY_VALUE_SET':
                    if block.get('EntityTypes', [{}])[0] == 'KEY':
                        key_text = block.get('Text', '')
                        if key_text:
                            pages[page_num]['forms'][key_text] = {
                                'key': key_text,
                                'confidence': block.get('Confidence', 0),
                                'geometry': block.get('Geometry', {})
                            }
                
                elif block_type == 'TABLE':
                    table_id = block.get('Id')
                    if table_id:
                        table_data = await self._extract_table_data(blocks, table_id)
                        pages[page_num]['tables'][table_id] = table_data
            
            # Calculate overall confidence scores
            confidence_scores = await self._calculate_confidence_scores(pages)
            
            return {
                "pages": pages,
                "forms": forms,
                "tables": tables,
                "lines": lines,
                "confidence_scores": confidence_scores,
                "total_pages": len(pages),
                "total_blocks": len(blocks),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Textract block processing error", error=str(e))
            raise Exception(f"Failed to process Textract blocks: {str(e)}")
    
    async def _extract_table_data(self, blocks: List[Dict], table_id: str) -> Dict[str, Any]:
        """
        Extract table data from Textract blocks
        
        Args:
            blocks: List of Textract blocks
            table_id: Table block ID
            
        Returns:
            Table data structure
        """
        try:
            # Find table block
            table_block = next((b for b in blocks if b.get('Id') == table_id), None)
            if not table_block:
                return {}
            
            # Get table relationships
            relationships = table_block.get('Relationships', [])
            cell_ids = []
            
            for rel in relationships:
                if rel.get('Type') == 'CHILD':
                    cell_ids.extend(rel.get('Ids', []))
            
            # Extract cells
            cells = []
            for cell_id in cell_ids:
                cell_block = next((b for b in blocks if b.get('Id') == cell_id), None)
                if cell_block:
                    cells.append({
                        'id': cell_id,
                        'text': cell_block.get('Text', ''),
                        'confidence': cell_block.get('Confidence', 0),
                        'geometry': cell_block.get('Geometry', {})
                    })
            
            # Organize cells into rows and columns
            table_data = await self._organize_table_cells(cells)
            
            return {
                "table_id": table_id,
                "cells": cells,
                "data": table_data,
                "confidence": table_block.get('Confidence', 0)
            }
            
        except Exception as e:
            logger.error("Table extraction error", error=str(e), table_id=table_id)
            return {}
    
    async def _organize_table_cells(self, cells: List[Dict]) -> Dict[str, Any]:
        """
        Organize table cells into rows and columns
        
        Args:
            cells: List of cell data
            
        Returns:
            Organized table structure
        """
        try:
            # Group cells by row (Y coordinate)
            rows = {}
            for cell in cells:
                y_pos = cell.get('geometry', {}).get('BoundingBox', {}).get('Top', 0)
                row_key = round(y_pos, 3)  # Round to group similar Y positions
                
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
                                    key=lambda x: x.get('geometry', {}).get('BoundingBox', {}).get('Left', 0))
                
                table_rows.append([cell['text'] for cell in sorted_cells])
            
            return {
                "rows": table_rows,
                "row_count": len(table_rows),
                "max_columns": max(len(row) for row in table_rows) if table_rows else 0
            }
            
        except Exception as e:
            logger.error("Table organization error", error=str(e))
            return {"rows": [], "row_count": 0, "max_columns": 0}
    
    async def _calculate_confidence_scores(self, pages: Dict) -> Dict[str, Any]:
        """
        Calculate confidence scores for document analysis
        
        Args:
            pages: Processed pages data
            
        Returns:
            Confidence score breakdown
        """
        try:
            total_confidence = 0
            total_items = 0
            page_scores = {}
            
            for page_num, page_data in pages.items():
                page_confidence = 0
                page_items = 0
                
                # Calculate confidence for lines
                for line in page_data.get('lines', []):
                    page_confidence += line.get('confidence', 0)
                    page_items += 1
                
                # Calculate confidence for forms
                for form_key, form_data in page_data.get('forms', {}).items():
                    page_confidence += form_data.get('confidence', 0)
                    page_items += 1
                
                # Calculate confidence for tables
                for table_id, table_data in page_data.get('tables', {}).items():
                    page_confidence += table_data.get('confidence', 0)
                    page_items += 1
                
                if page_items > 0:
                    page_avg_confidence = page_confidence / page_items
                    page_scores[page_num] = {
                        "average_confidence": page_avg_confidence,
                        "total_items": page_items,
                        "total_confidence": page_confidence
                    }
                    
                    total_confidence += page_confidence
                    total_items += page_items
            
            overall_confidence = total_confidence / total_items if total_items > 0 else 0
            
            return {
                "overall_confidence": overall_confidence,
                "total_items": total_items,
                "page_scores": page_scores,
                "confidence_level": self._get_confidence_level(overall_confidence)
            }
            
        except Exception as e:
            logger.error("Confidence calculation error", error=str(e))
            return {
                "overall_confidence": 0,
                "total_items": 0,
                "page_scores": {},
                "confidence_level": "low"
            }
    
    def _get_confidence_level(self, confidence: float) -> str:
        """
        Get confidence level based on score
        
        Args:
            confidence: Confidence score (0-100)
            
        Returns:
            Confidence level string
        """
        if confidence >= 90:
            return "high"
        elif confidence >= 75:
            return "medium"
        elif confidence >= 50:
            return "low"
        else:
            return "very_low"


# Global Textract service instance
textract_service = TextractService()
