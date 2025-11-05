"""
Document Aggregation Service
Centralizes logic for aggregating income and withholding data from tax documents
"""

import json
from typing import Dict, Any, List
from datetime import datetime
import structlog

logger = structlog.get_logger()


class DocumentAggregationService:
    """Service for aggregating income and withholding data from extracted tax documents"""
    
    def __init__(self):
        pass
    
    def check_fica_exemption(self, visa_type: str, entry_date: str, tax_year: int) -> bool:
        """
        Check if student is exempt from FICA (Social Security + Medicare) taxes
        
        Per IRS: https://www.irs.gov/individuals/international-taxpayers/foreign-student-liability-for-social-security-and-medicare-taxes
        F-1, J-1, M-1, Q-1, Q-2 students are EXEMPT from FICA for first 5 calendar years in USA
        
        Args:
            visa_type: Visa classification (F-1, J-1, M-1, Q-1, Q-2, etc.)
            entry_date: First entry date to US (YYYY-MM-DD)
            tax_year: Tax year being filed
            
        Returns:
            True if FICA exempt, False if FICA applies
        """
        # Student visa types eligible for FICA exemption
        exempt_visas = ['F-1', 'F1', 'J-1', 'J1', 'M-1', 'M1', 'Q-1', 'Q1', 'Q-2', 'Q2']
        
        if visa_type not in exempt_visas:
            return False  # Not a student visa, FICA applies
        
        try:
            entry = datetime.strptime(entry_date, '%Y-%m-%d')
            entry_year = entry.year
            
            # Calculate years in US (5 calendar year rule)
            years_in_us = tax_year - entry_year + 1
            
            # Exempt if 5 or fewer calendar years
            return years_in_us <= 5
            
        except (ValueError, AttributeError):
            # If we can't determine, assume FICA applies (safer)
            return False
    
    async def aggregate_income_from_documents(self, documents: list) -> Dict[str, Any]:
        """
        Aggregate income from all extracted documents
        
        Supports: W-2, 1099-INT, 1099-NEC, 1099-DIV, 1099-G, 1099-MISC, 1099-B, 1099-R, 1098-T, 1042-S
        
        Args:
            documents: List of document records with extracted_json field
            
        Returns:
            Aggregated income data by category
        """
        income_data = {
            "wages": 0,
            "interest": 0,
            "dividends": 0,
            "qualified_dividends": 0,
            "capital_gains": 0,
            "self_employment": 0,
            "unemployment": 0,
            "state_refunds": 0,
            "rents": 0,
            "royalties": 0,
            "other_income": 0,
            "retirement_distributions": 0,
            "retirement_taxable": 0,
            "scholarships_grants": 0,
            "tuition_paid": 0,
            "foreign_income": 0,
            "us_work_days": 0,
            "total_work_days": 0
        }
        
        for doc in documents:
            if not doc.get("extracted_json"):
                continue
            
            logger.debug("Processing document", doc_type=doc.get('doc_type'))
            
            try:
                # JSONB columns are already parsed as dicts by asyncpg
                if isinstance(doc["extracted_json"], dict):
                    extracted_data = doc["extracted_json"]
                elif isinstance(doc["extracted_json"], str):
                    extracted_data = json.loads(doc["extracted_json"])
                else:
                    extracted_data = doc["extracted_json"]
                fields = extracted_data.get("extracted_fields", {})
                
                # W-2: Wage income
                if doc["doc_type"] == "W2":
                    wages = fields.get("wages", {}).get("value")
                    if wages:
                        income_data["wages"] += self._parse_currency(wages)
                
                # 1099-INT: Interest income
                elif doc["doc_type"] == "1099INT":
                    interest = fields.get("interest_income", {}).get("value")
                    if interest:
                        income_data["interest"] += self._parse_currency(interest)
                
                # 1099-NEC: Non-employee compensation
                elif doc["doc_type"] == "1099NEC":
                    comp = fields.get("nonemployee_compensation", {}).get("value")
                    if comp:
                        income_data["self_employment"] += self._parse_currency(comp)
                
                # 1099-DIV: Dividends and capital gains
                elif doc["doc_type"] == "1099DIV":
                    ordinary_div = fields.get("total_ordinary_dividends", {}).get("value")
                    if ordinary_div:
                        income_data["dividends"] += self._parse_currency(ordinary_div)
                    
                    qualified_div = fields.get("qualified_dividends", {}).get("value")
                    if qualified_div:
                        income_data["qualified_dividends"] += self._parse_currency(qualified_div)
                    
                    cap_gains = fields.get("total_capital_gain_distributions", {}).get("value")
                    if cap_gains:
                        income_data["capital_gains"] += self._parse_currency(cap_gains)
                
                # 1099-G: Government payments
                elif doc["doc_type"] == "1099G":
                    unemployment = fields.get("unemployment_compensation", {}).get("value")
                    if unemployment:
                        income_data["unemployment"] += self._parse_currency(unemployment)
                    
                    state_refund = fields.get("state_tax_refund", {}).get("value")
                    if state_refund:
                        income_data["state_refunds"] += self._parse_currency(state_refund)
                
                # 1099-MISC: Miscellaneous income
                elif doc["doc_type"] == "1099MISC":
                    rents = fields.get("rents", {}).get("value")
                    if rents:
                        income_data["rents"] += self._parse_currency(rents)
                    
                    royalties = fields.get("royalties", {}).get("value")
                    if royalties:
                        income_data["royalties"] += self._parse_currency(royalties)
                    
                    other = fields.get("other_income", {}).get("value")
                    if other:
                        income_data["other_income"] += self._parse_currency(other)
                
                # 1099-B: Broker transactions
                elif doc["doc_type"] == "1099B":
                    gain_loss = fields.get("gain_or_loss", {}).get("value")
                    if gain_loss:
                        # Handle negative values (losses)
                        income_data["capital_gains"] += self._parse_currency(gain_loss, allow_negative=True)
                
                # 1099-R: Retirement distributions
                elif doc["doc_type"] == "1099R":
                    gross = fields.get("gross_distribution", {}).get("value")
                    if gross:
                        income_data["retirement_distributions"] += self._parse_currency(gross)
                    
                    taxable = fields.get("taxable_amount", {}).get("value")
                    if taxable:
                        income_data["retirement_taxable"] += self._parse_currency(taxable)
                
                # 1098-T: Tuition (for education credits)
                elif doc["doc_type"] == "1098T":
                    tuition = fields.get("qualified_tuition_expenses", {}).get("value")
                    if tuition:
                        income_data["tuition_paid"] += self._parse_currency(tuition)
                    
                    scholarships = fields.get("scholarships_grants", {}).get("value")
                    if scholarships:
                        income_data["scholarships_grants"] += self._parse_currency(scholarships)
                
                # 1042-S: Foreign person's U.S. income
                elif doc["doc_type"] == "1042S":
                    gross_income = fields.get("gross_income", {}).get("value")
                    if gross_income:
                        income_data["foreign_income"] += self._parse_currency(gross_income)
                
            except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"Failed to process document {doc.get('id')}: {str(e)}")
                continue
        
        return income_data
    
    async def aggregate_withholding_from_documents(
        self, 
        documents: list, 
        visa_type: str = None, 
        entry_date: str = None, 
        tax_year: int = None
    ) -> Dict[str, Any]:
        """
        Aggregate withholding from all extracted documents
        
        Checks for FICA exemption per:
        https://www.irs.gov/individuals/international-taxpayers/foreign-student-liability-for-social-security-and-medicare-taxes
        
        Args:
            documents: List of document records with extracted_json field
            visa_type: Optional visa type for FICA exemption check
            entry_date: Optional entry date for FICA exemption check
            tax_year: Optional tax year for FICA exemption check
            
        Returns:
            Aggregated withholding data with FICA exemption analysis
        """
        withholding_data = {
            "federal_income_tax": 0,
            "social_security_tax": 0,
            "medicare_tax": 0,
            "state_income_tax": 0,
            "foreign_tax": 0,
            "fica_exempt": False,
            "incorrect_fica_withheld": 0,
            "fica_refund_eligible": False
        }
        
        # Check if student is FICA exempt
        if visa_type and entry_date and tax_year:
            withholding_data["fica_exempt"] = self.check_fica_exemption(visa_type, entry_date, tax_year)
        
        for doc in documents:
            if not doc.get("extracted_json"):
                continue
            
            try:
                # JSONB columns are already parsed as dicts by asyncpg
                if isinstance(doc["extracted_json"], dict):
                    extracted_data = doc["extracted_json"]
                elif isinstance(doc["extracted_json"], str):
                    extracted_data = json.loads(doc["extracted_json"])
                else:
                    extracted_data = doc["extracted_json"]
                fields = extracted_data.get("extracted_fields", {})
                
                # Federal income tax (all forms)
                federal_tax = fields.get("federal_income_tax_withheld", {}).get("value")
                if not federal_tax:
                    federal_tax = fields.get("federal_tax_withheld", {}).get("value")  # 1042-S variation
                if federal_tax:
                    withholding_data["federal_income_tax"] += self._parse_currency(federal_tax)
                
                # Social Security tax (W-2 only) - Check for FICA exemption
                ss_tax = fields.get("social_security_tax_withheld", {}).get("value")
                if ss_tax:
                    ss_amount = self._parse_currency(ss_tax)
                    withholding_data["social_security_tax"] += ss_amount
                    
                    # If FICA exempt but SS tax was withheld, it's incorrect!
                    if withholding_data["fica_exempt"]:
                        withholding_data["incorrect_fica_withheld"] += ss_amount
                
                # Medicare tax (W-2 only) - Check for FICA exemption
                medicare_tax = fields.get("medicare_tax_withheld", {}).get("value")
                if medicare_tax:
                    medicare_amount = self._parse_currency(medicare_tax)
                    withholding_data["medicare_tax"] += medicare_amount
                    
                    # If FICA exempt but Medicare tax was withheld, it's incorrect!
                    if withholding_data["fica_exempt"]:
                        withholding_data["incorrect_fica_withheld"] += medicare_amount
                
                # State income tax (1099-G, W-2)
                state_tax = fields.get("state_income_tax_withheld", {}).get("value")
                if state_tax:
                    withholding_data["state_income_tax"] += self._parse_currency(state_tax)
                
                # Foreign tax paid (1099-DIV)
                foreign_tax = fields.get("foreign_tax_paid", {}).get("value")
                if foreign_tax:
                    withholding_data["foreign_tax"] += self._parse_currency(foreign_tax)
                
            except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"Failed to process withholding from document {doc.get('id')}: {str(e)}")
                continue
        
        # Flag if student can claim FICA refund
        if withholding_data["incorrect_fica_withheld"] > 0:
            withholding_data["fica_refund_eligible"] = True
        
        return withholding_data
    
    def _parse_currency(self, value: str, allow_negative: bool = False) -> float:
        """
        Parse currency string to float
        
        Args:
            value: Currency string (e.g., "$1,234.56" or "1234.56")
            allow_negative: Whether to allow negative values (for losses)
            
        Returns:
            Parsed float value
        """
        if not value:
            return 0.0
        
        try:
            # Remove currency symbols and commas
            cleaned = str(value).replace("$", "").replace(",", "").strip()
            
            # Handle negative values
            if cleaned.startswith("-") or cleaned.startswith("("):
                if allow_negative:
                    cleaned = cleaned.replace("(", "").replace(")", "")
                    return -float(cleaned) if cleaned.startswith("-") else -float(cleaned)
                else:
                    cleaned = cleaned.replace("-", "")
            
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0


# Global instance
document_aggregation_service = DocumentAggregationService()

