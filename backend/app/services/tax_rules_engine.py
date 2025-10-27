"""
Tax Rules Engine for Non-Resident Tax Calculations
Deterministic rules for residency tests, treaty articles, income sourcing, and credits
"""

import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import structlog

logger = structlog.get_logger()


class ResidencyStatus(Enum):
    RESIDENT = "resident"
    NON_RESIDENT = "non_resident"
    DUAL_STATUS = "dual_status"


class VisaType(Enum):
    H1B = "H1B"
    F1 = "F-1"
    F1_OPT = "F-1-OPT"
    J1 = "J-1"
    O1 = "O-1"
    TN = "TN"
    E2 = "E-2"
    L1 = "L-1"
    H4 = "H-4"
    OTHER = "OTHER"


class TaxTreatyCountry(Enum):
    INDIA = "IN"
    CHINA = "CN"
    CANADA = "CA"
    MEXICO = "MX"
    UK = "GB"
    GERMANY = "DE"
    FRANCE = "FR"
    JAPAN = "JP"
    SOUTH_KOREA = "KR"
    BRAZIL = "BR"


class TaxRulesEngine:
    """Deterministic tax rules engine for non-resident tax calculations"""
    
    def __init__(self, tax_year: int = None):
        self.tax_year = tax_year or datetime.now().year
        self.ruleset_version = f"v{self.tax_year}.1"
        
        # Load tax rates and thresholds for the year
        self.tax_rates = self._load_tax_rates()
        self.standard_deductions = self._load_standard_deductions()
        self.treaty_exemptions = self._load_treaty_exemptions()
        self.state_tax_rates = self._load_state_tax_rates()
    
    def _load_tax_rates(self) -> Dict[str, Any]:
        """Load federal tax rates for the tax year"""
        # 2024 tax brackets for non-residents (single filer)
        return {
            "non_resident_brackets": [
                {"min": 0, "max": 11000, "rate": 0.10},
                {"min": 11000, "max": 44725, "rate": 0.12},
                {"min": 44725, "max": 95375, "rate": 0.22},
                {"min": 95375, "max": 182100, "rate": 0.24},
                {"min": 182100, "max": 231250, "rate": 0.32},
                {"min": 231250, "max": 578125, "rate": 0.35},
                {"min": 578125, "max": float('inf'), "rate": 0.37}
            ],
            "social_security_rate": 0.062,
            "medicare_rate": 0.0145,
            "additional_medicare_threshold": 200000,
            "additional_medicare_rate": 0.009,
            "social_security_wage_base": 160200
        }
    
    def _load_standard_deductions(self) -> Dict[str, Decimal]:
        """Load standard deductions"""
        return {
            "single": Decimal("13850"),
            "married_filing_jointly": Decimal("27700"),
            "head_of_household": Decimal("20800")
        }
    
    def _load_treaty_exemptions(self) -> Dict[str, Dict[str, Any]]:
        """Load tax treaty exemptions by country, prevents double taxation"""
        return {
            "IN": {  # India
                "student_exemption": {
                    "amount": 5000,
                    "article": "Article 21",
                    "description": "Student exemption for scholarship/fellowship"
                },
                "teacher_exemption": {
                    "amount": None,  # Full exemption
                    "period_years": 2,
                    "article": "Article 21",
                    "description": "Teacher/researcher exemption for 2 years"
                },
                "business_profits": {
                    "article": "Article 7",
                    "description": "Business profits only taxed if permanent establishment"
                }
            },
            "CN": {  # China
                "student_exemption": {
                    "amount": None,  # Full exemption for training/education
                    "article": "Article 20",
                    "description": "Student exemption for scholarship/fellowship"
                },
                "teacher_exemption": {
                    "amount": None,
                    "period_years": 3,
                    "article": "Article 19",
                    "description": "Teacher/researcher exemption for 3 years"
                }
            },
            "CA": {  # Canada
                "student_exemption": {
                    "amount": None,
                    "article": "Article XX",
                    "description": "Student exemption for scholarship/fellowship"
                }
            }
        }
    
    def _load_state_tax_rates(self) -> Dict[str, Dict[str, Any]]:
        """Load state tax rates"""
        return {
            "CA": {  # California
                "tax_brackets": [
                    {"min": 0, "max": 10099, "rate": 0.01},
                    {"min": 10099, "max": 23942, "rate": 0.02},
                    {"min": 23942, "max": 37788, "rate": 0.04},
                    {"min": 37788, "max": 52455, "rate": 0.06},
                    {"min": 52455, "max": 66295, "rate": 0.08},
                    {"min": 66295, "max": 338639, "rate": 0.093},
                    {"min": 338639, "max": 406364, "rate": 0.103},
                    {"min": 406364, "max": 677275, "rate": 0.113},
                    {"min": 677275, "max": float('inf'), "rate": 0.123}
                ],
                "standard_deduction": 5202
            },
            "NY": {  # New York
                "tax_brackets": [
                    {"min": 0, "max": 8500, "rate": 0.04},
                    {"min": 8500, "max": 11700, "rate": 0.045},
                    {"min": 11700, "max": 13900, "rate": 0.0525},
                    {"min": 13900, "max": 80650, "rate": 0.0585},
                    {"min": 80650, "max": 215400, "rate": 0.0625},
                    {"min": 215400, "max": 1077550, "rate": 0.0685},
                    {"min": 1077550, "max": 5000000, "rate": 0.0965},
                    {"min": 5000000, "max": 25000000, "rate": 0.103},
                    {"min": 25000000, "max": float('inf'), "rate": 0.109}
                ],
                "standard_deduction": 8000
            },
            "TX": {  # Texas - No state income tax
                "tax_brackets": [],
                "standard_deduction": 0
            },
            "FL": {  # Florida - No state income tax
                "tax_brackets": [],
                "standard_deduction": 0
            },
            "WA": {  # Washington - No state income tax
                "tax_brackets": [],
                "standard_deduction": 0
            }
        }
    
    async def determine_residency_status(
        self,
        visa_type: str,
        entry_date: date,
        days_in_us: Dict[int, int],
        substantial_presence_override: bool = False
    ) -> Dict[str, Any]:
        """
        Determine residency status using Substantial Presence Test
        
        Args:
            visa_type: Visa classification
            entry_date: First entry date to US
            days_in_us: Dictionary of {year: days_present}
            substantial_presence_override: Manual override for exempt individuals
            
        Returns:
            Residency determination with reasoning
        """
        try:
            logger.info("Determining residency status", 
                       visa_type=visa_type,
                       tax_year=self.tax_year)
            
            # Check if exempt individual (F-1, J-1, etc.)
            is_exempt = await self._is_exempt_individual(visa_type, entry_date)
            
            if is_exempt and not substantial_presence_override:
                return {
                    "residency_status": ResidencyStatus.NON_RESIDENT.value,
                    "determination_method": "exempt_individual",
                    "reasoning": f"{visa_type} visa holders are exempt from substantial presence test",
                    "exempt_years_used": self._calculate_exempt_years(visa_type, entry_date),
                    "substantial_presence_days": 0,
                    "determined_at": datetime.utcnow().isoformat()
                }
            
            # Calculate substantial presence test
            substantial_presence_result = await self._calculate_substantial_presence(
                days_in_us
            )
            
            if substantial_presence_result["meets_test"]:
                return {
                    "residency_status": ResidencyStatus.RESIDENT.value,
                    "determination_method": "substantial_presence_test",
                    "reasoning": "Meets substantial presence test (>= 183 days)",
                    "substantial_presence_days": substantial_presence_result["total_days"],
                    "calculation_breakdown": substantial_presence_result["breakdown"],
                    "determined_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "residency_status": ResidencyStatus.NON_RESIDENT.value,
                    "determination_method": "substantial_presence_test",
                    "reasoning": "Does not meet substantial presence test (< 183 days)",
                    "substantial_presence_days": substantial_presence_result["total_days"],
                    "calculation_breakdown": substantial_presence_result["breakdown"],
                    "determined_at": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error("Residency determination failed", error=str(e))
            raise Exception(f"Failed to determine residency status: {str(e)}")
    
    async def _is_exempt_individual(self, visa_type: str, entry_date: date) -> bool:
        """
        Check if individual is exempt from SUBSTANTIAL PRESENCE TEST (days don't count)
        
        This is DIFFERENT from FICA exemption!
        
        Per IRS: https://www.irs.gov/individuals/international-taxpayers/substantial-presence-test
        - F-1, M-1, Q-1 students: Exempt for 5 calendar years (days don't count)
        - J-1 students: Exempt for 2 years
        - J-1 scholars/teachers: Exempt for 2 years out of last 6
        
        Result: If exempt, they remain NON-RESIDENT even if physically present 183+ days
        """
        exempt_visas = {
            "F-1": 5,  # 5 years - days don't count for substantial presence test
            "F-1-OPT": 5,
            "J-1": 2,  # 2 years for students, 2 of last 6 for scholars
            "M-1": 5,
            "Q-1": 5
        }
        
        if visa_type not in exempt_visas:
            return False
        
        # Calculate years since entry
        years_since_entry = (date(self.tax_year, 12, 31) - entry_date).days / 365.25
        
        return years_since_entry < exempt_visas[visa_type]
    
    def _calculate_exempt_years(self, visa_type: str, entry_date: date) -> int:
        """Calculate number of exempt years used"""
        years_since_entry = int((date(self.tax_year, 12, 31) - entry_date).days / 365.25)
        
        exempt_limits = {
            "F-1": 5,
            "F-1-OPT": 5,
            "J-1": 2,
            "M-1": 5,
            "Q-1": 5
        }
        
        limit = exempt_limits.get(visa_type, 0)
        return min(years_since_entry, limit)
    
    async def _calculate_substantial_presence(
        self,
        days_in_us: Dict[int, int]
    ) -> Dict[str, Any]:
        """
        Calculate substantial presence test
        Formula: Current year days + (1/3 * prior year days) + (1/6 * 2 years ago days)
        """
        current_year_days = days_in_us.get(self.tax_year, 0)
        prior_year_days = days_in_us.get(self.tax_year - 1, 0)
        two_years_ago_days = days_in_us.get(self.tax_year - 2, 0)
        
        weighted_prior_year = prior_year_days / 3
        weighted_two_years_ago = two_years_ago_days / 6
        
        total_days = current_year_days + weighted_prior_year + weighted_two_years_ago
        
        return {
            "meets_test": total_days >= 183,
            "total_days": round(total_days, 2),
            "breakdown": {
                "current_year": current_year_days,
                "prior_year": prior_year_days,
                "two_years_ago": two_years_ago_days,
                "weighted_prior_year": round(weighted_prior_year, 2),
                "weighted_two_years_ago": round(weighted_two_years_ago, 2)
            }
        }
    
    async def apply_treaty_benefits(
        self,
        country_code: str,
        visa_type: str,
        income_breakdown: Dict[str, Decimal],
        years_in_status: int
    ) -> Dict[str, Any]:
        """
        Apply tax treaty benefits based on country and visa status
        
        Args:
            country_code: ISO country code
            visa_type: Visa classification
            income_breakdown: Income by category
            years_in_status: Years in current visa status
            
        Returns:
            Treaty benefits application result
        """
        try:
            logger.info("Applying treaty benefits", 
                       country=country_code,
                       visa_type=visa_type)
            
            treaty_benefits = self.treaty_exemptions.get(country_code, {})
            
            if not treaty_benefits:
                return {
                    "has_treaty": False,
                    "treaty_country": country_code,
                    "exemptions_applied": [],
                    "total_exemption_amount": Decimal("0"),
                    "reasoning": f"No tax treaty with {country_code}"
                }
            
            exemptions_applied = []
            total_exemption = Decimal("0")
            
            # Check student exemption
            if visa_type in ["F-1", "F-1-OPT", "J-1"] and "student_exemption" in treaty_benefits:
                student_exemption = treaty_benefits["student_exemption"]
                scholarship_income = income_breakdown.get("scholarship", Decimal("0"))
                fellowship_income = income_breakdown.get("fellowship", Decimal("0"))
                
                exempt_amount = student_exemption.get("amount")
                if exempt_amount:
                    exemption = min(
                        Decimal(str(exempt_amount)),
                        scholarship_income + fellowship_income
                    )
                else:
                    exemption = scholarship_income + fellowship_income
                
                if exemption > 0:
                    exemptions_applied.append({
                        "type": "student_exemption",
                        "article": student_exemption.get("article"),
                        "amount": float(exemption),
                        "description": student_exemption.get("description")
                    })
                    total_exemption += exemption
            
            # Check teacher/researcher exemption
            if visa_type in ["J-1", "H1B"] and "teacher_exemption" in treaty_benefits:
                teacher_exemption = treaty_benefits["teacher_exemption"]
                teaching_income = income_breakdown.get("teaching", Decimal("0"))
                research_income = income_breakdown.get("research", Decimal("0"))
                
                period_years = teacher_exemption.get("period_years", 0)
                if years_in_status <= period_years:
                    exempt_amount = teacher_exemption.get("amount")
                    if exempt_amount:
                        exemption = min(
                            Decimal(str(exempt_amount)),
                            teaching_income + research_income
                        )
                    else:
                        exemption = teaching_income + research_income
                    
                    if exemption > 0:
                        exemptions_applied.append({
                            "type": "teacher_exemption",
                            "article": teacher_exemption.get("article"),
                            "amount": float(exemption),
                            "description": teacher_exemption.get("description"),
                            "years_remaining": period_years - years_in_status
                        })
                        total_exemption += exemption
            
            return {
                "has_treaty": True,
                "treaty_country": country_code,
                "exemptions_applied": exemptions_applied,
                "total_exemption_amount": float(total_exemption),
                "reasoning": f"Applied {len(exemptions_applied)} treaty exemption(s)",
                "applied_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Treaty benefits application failed", error=str(e))
            raise Exception(f"Failed to apply treaty benefits: {str(e)}")
    
    async def calculate_income_sourcing(
        self,
        income_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determine income sourcing (US vs Foreign) for non-resident taxation
        
        Args:
            income_data: Income breakdown with source information
            
        Returns:
            Income sourcing determination
        """
        try:
            logger.info("Calculating income sourcing")
            
            us_source_income = Decimal("0")
            foreign_source_income = Decimal("0")
            
            sourcing_breakdown = {
                "us_source": {},
                "foreign_source": {},
                "sourcing_rules_applied": []
            }
            
            # Wages - generally sourced based on where services performed
            wages = Decimal(str(income_data.get("wages", 0)))
            us_work_days = income_data.get("us_work_days", 0)
            total_work_days = income_data.get("total_work_days", us_work_days)
            
            if total_work_days > 0:
                us_wage_portion = wages * Decimal(str(us_work_days / total_work_days))
                foreign_wage_portion = wages - us_wage_portion
            else:
                us_wage_portion = wages
                foreign_wage_portion = Decimal("0")
            
            sourcing_breakdown["us_source"]["wages"] = float(us_wage_portion)
            sourcing_breakdown["foreign_source"]["wages"] = float(foreign_wage_portion)
            sourcing_breakdown["sourcing_rules_applied"].append({
                "income_type": "wages",
                "rule": "IRC Section 861(a)(3) - Services performed in US",
                "us_portion": float(us_wage_portion),
                "foreign_portion": float(foreign_wage_portion)
            })
            
            us_source_income += us_wage_portion
            foreign_source_income += foreign_wage_portion
            
            # Interest income - generally sourced based on payor residence
            interest = Decimal(str(income_data.get("interest", 0)))
            us_bank_interest = Decimal(str(income_data.get("us_bank_interest", interest)))
            foreign_bank_interest = interest - us_bank_interest
            
            sourcing_breakdown["us_source"]["interest"] = float(us_bank_interest)
            sourcing_breakdown["foreign_source"]["interest"] = float(foreign_bank_interest)
            sourcing_breakdown["sourcing_rules_applied"].append({
                "income_type": "interest",
                "rule": "IRC Section 861(a)(1) - Payor residence",
                "us_portion": float(us_bank_interest),
                "foreign_portion": float(foreign_bank_interest)
            })
            
            us_source_income += us_bank_interest
            foreign_source_income += foreign_bank_interest
            
            # Dividends - generally sourced based on corporation residence
            dividends = Decimal(str(income_data.get("dividends", 0)))
            us_corp_dividends = Decimal(str(income_data.get("us_corp_dividends", dividends)))
            foreign_corp_dividends = dividends - us_corp_dividends
            
            sourcing_breakdown["us_source"]["dividends"] = float(us_corp_dividends)
            sourcing_breakdown["foreign_source"]["dividends"] = float(foreign_corp_dividends)
            sourcing_breakdown["sourcing_rules_applied"].append({
                "income_type": "dividends",
                "rule": "IRC Section 861(a)(2) - Corporation residence",
                "us_portion": float(us_corp_dividends),
                "foreign_portion": float(foreign_corp_dividends)
            })
            
            us_source_income += us_corp_dividends
            foreign_source_income += foreign_corp_dividends
            
            # Self-employment income - sourced where services performed
            self_employment = Decimal(str(income_data.get("self_employment", 0)))
            us_self_employment = Decimal(str(income_data.get("us_self_employment", self_employment)))
            foreign_self_employment = self_employment - us_self_employment
            
            sourcing_breakdown["us_source"]["self_employment"] = float(us_self_employment)
            sourcing_breakdown["foreign_source"]["self_employment"] = float(foreign_self_employment)
            sourcing_breakdown["sourcing_rules_applied"].append({
                "income_type": "self_employment",
                "rule": "IRC Section 861(a)(3) - Services performed in US",
                "us_portion": float(us_self_employment),
                "foreign_portion": float(foreign_self_employment)
            })
            
            us_source_income += us_self_employment
            foreign_source_income += foreign_self_employment
            
            return {
                "total_us_source_income": float(us_source_income),
                "total_foreign_source_income": float(foreign_source_income),
                "sourcing_breakdown": sourcing_breakdown,
                "effectively_connected_income": float(us_source_income),  # ECI for non-residents
                "calculated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Income sourcing calculation failed", error=str(e))
            raise Exception(f"Failed to calculate income sourcing: {str(e)}")
    
    async def calculate_federal_tax(
        self,
        taxable_income: Decimal,
        filing_status: str = "single"
    ) -> Dict[str, Any]:
        """
        Calculate federal income tax using progressive brackets
        
        Args:
            taxable_income: Taxable income amount
            filing_status: Filing status (single, married, etc.)
            
        Returns:
            Tax calculation breakdown
        """
        try:
            logger.info("Calculating federal tax", 
                       taxable_income=float(taxable_income))
            
            brackets = self.tax_rates["non_resident_brackets"]
            
            total_tax = Decimal("0")
            tax_by_bracket = []
            
            for bracket in brackets:
                bracket_min = Decimal(str(bracket["min"]))
                bracket_max = Decimal(str(bracket["max"]))
                rate = Decimal(str(bracket["rate"]))
                
                if taxable_income <= bracket_min:
                    break
                
                taxable_in_bracket = min(taxable_income, bracket_max) - bracket_min
                if taxable_in_bracket > 0:
                    tax_in_bracket = taxable_in_bracket * rate
                    total_tax += tax_in_bracket
                    
                    tax_by_bracket.append({
                        "bracket": f"${bracket_min:,.0f} - ${bracket_max:,.0f}",
                        "rate": f"{rate * 100:.1f}%",
                        "taxable_amount": float(taxable_in_bracket),
                        "tax_amount": float(tax_in_bracket)
                    })
            
            effective_rate = (total_tax / taxable_income * 100) if taxable_income > 0 else Decimal("0")
            
            return {
                "taxable_income": float(taxable_income),
                "total_tax": float(total_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "effective_rate": float(effective_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "tax_by_bracket": tax_by_bracket,
                "filing_status": filing_status,
                "calculated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Federal tax calculation failed", error=str(e))
            raise Exception(f"Failed to calculate federal tax: {str(e)}")
    
    async def calculate_state_tax(
        self,
        state_code: str,
        taxable_income: Decimal,
        filing_status: str = "single"
    ) -> Dict[str, Any]:
        """
        Calculate state income tax
        
        Args:
            state_code: State abbreviation (e.g., CA, NY)
            taxable_income: Taxable income amount
            filing_status: Filing status
            
        Returns:
            State tax calculation
        """
        try:
            logger.info("Calculating state tax", 
                       state=state_code,
                       taxable_income=float(taxable_income))
            
            state_rules = self.state_tax_rates.get(state_code, {})
            
            if not state_rules or not state_rules.get("tax_brackets"):
                return {
                    "state": state_code,
                    "has_income_tax": False,
                    "total_tax": 0.0,
                    "effective_rate": 0.0,
                    "message": f"{state_code} has no state income tax"
                }
            
            brackets = state_rules["tax_brackets"]
            standard_deduction = Decimal(str(state_rules.get("standard_deduction", 0)))
            
            # Apply standard deduction
            state_taxable_income = max(Decimal("0"), taxable_income - standard_deduction)
            
            total_tax = Decimal("0")
            tax_by_bracket = []
            
            for bracket in brackets:
                bracket_min = Decimal(str(bracket["min"]))
                bracket_max = Decimal(str(bracket["max"]))
                rate = Decimal(str(bracket["rate"]))
                
                if state_taxable_income <= bracket_min:
                    break
                
                taxable_in_bracket = min(state_taxable_income, bracket_max) - bracket_min
                if taxable_in_bracket > 0:
                    tax_in_bracket = taxable_in_bracket * rate
                    total_tax += tax_in_bracket
                    
                    tax_by_bracket.append({
                        "bracket": f"${bracket_min:,.0f} - ${bracket_max:,.0f}",
                        "rate": f"{rate * 100:.2f}%",
                        "taxable_amount": float(taxable_in_bracket),
                        "tax_amount": float(tax_in_bracket)
                    })
            
            effective_rate = (total_tax / taxable_income * 100) if taxable_income > 0 else Decimal("0")
            
            return {
                "state": state_code,
                "has_income_tax": True,
                "taxable_income": float(taxable_income),
                "standard_deduction": float(standard_deduction),
                "state_taxable_income": float(state_taxable_income),
                "total_tax": float(total_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "effective_rate": float(effective_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "tax_by_bracket": tax_by_bracket,
                "calculated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("State tax calculation failed", error=str(e))
            raise Exception(f"Failed to calculate state tax: {str(e)}")
    
    async def calculate_tax_credits(
        self,
        income_data: Dict[str, Any],
        withholding_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate available tax credits for non-residents
        
        Args:
            income_data: Income information
            withholding_data: Tax withholding information
            
        Returns:
            Tax credits calculation
        """
        try:
            logger.info("Calculating tax credits")
            
            credits = {
                "total_credits": Decimal("0"),
                "credits_breakdown": [],
                "withholding_credits": {}
            }
            
            # Federal income tax withheld
            federal_withholding = Decimal(str(withholding_data.get("federal_income_tax", 0)))
            if federal_withholding > 0:
                credits["withholding_credits"]["federal_income_tax"] = float(federal_withholding)
                credits["credits_breakdown"].append({
                    "credit_type": "federal_withholding",
                    "amount": float(federal_withholding),
                    "description": "Federal income tax withheld"
                })
                credits["total_credits"] += federal_withholding
            
            # State income tax withheld (if applicable)
            state_withholding = Decimal(str(withholding_data.get("state_income_tax", 0)))
            if state_withholding > 0:
                credits["withholding_credits"]["state_income_tax"] = float(state_withholding)
                credits["credits_breakdown"].append({
                    "credit_type": "state_withholding",
                    "amount": float(state_withholding),
                    "description": "State income tax withheld"
                })
                credits["total_credits"] += state_withholding
            
            # Note: Non-residents typically don't qualify for most tax credits
            # (e.g., EITC, Child Tax Credit) unless they have US-source income
            
            return {
                "total_credits": float(credits["total_credits"]),
                "credits_breakdown": credits["credits_breakdown"],
                "withholding_credits": credits["withholding_credits"],
                "calculated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Tax credits calculation failed", error=str(e))
            raise Exception(f"Failed to calculate tax credits: {str(e)}")
    
    ### MOST IMPORTANT FUNCTION IN THE ENGINE ###
    async def compute_complete_tax_return(
        self,
        user_data: Dict[str, Any],
        income_data: Dict[str, Any],
        withholding_data: Dict[str, Any],
        days_in_us: Dict[int, int]
    ) -> Dict[str, Any]:
        """
        Compute complete tax return for non-resident
        
        Args:
            user_data: User information (visa, country, etc.)
            income_data: All income information
            withholding_data: Tax withholding information
            days_in_us: Days present in US by year
            
        Returns:
            Complete tax computation
        """
        try:
            logger.info("Computing complete tax return", tax_year=self.tax_year)
            
            computation_result = {
                "tax_year": self.tax_year,
                "ruleset_version": self.ruleset_version,
                "computed_at": datetime.utcnow().isoformat()
            }
            
            # Step 1: Determine residency status
            residency = await self.determine_residency_status(
                visa_type=user_data.get("visa_type"),
                entry_date=datetime.strptime(user_data.get("entry_date"), "%Y-%m-%d").date(),
                days_in_us=days_in_us
            )
            computation_result["residency_determination"] = residency
            
            # Step 2: Source income (US vs Foreign)
            income_sourcing = await self.calculate_income_sourcing(income_data)
            computation_result["income_sourcing"] = income_sourcing
            
            # Step 3: Apply treaty benefits
            treaty_benefits = await self.apply_treaty_benefits(
                country_code=user_data.get("country_code"),
                visa_type=user_data.get("visa_type"),
                income_breakdown=income_data,
                years_in_status=user_data.get("years_in_status", 0)
            )
            computation_result["treaty_benefits"] = treaty_benefits
            
            # Step 4: Calculate taxable income
            us_source_income = Decimal(str(income_sourcing["total_us_source_income"]))
            treaty_exemption = Decimal(str(treaty_benefits["total_exemption_amount"]))
            taxable_income = max(Decimal("0"), us_source_income - treaty_exemption)
            
            computation_result["taxable_income_calculation"] = {
                "us_source_income": float(us_source_income),
                "treaty_exemptions": float(treaty_exemption),
                "taxable_income": float(taxable_income)
            }
            
            # Step 5: Calculate federal tax
            federal_tax = await self.calculate_federal_tax(taxable_income)
            computation_result["federal_tax"] = federal_tax
            
            # Step 6: Calculate state tax (if applicable)
            state_code = user_data.get("state_code")
            if state_code:
                state_tax = await self.calculate_state_tax(state_code, taxable_income)
                computation_result["state_tax"] = state_tax
            
            # Step 7: Calculate tax credits
            tax_credits = await self.calculate_tax_credits(income_data, withholding_data)
            computation_result["tax_credits"] = tax_credits
            
            # Step 8: Calculate final tax liability
            total_tax = Decimal(str(federal_tax["total_tax"]))
            if state_code:
                total_tax += Decimal(str(computation_result["state_tax"]["total_tax"]))
            
            total_credits = Decimal(str(tax_credits["total_credits"]))
            tax_liability = total_tax - total_credits
            
            computation_result["final_computation"] = {
                "total_tax": float(total_tax),
                "total_credits": float(total_credits),
                "tax_liability": float(tax_liability),
                "refund_or_owed": "refund" if tax_liability < 0 else "owed",
                "amount": abs(float(tax_liability))
            }
            
            logger.info("Tax return computation completed", 
                       tax_liability=float(tax_liability),
                       residency=residency["residency_status"])
            
            return computation_result
            
        except Exception as e:
            logger.error("Tax return computation failed", error=str(e))
            raise Exception(f"Failed to compute tax return: {str(e)}")


# Global tax rules engine instance
def get_tax_rules_engine(tax_year: int = None) -> TaxRulesEngine:
    """Get tax rules engine instance for specific year"""
    return TaxRulesEngine(tax_year=tax_year)
