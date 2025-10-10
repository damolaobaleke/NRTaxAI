"""
Tax Form Generator Service
Generates PDF tax forms (1040NR, 8843, W-8BEN, 1040-V) with validations
"""

import io
import json
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
import structlog

from app.core.config import settings
from app.services.s3_service import s3_service

logger = structlog.get_logger()


class FormGenerator:
    """Generate IRS tax forms as PDFs"""
    
    def __init__(self):
        self.page_width, self.page_height = letter
        self.margin = 0.75 * inch
    
    async def generate_1040nr(
        self,
        tax_data: Dict[str, Any],
        user_data: Dict[str, Any],
        return_id: str
    ) -> Dict[str, Any]:
        """
        Generate Form 1040-NR (U.S. Nonresident Alien Income Tax Return)
        
        Args:
            tax_data: Tax computation data
            user_data: User profile data
            return_id: Tax return ID
            
        Returns:
            Generated form metadata
        """
        try:
            logger.info("Generating Form 1040-NR", return_id=return_id)
            
            # Create PDF buffer
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            # Page 1: Personal Information and Income
            self._draw_1040nr_page1(pdf, tax_data, user_data)
            
            # Page 2: Deductions and Tax Computation
            pdf.showPage()
            self._draw_1040nr_page2(pdf, tax_data, user_data)
            
            # Page 3: Credits and Payments
            pdf.showPage()
            self._draw_1040nr_page3(pdf, tax_data, user_data)
            
            # Save PDF
            pdf.save()
            
            # Upload to S3
            pdf_content = buffer.getvalue()
            file_key = f"forms/{return_id}/1040NR_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            upload_result = await s3_service.upload_file(
                file_key=file_key,
                file_content=pdf_content,
                bucket=settings.S3_BUCKET_PDFS,
                metadata={
                    "form_type": "1040NR",
                    "return_id": return_id,
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info("Form 1040-NR generated", 
                       return_id=return_id,
                       file_key=file_key)
            
            return {
                "form_type": "1040NR",
                "file_key": file_key,
                "file_size": upload_result["size_bytes"],
                "generated_at": datetime.utcnow().isoformat(),
                "status": "generated"
            }
            
        except Exception as e:
            logger.error("Form 1040-NR generation failed", error=str(e))
            raise Exception(f"Failed to generate Form 1040-NR: {str(e)}")
    
    def _draw_1040nr_page1(
        self,
        pdf: canvas.Canvas,
        tax_data: Dict[str, Any],
        user_data: Dict[str, Any]
    ):
        """Draw page 1 of Form 1040-NR"""
        y_position = self.page_height - self.margin
        
        # Form header
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(self.margin, y_position, "Form 1040-NR")
        y_position -= 20
        
        pdf.setFont("Helvetica", 12)
        pdf.drawString(self.margin, y_position, "U.S. Nonresident Alien Income Tax Return")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        pdf.drawString(self.margin, y_position, f"Tax Year: {tax_data.get('tax_year', datetime.now().year)}")
        y_position -= 30
        
        # Personal Information
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(self.margin, y_position, "Personal Information")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        pdf.drawString(self.margin, y_position, f"Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}")
        y_position -= 15
        
        pdf.drawString(self.margin, y_position, f"ITIN/SSN: {user_data.get('itin', 'XXX-XX-XXXX')}")
        y_position -= 15
        
        address = user_data.get('address_json', {})
        pdf.drawString(self.margin, y_position, f"Address: {address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
        y_position -= 15
        
        pdf.drawString(self.margin, y_position, f"Country: {user_data.get('residency_country', '')}")
        y_position -= 15
        
        pdf.drawString(self.margin, y_position, f"Visa Status: {user_data.get('visa_class', '')}")
        y_position -= 30
        
        # Residency Status
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(self.margin, y_position, "Residency Status")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        residency = tax_data.get('residency_determination', {})
        pdf.drawString(self.margin, y_position, f"Status: {residency.get('residency_status', 'Non-Resident').upper()}")
        y_position -= 15
        
        pdf.drawString(self.margin, y_position, f"Determination Method: {residency.get('determination_method', 'N/A')}")
        y_position -= 30
        
        # Income
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(self.margin, y_position, "Income")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        income_sourcing = tax_data.get('income_sourcing', {})
        
        pdf.drawString(self.margin, y_position, f"1. Total US Source Income: ${income_sourcing.get('total_us_source_income', 0):,.2f}")
        y_position -= 15
        
        sourcing_breakdown = income_sourcing.get('sourcing_breakdown', {})
        us_source = sourcing_breakdown.get('us_source', {})
        
        pdf.drawString(self.margin + 20, y_position, f"   Wages (W-2): ${us_source.get('wages', 0):,.2f}")
        y_position -= 15
        
        pdf.drawString(self.margin + 20, y_position, f"   Interest: ${us_source.get('interest', 0):,.2f}")
        y_position -= 15
        
        pdf.drawString(self.margin + 20, y_position, f"   Self-Employment: ${us_source.get('self_employment', 0):,.2f}")
        y_position -= 20
        
        # Treaty Benefits
        treaty_benefits = tax_data.get('treaty_benefits', {})
        if treaty_benefits.get('has_treaty'):
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Treaty Benefits Applied")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, f"Treaty Country: {treaty_benefits.get('treaty_country', 'N/A')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"Total Exemption: ${treaty_benefits.get('total_exemption_amount', 0):,.2f}")
            y_position -= 15
            
            for exemption in treaty_benefits.get('exemptions_applied', []):
                pdf.drawString(self.margin + 20, y_position, f"   {exemption.get('description', 'N/A')}: ${exemption.get('amount', 0):,.2f}")
                y_position -= 15
        
        # Add page number
        pdf.setFont("Helvetica", 8)
        pdf.drawString(self.page_width - self.margin - 50, self.margin / 2, "Page 1 of 3")
    
    def _draw_1040nr_page2(
        self,
        pdf: canvas.Canvas,
        tax_data: Dict[str, Any],
        user_data: Dict[str, Any]
    ):
        """Draw page 2 of Form 1040-NR"""
        y_position = self.page_height - self.margin
        
        # Taxable Income Calculation
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(self.margin, y_position, "Taxable Income Calculation")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        taxable_income_calc = tax_data.get('taxable_income_calculation', {})
        
        pdf.drawString(self.margin, y_position, f"US Source Income: ${taxable_income_calc.get('us_source_income', 0):,.2f}")
        y_position -= 15
        
        pdf.drawString(self.margin, y_position, f"Less: Treaty Exemptions: $({taxable_income_calc.get('treaty_exemptions', 0):,.2f})")
        y_position -= 15
        
        pdf.drawString(self.margin, y_position, "─" * 60)
        y_position -= 15
        
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(self.margin, y_position, f"Taxable Income: ${taxable_income_calc.get('taxable_income', 0):,.2f}")
        y_position -= 30
        
        # Tax Computation
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(self.margin, y_position, "Tax Computation")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        federal_tax = tax_data.get('federal_tax', {})
        
        pdf.drawString(self.margin, y_position, "Tax by Bracket:")
        y_position -= 15
        
        for bracket_info in federal_tax.get('tax_by_bracket', []):
            pdf.drawString(self.margin + 20, y_position, 
                          f"{bracket_info.get('bracket', 'N/A')} @ {bracket_info.get('rate', 'N/A')}: ${bracket_info.get('tax_amount', 0):,.2f}")
            y_position -= 15
        
        y_position -= 5
        pdf.drawString(self.margin, y_position, "─" * 60)
        y_position -= 15
        
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(self.margin, y_position, f"Total Federal Tax: ${federal_tax.get('total_tax', 0):,.2f}")
        y_position -= 15
        
        pdf.setFont("Helvetica", 10)
        pdf.drawString(self.margin, y_position, f"Effective Tax Rate: {federal_tax.get('effective_rate', 0):.2f}%")
        y_position -= 30
        
        # State Tax (if applicable)
        if 'state_tax' in tax_data:
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "State Tax")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            state_tax = tax_data.get('state_tax', {})
            
            pdf.drawString(self.margin, y_position, f"State: {state_tax.get('state', 'N/A')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"State Taxable Income: ${state_tax.get('state_taxable_income', 0):,.2f}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"State Tax: ${state_tax.get('total_tax', 0):,.2f}")
            y_position -= 20
        
        # Add page number
        pdf.setFont("Helvetica", 8)
        pdf.drawString(self.page_width - self.margin - 50, self.margin / 2, "Page 2 of 3")
    
    def _draw_1040nr_page3(
        self,
        pdf: canvas.Canvas,
        tax_data: Dict[str, Any],
        user_data: Dict[str, Any]
    ):
        """Draw page 3 of Form 1040-NR"""
        y_position = self.page_height - self.margin
        
        # Tax Credits and Payments
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(self.margin, y_position, "Tax Credits and Payments")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        tax_credits = tax_data.get('tax_credits', {})
        
        for credit in tax_credits.get('credits_breakdown', []):
            pdf.drawString(self.margin, y_position, 
                          f"{credit.get('description', 'N/A')}: ${credit.get('amount', 0):,.2f}")
            y_position -= 15
        
        y_position -= 5
        pdf.drawString(self.margin, y_position, "─" * 60)
        y_position -= 15
        
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(self.margin, y_position, f"Total Credits: ${tax_credits.get('total_credits', 0):,.2f}")
        y_position -= 30
        
        # Final Computation
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(self.margin, y_position, "Amount You Owe or Refund")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        final_comp = tax_data.get('final_computation', {})
        
        pdf.drawString(self.margin, y_position, f"Total Tax: ${final_comp.get('total_tax', 0):,.2f}")
        y_position -= 15
        
        pdf.drawString(self.margin, y_position, f"Less: Total Credits: $({final_comp.get('total_credits', 0):,.2f})")
        y_position -= 15
        
        pdf.drawString(self.margin, y_position, "═" * 60)
        y_position -= 20
        
        pdf.setFont("Helvetica-Bold", 14)
        refund_or_owed = final_comp.get('refund_or_owed', 'owed')
        amount = final_comp.get('amount', 0)
        
        if refund_or_owed == 'refund':
            pdf.setFillColor(colors.green)
            pdf.drawString(self.margin, y_position, f"REFUND DUE: ${amount:,.2f}")
        else:
            pdf.setFillColor(colors.red)
            pdf.drawString(self.margin, y_position, f"AMOUNT OWED: ${amount:,.2f}")
        
        pdf.setFillColor(colors.black)
        y_position -= 40
        
        # Signature Section
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(self.margin, y_position, "Sign Here")
        y_position -= 20
        
        pdf.setFont("Helvetica", 8)
        pdf.drawString(self.margin, y_position, "Under penalties of perjury, I declare that I have examined this return and accompanying schedules and statements,")
        y_position -= 10
        pdf.drawString(self.margin, y_position, "and to the best of my knowledge and belief, they are true, correct, and complete.")
        y_position -= 20
        
        pdf.setFont("Helvetica", 10)
        pdf.drawString(self.margin, y_position, "Signature: _________________________________")
        pdf.drawString(self.margin + 300, y_position, f"Date: {date.today().strftime('%m/%d/%Y')}")
        
        # Add page number
        pdf.setFont("Helvetica", 8)
        pdf.drawString(self.page_width - self.margin - 50, self.margin / 2, "Page 3 of 3")
    
    async def generate_form_8843(
        self,
        user_data: Dict[str, Any],
        days_data: Dict[int, int],
        return_id: str
    ) -> Dict[str, Any]:
        """
        Generate Form 8843 (Statement for Exempt Individuals)
        
        Args:
            user_data: User profile data
            days_data: Days present in US by year
            return_id: Tax return ID
            
        Returns:
            Generated form metadata
        """
        try:
            logger.info("Generating Form 8843", return_id=return_id)
            
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            y_position = self.page_height - self.margin
            
            # Form header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(self.margin, y_position, "Form 8843")
            y_position -= 20
            
            pdf.setFont("Helvetica", 12)
            pdf.drawString(self.margin, y_position, "Statement for Exempt Individuals and Individuals With a Medical Condition")
            y_position -= 30
            
            # Personal Information
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Personal Information")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, f"Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"ITIN/SSN: {user_data.get('itin', 'XXX-XX-XXXX')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"Visa Status: {user_data.get('visa_class', '')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"Country of Tax Residence: {user_data.get('residency_country', '')}")
            y_position -= 30
            
            # Days Present in US
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Days Present in the United States")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            for year, days in sorted(days_data.items(), reverse=True):
                pdf.drawString(self.margin, y_position, f"{year}: {days} days")
                y_position -= 15
            
            y_position -= 20
            
            # Exempt Individual Status
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Exempt Individual Status")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, "I am claiming exempt individual status as a:")
            y_position -= 15
            
            visa_class = user_data.get('visa_class', '')
            if 'F-1' in visa_class or 'F1' in visa_class:
                pdf.drawString(self.margin + 20, y_position, "[X] Student (F-1)")
            elif 'J-1' in visa_class or 'J1' in visa_class:
                pdf.drawString(self.margin + 20, y_position, "[X] Scholar/Teacher (J-1)")
            else:
                pdf.drawString(self.margin + 20, y_position, f"[X] {visa_class}")
            
            # Save and upload
            pdf.save()
            
            pdf_content = buffer.getvalue()
            file_key = f"forms/{return_id}/8843_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            upload_result = await s3_service.upload_file(
                file_key=file_key,
                file_content=pdf_content,
                bucket=settings.S3_BUCKET_PDFS
            )
            
            logger.info("Form 8843 generated", return_id=return_id)
            
            return {
                "form_type": "8843",
                "file_key": file_key,
                "file_size": upload_result["size_bytes"],
                "generated_at": datetime.utcnow().isoformat(),
                "status": "generated"
            }
            
        except Exception as e:
            logger.error("Form 8843 generation failed", error=str(e))
            raise Exception(f"Failed to generate Form 8843: {str(e)}")
    
    async def generate_w8ben(
        self,
        user_data: Dict[str, Any],
        return_id: str
    ) -> Dict[str, Any]:
        """
        Generate Form W-8BEN (Certificate of Foreign Status)
        
        Args:
            user_data: User profile data
            return_id: Tax return ID
            
        Returns:
            Generated form metadata
        """
        try:
            logger.info("Generating Form W-8BEN", return_id=return_id)
            
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            y_position = self.page_height - self.margin
            
            # Form header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(self.margin, y_position, "Form W-8BEN")
            y_position -= 20
            
            pdf.setFont("Helvetica", 12)
            pdf.drawString(self.margin, y_position, "Certificate of Foreign Status of Beneficial Owner for United States Tax Withholding and Reporting")
            y_position -= 30
            
            # Part I: Identification
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Part I - Identification of Beneficial Owner")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, f"1. Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"2. Country of citizenship: {user_data.get('residency_country', '')}")
            y_position -= 15
            
            address = user_data.get('address_json', {})
            pdf.drawString(self.margin, y_position, f"3. Permanent residence address:")
            y_position -= 15
            pdf.drawString(self.margin + 20, y_position, f"{address.get('street', '')}")
            y_position -= 15
            pdf.drawString(self.margin + 20, y_position, f"{address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
            y_position -= 15
            pdf.drawString(self.margin + 20, y_position, f"{user_data.get('residency_country', '')}")
            y_position -= 20
            
            pdf.drawString(self.margin, y_position, f"5. U.S. taxpayer identification number (SSN or ITIN): {user_data.get('itin', 'XXX-XX-XXXX')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"6. Foreign tax identifying number (if any): _______________")
            y_position -= 30
            
            # Part II: Claim of Tax Treaty Benefits
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Part II - Claim of Tax Treaty Benefits")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, f"9. I certify that the beneficial owner is a resident of {user_data.get('residency_country', '')} within the meaning")
            y_position -= 15
            pdf.drawString(self.margin + 20, y_position, "of the income tax treaty between the United States and that country.")
            y_position -= 20
            
            # Signature Section
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Certification")
            y_position -= 20
            
            pdf.setFont("Helvetica", 8)
            pdf.drawString(self.margin, y_position, "Under penalties of perjury, I declare that I have examined the information on this form and to the best of my knowledge")
            y_position -= 10
            pdf.drawString(self.margin, y_position, "and belief it is true, correct, and complete.")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, "Signature: _________________________________")
            pdf.drawString(self.margin + 300, y_position, f"Date: {date.today().strftime('%m/%d/%Y')}")
            
            # Save and upload
            pdf.save()
            
            pdf_content = buffer.getvalue()
            file_key = f"forms/{return_id}/W8BEN_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            upload_result = await s3_service.upload_file(
                file_key=file_key,
                file_content=pdf_content,
                bucket=settings.S3_BUCKET_PDFS
            )
            
            logger.info("Form W-8BEN generated", return_id=return_id)
            
            return {
                "form_type": "W8BEN",
                "file_key": file_key,
                "file_size": upload_result["size_bytes"],
                "generated_at": datetime.utcnow().isoformat(),
                "status": "generated"
            }
            
        except Exception as e:
            logger.error("Form W-8BEN generation failed", error=str(e))
            raise Exception(f"Failed to generate Form W-8BEN: {str(e)}")
    
    async def generate_1040v(
        self,
        tax_data: Dict[str, Any],
        user_data: Dict[str, Any],
        return_id: str
    ) -> Dict[str, Any]:
        """
        Generate Form 1040-V (Payment Voucher)
        
        Args:
            tax_data: Tax computation data
            user_data: User profile data
            return_id: Tax return ID
            
        Returns:
            Generated form metadata
        """
        try:
            logger.info("Generating Form 1040-V", return_id=return_id)
            
            final_comp = tax_data.get('final_computation', {})
            
            # Only generate if taxpayer owes money
            if final_comp.get('refund_or_owed') != 'owed':
                return {
                    "form_type": "1040V",
                    "status": "not_required",
                    "message": "Payment voucher not required for refund"
                }
            
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            y_position = self.page_height - self.margin
            
            # Form header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(self.margin, y_position, "Form 1040-V")
            y_position -= 20
            
            pdf.setFont("Helvetica", 12)
            pdf.drawString(self.margin, y_position, "Payment Voucher")
            y_position -= 30
            
            # Payment Information
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(self.margin, y_position, f"Amount of Payment: ${final_comp.get('amount', 0):,.2f}")
            y_position -= 30
            
            # Personal Information
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, f"Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}")
            y_position -= 15
            
            pdf.drawString(self.margin, y_position, f"ITIN/SSN: {user_data.get('itin', 'XXX-XX-XXXX')}")
            y_position -= 15
            
            address = user_data.get('address_json', {})
            pdf.drawString(self.margin, y_position, f"Address: {address.get('street', '')}")
            y_position -= 15
            pdf.drawString(self.margin, y_position, f"         {address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
            y_position -= 30
            
            # Instructions
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(self.margin, y_position, "Instructions")
            y_position -= 20
            
            pdf.setFont("Helvetica", 10)
            pdf.drawString(self.margin, y_position, "• Make your check or money order payable to 'United States Treasury'")
            y_position -= 15
            pdf.drawString(self.margin, y_position, "• Write your ITIN/SSN, tax year, and '1040-NR' on your payment")
            y_position -= 15
            pdf.drawString(self.margin, y_position, "• Do not staple or attach your payment to this voucher")
            y_position -= 15
            pdf.drawString(self.margin, y_position, "• Mail this voucher with your payment to the IRS address for your state")
            
            # Save and upload
            pdf.save()
            
            pdf_content = buffer.getvalue()
            file_key = f"forms/{return_id}/1040V_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            upload_result = await s3_service.upload_file(
                file_key=file_key,
                file_content=pdf_content,
                bucket=settings.S3_BUCKET_PDFS
            )
            
            logger.info("Form 1040-V generated", return_id=return_id)
            
            return {
                "form_type": "1040V",
                "file_key": file_key,
                "file_size": upload_result["size_bytes"],
                "generated_at": datetime.utcnow().isoformat(),
                "status": "generated"
            }
            
        except Exception as e:
            logger.error("Form 1040-V generation failed", error=str(e))
            raise Exception(f"Failed to generate Form 1040-V: {str(e)}")
    
    async def generate_all_forms(
        self,
        tax_data: Dict[str, Any],
        user_data: Dict[str, Any],
        days_data: Dict[int, int],
        return_id: str
    ) -> Dict[str, Any]:
        """
        Generate all applicable tax forms
        
        Args:
            tax_data: Tax computation data
            user_data: User profile data
            days_data: Days present in US
            return_id: Tax return ID
            
        Returns:
            All generated forms metadata
        """
        try:
            logger.info("Generating all tax forms", return_id=return_id)
            
            forms = {}
            
            # Generate 1040-NR (always required)
            forms["1040NR"] = await self.generate_1040nr(tax_data, user_data, return_id)
            
            # Generate 8843 (for exempt individuals)
            visa_class = user_data.get('visa_class', '')
            if any(v in visa_class for v in ['F-1', 'F1', 'J-1', 'J1', 'M-1', 'M1', 'Q-1', 'Q1']):
                forms["8843"] = await self.generate_form_8843(user_data, days_data, return_id)
            
            # Generate W-8BEN (if claiming treaty benefits)
            treaty_benefits = tax_data.get('treaty_benefits', {})
            if treaty_benefits.get('has_treaty'):
                forms["W8BEN"] = await self.generate_w8ben(user_data, return_id)
            
            # Generate 1040-V (if payment required)
            final_comp = tax_data.get('final_computation', {})
            if final_comp.get('refund_or_owed') == 'owed':
                forms["1040V"] = await self.generate_1040v(tax_data, user_data, return_id)
            
            logger.info("All forms generated successfully", 
                       return_id=return_id,
                       forms_generated=list(forms.keys()))
            
            return {
                "return_id": return_id,
                "forms": forms,
                "total_forms": len(forms),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Batch form generation failed", error=str(e))
            raise Exception(f"Failed to generate all forms: {str(e)}")


# Global form generator instance
form_generator = FormGenerator()
