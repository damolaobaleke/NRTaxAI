"""
Form 8879 Generator - IRS e-file Signature Authorization
"""

import io
import json
from datetime import datetime, date
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
import structlog

from app.core.config import settings
from app.services.s3_service import s3_service

logger = structlog.get_logger()


class Form8879Generator:
    """Generate Form 8879 for e-file authorization"""
    
    def __init__(self):
        self.page_width, self.page_height = letter
        self.margin = 0.75 * inch
    
    async def generate_form_8879(
        self,
        return_id: str,
        tax_data: Dict[str, Any],
        user_data: Dict[str, Any],
        operator_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Form 8879 for e-file authorization
        
        Args:
            return_id: Tax return ID
            tax_data: Tax computation data
            user_data: User/taxpayer data
            operator_data: Operator/preparer data
            
        Returns:
            Generated form metadata
        """
        try:
            logger.info("Generating Form 8879", return_id=return_id)
            
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            y_position = self.page_height - self.margin
            
            # Form Header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(self.margin, y_position, "Form 8879")
            y_position -= 20
            
            pdf.setFont("Helvetica", 12)
            pdf.drawString(self.margin, y_position, "IRS e-file Signature Authorization")
            y_position -= 15
            pdf.drawString(self.margin, y_position, "for Form 1040-NR")
            y_position -= 30
            
            # Tax Year
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, f"Tax Year: {tax_data.get('tax_year', datetime.now().year)}")
            y_position -= 30
            
            # Part I: Tax Return Information
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Part I - Tax Return Information")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, f"Your name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"Your ITIN/SSN: {self._mask_tin(user_data.get('itin', ''))}")
            y_position -= 20
            
            # Tax computation summary
            final_comp = tax_data.get('final_computation', {})
            
            pdf.drawString(self.margin, y_position, f"1. Total tax (Form 1040-NR): ${final_comp.get('total_tax', 0):,.2f}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"2. Federal income tax withheld: ${final_comp.get('total_credits', 0):,.2f}")
            y_position -= 15
            
            refund_or_owed = final_comp.get('refund_or_owed', 'owed')
            amount = final_comp.get('amount', 0)
            
            if refund_or_owed == 'refund':
                pdf.drawString(self.margin, y_position, f"3. Refund: ${amount:,.2f}")
            else:
                pdf.drawString(self.margin, y_position, f"3. Amount you owe: ${amount:,.2f}")
            
            y_position -= 30
            
            # Part II: Declaration of Taxpayer
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Part II - Declaration of Taxpayer")
            y_position -= 20
            
            pdf.setFont("Helvetica", 8)
            pdf.drawString(self.margin, y_position, "I authorize the U.S. Treasury and its designated Financial Agent to initiate an ACH electronic funds")
            y_position -= 10
            pdf.drawString(self.margin, y_position, "withdrawal (direct debit) entry to the financial institution account indicated in the tax preparation software")
            y_position -= 10
            pdf.drawString(self.margin, y_position, "for payment of my federal taxes owed on this return, and the financial institution to debit the entry to this account.")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, "Taxpayer's PIN: _____ (5-digit self-selected PIN)")
            y_position -= 20
            
            pdf.drawString(self.margin, y_position, "Taxpayer's signature: _________________________________")
            pdf.drawString(self.margin + 300, y_position, "Date: ___________")
            y_position -= 30
            
            # Part III: Certification and Authentication
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Part III - Certification and Authentication")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, f"ERO's PTIN: {operator_data.get('ptin', 'PXXXXXXX')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"ERO's name: {operator_data.get('email', 'N/A')}")
            y_position -= 20
            
            pdf.setFont("Helvetica", 8)
            pdf.drawString(self.margin, y_position, "I declare that I have reviewed the above return and that the entries on this form are complete and correct")
            y_position -= 10
            pdf.drawString(self.margin, y_position, "to the best of my knowledge.")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, "ERO's signature: _________________________________")
            pdf.drawString(self.margin + 300, y_position, "Date: ___________")
            y_position -= 30
            
            # Part IV: Certification
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Part IV - Electronic Return Originator (ERO) Certification")
            y_position -= 20
            
            pdf.setFont("Helvetica", 8)
            pdf.drawString(self.margin, y_position, "I certify that the above numeric entry is my PIN, which is my signature on the 2024 electronically filed")
            y_position -= 10
            pdf.drawString(self.margin, y_position, "return indicated above. I confirm that I am submitting this return in accordance with the requirements of")
            y_position -= 10
            pdf.drawString(self.margin, y_position, "Pub. 1345, Handbook for Authorized IRS e-file Providers of Individual Income Tax Returns.")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, "ERO's PIN: _____ (5-digit self-selected PIN)")
            y_position -= 30
            
            # Instructions
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(self.margin, y_position, "Instructions for Completion:")
            y_position -= 15
            
            pdf.setFont("Helvetica", 9)
            pdf.drawString(self.margin, y_position, "1. Taxpayer: Enter your 5-digit PIN and sign the form")
            y_position -= 12
            pdf.drawString(self.margin, y_position, "2. ERO: After taxpayer signature, enter your PIN and sign")
            y_position -= 12
            pdf.drawString(self.margin, y_position, "3. Keep this form for your records - do not send to the IRS")
            y_position -= 12
            pdf.drawString(self.margin, y_position, "4. This form authorizes electronic filing of your tax return")
            
            # Save PDF
            pdf.save()
            
            # Upload to S3
            pdf_content = buffer.getvalue()
            file_key = f"forms/{return_id}/8879_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            upload_result = await s3_service.upload_file(
                file_key=file_key,
                file_content=pdf_content,
                bucket=settings.S3_BUCKET_PDFS,
                metadata={
                    "form_type": "8879",
                    "return_id": return_id,
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info("Form 8879 generated", return_id=return_id)
            
            return {
                "form_type": "8879",
                "file_key": file_key,
                "file_size": upload_result["size_bytes"],
                "generated_at": datetime.utcnow().isoformat(),
                "status": "generated"
            }
            
        except Exception as e:
            logger.error("Form 8879 generation failed", error=str(e))
            raise Exception(f"Failed to generate Form 8879: {str(e)}")
    
    def _mask_tin(self, tin: str) -> str:
        """Mask TIN for display (XXX-XX-1234)"""
        if not tin:
            return "XXX-XX-XXXX"
        
        # Remove formatting
        clean_tin = tin.replace("-", "")
        
        if len(clean_tin) == 9:
            return f"XXX-XX-{clean_tin[-4:]}"
        
        return "XXX-XX-XXXX"


# Global form 8879 generator instance
form_8879_generator = Form8879Generator()
