"""
OpenAI Chat Service with Tool Calling
"""

import json
import openai
from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog

from app.core.config import settings
from app.services.tax_rules_engine import get_tax_rules_engine
from app.services.extraction_pipeline import ExtractionPipeline
from app.core.database import get_database

logger = structlog.get_logger()

# Initialize OpenAI client
openai.api_key = settings.OPENAI_API_KEY

# Substantial Presence Test/Residency Status Determination:
# https://www.irs.gov/individuals/international-taxpayers/determining-an-individuals-tax-residency-status
# https://www.irs.gov/individuals/international-taxpayers/substantial-presence-test
# You will be considered a United States resident for tax purposes if you meet the substantial presence test for the calendar year. To meet this test, you must be physically present in the United States (U.S.) on at least:

# 31 days during the current year, and
# 183 days during the 3-year period that includes the current year and the 2 years immediately before that, counting:
# All the days you were present in the current year, and
# 1/3 of the days you were present in the first year before the current year, and
# 1/6 of the days you were present in the second year before the current year.

# Formula:
# Total = (Current Year Days) + (Prior Year Days × 1/3) + (Two Years Ago Days × 1/6)
# Result: Resident if Current Year ≥ 31 AND Total ≥ 183 days

# Tax Treaty Benefits:
# https://www.irs.gov/individuals/international-taxpayers/tax-treaties

class ChatService:
    """OpenAI-powered chat service with tool calling for tax assistance"""
    
    def __init__(self, db):
        self.db = db
        self.model = "gpt-4-turbo-preview"
        
        # Define available tools for the agent
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_document_status",
                    "description": "Get the status of uploaded documents and their extraction progress",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "return_id": {
                                "type": "string",
                                "description": "The tax return ID to check documents for"
                            }
                        },
                        "required": ["return_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "compute_tax_liability",
                    "description": "Compute the tax liability for a non-resident based on their income and visa status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "return_id": {
                                "type": "string",
                                "description": "The tax return ID to compute"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "The user ID"
                            }
                        },
                        "required": ["return_id", "user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_residency_status",
                    "description": "Determine if a person qualifies as a resident or non-resident for tax purposes using the substantial presence test",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "visa_type": {
                                "type": "string",
                                "description": "Visa classification (e.g., H1B, F-1, J-1, O-1, E2, TN, etc.)"
                            },
                            "entry_date": {
                                "type": "string",
                                "description": "First entry date to US (YYYY-MM-DD)"
                            },
                            "days_current_year": {
                                "type": "integer",
                                "description": "Days present in current year"
                            },
                            "days_prior_year": {
                                "type": "integer",
                                "description": "Days present in prior year"
                            },
                            "days_two_years_ago": {
                                "type": "integer",
                                "description": "Days present two years ago"
                            },
                            "tax_year": {
                                "type": "integer",
                                "description": "Tax year to check"
                            }
                        },
                        "required": ["visa_type", "days_current_year", "days_prior_year", "days_two_years_ago", "tax_year"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_fica_exemption",
                    "description": "Check if student is exempt from FICA (Social Security + Medicare) taxes. F-1, J-1, M-1, Q-1, Q-2 students are exempt for first 5 calendar years in USA. Alerts if FICA was incorrectly withheld and student can claim refund via Form 843.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "visa_type": {
                                "type": "string",
                                "description": "Visa classification (F-1, J-1, M-1, Q-1, Q-2, H1B, etc.)"
                            },
                            "entry_date": {
                                "type": "string",
                                "description": "First entry date to US (YYYY-MM-DD)"
                            },
                            "tax_year": {
                                "type": "integer",
                                "description": "Tax year to check"
                            }
                        },
                        "required": ["visa_type", "entry_date", "tax_year"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_treaty_benefits",
                    "description": "Check available tax treaty benefits based on country of residence",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "country_code": {
                                "type": "string",
                                "description": "ISO country code (e.g., IN for India, CN for China)"
                            },
                            "visa_type": {
                                "type": "string",
                                "description": "Visa classification"
                            },
                            "years_in_status": {
                                "type": "integer",
                                "description": "Years in current visa status"
                            }
                        },
                        "required": ["country_code", "visa_type", "years_in_status"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tax_return_summary",
                    "description": "Get a summary of the tax return including computed values and status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "return_id": {
                                "type": "string",
                                "description": "The tax return ID"
                            }
                        },
                        "required": ["return_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "start_document_extraction",
                    "description": "Start OCR extraction for an uploaded document",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "The document ID to extract"
                            }
                        },
                        "required": ["document_id"]
                    }
                }
            }
        ]
        
        # System prompt for the tax assistant
        self.system_prompt = """You are a knowledgeable tax assistant specializing in US non-resident tax preparation for individuals on work visas (H1B, F-1, O-1, J-1, TN, E2, etc.).

Your role is to:
1. Help users understand their tax obligations as non-residents
2. Guide them through document upload and tax return preparation
3. Explain residency status, tax treaty benefits, and income sourcing rules
4. Use the available tools to check status, compute taxes, and retrieve information
5. Provide clear, accurate information based on IRS rules and regulations

Important guidelines:
- Always be clear that you provide information, not legal advice
- For complex situations, recommend consulting a licensed tax professional
- Use deterministic tax calculation tools rather than estimating
- Explain tax concepts in simple terms
- Be patient and thorough in your explanations

When users ask about their tax situation:
1. First understand their visa type and residency country
2. Check their residency status using the substantial presence test
3. Identify applicable tax treaty benefits
4. Guide them through document upload if needed
5. Compute their tax liability when all information is available

Remember: Tax preparation requires accuracy. Always use the tools to get exact calculations rather than approximating."""
    
    async def send_message(
        self,
        session_id: str,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message and get AI response with tool calling
        
        Args:
            session_id: Chat session ID
            user_id: User ID
            message: User message
            context: Optional context (return_id, etc.)
            
        Returns:
            AI response with tool calls if applicable
        """
        try:
            logger.info("Processing chat message", session_id=session_id, user_id=user_id)
            
            # Get chat history
            chat_history = await self._get_chat_history(session_id)
            
            # Build messages for OpenAI
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add chat history
            for msg in chat_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add new user message
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Store user message
            await self._store_message(session_id, "user", message)
            
            # Call OpenAI with tools
            response = await self._call_openai_with_tools(
                messages=messages,
                user_id=user_id,
                context=context
            )
            
            # Store assistant response
            await self._store_message(
                session_id, 
                "assistant", 
                response["content"],
                tool_calls=response.get("tool_calls")
            )
            
            return {
                "session_id": session_id,
                "message": response["content"],
                "tool_calls": response.get("tool_calls", []),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Chat message processing failed", error=str(e))
            raise Exception(f"Failed to process chat message: {str(e)}")
    
    async def _call_openai_with_tools(
        self,
        messages: List[Dict[str, Any]],
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call OpenAI API with tool support"""
        try:
            # Initial API call
            response = openai.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500
            )
            
            message = response.choices[0].message
            
            # Check if tool calls are needed
            if message.tool_calls:
                # Execute tool calls
                tool_results = []
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info("Executing tool call", 
                               function=function_name,
                               args=function_args)
                    
                    # Execute the function
                    result = await self._execute_tool(
                        function_name,
                        function_args,
                        user_id,
                        context
                    )
                    
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "function_name": function_name,
                        "result": result
                    })
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
                
                # Get final response with tool results
                final_response = openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1500
                )
                
                final_message = final_response.choices[0].message
                
                return {
                    "content": final_message.content,
                    "tool_calls": tool_results
                }
            else:
                # No tool calls needed
                return {
                    "content": message.content,
                    "tool_calls": []
                }
            
        except Exception as e:
            logger.error("OpenAI API call failed", error=str(e))
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def _execute_tool(
        self,
        function_name: str,
        function_args: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a tool function"""
        try:
            if function_name == "get_document_status":
                return await self._tool_get_document_status(
                    function_args.get("return_id"),
                    user_id
                )
            
            elif function_name == "compute_tax_liability":
                return await self._tool_compute_tax_liability(
                    function_args.get("return_id"),
                    function_args.get("user_id")
                )
            
            elif function_name == "check_residency_status":
                return await self._tool_check_residency_status(function_args)
            
            elif function_name == "check_fica_exemption":
                return await self._tool_check_fica_exemption(function_args)
            
            elif function_name == "check_treaty_benefits":
                return await self._tool_check_treaty_benefits(function_args)
            
            elif function_name == "get_tax_return_summary":
                return await self._tool_get_tax_return_summary(
                    function_args.get("return_id"),
                    user_id
                )
            
            elif function_name == "start_document_extraction":
                return await self._tool_start_document_extraction(
                    function_args.get("document_id"),
                    user_id
                )
            
            else:
                return {"error": f"Unknown function: {function_name}"}
            
        except Exception as e:
            logger.error("Tool execution failed", 
                        function=function_name, 
                        error=str(e))
            return {"error": str(e)}
    
    # Tool implementation methods
    async def _tool_get_document_status(
        self,
        return_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get document status for a tax return"""
        try:
            documents = await self.db.fetch_all(
                """
                SELECT id, doc_type, status, created_at 
                FROM documents 
                WHERE return_id = :return_id AND user_id = :user_id
                ORDER BY created_at DESC
                """,
                {"return_id": return_id, "user_id": user_id}
            )
            
            doc_list = []
            for doc in documents:
                doc_list.append({
                    "id": str(doc["id"]),
                    "type": doc["doc_type"],
                    "status": doc["status"],
                    "uploaded_at": doc["created_at"].isoformat() if doc["created_at"] else None
                })
            
            return {
                "return_id": return_id,
                "documents": doc_list,
                "total_documents": len(doc_list),
                "extracted_documents": len([d for d in doc_list if d["status"] == "extracted"])
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_compute_tax_liability(
        self,
        return_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Compute tax liability using the tax rules engine"""
        try:
            # Get tax return
            tax_return = await self.db.fetch_one(
                """
                SELECT * FROM tax_returns 
                WHERE id = :return_id AND user_id = :user_id
                """,
                {"return_id": return_id, "user_id": user_id}
            )
            
            if not tax_return:
                return {"error": "Tax return not found"}
            
            # Get user profile
            user_profile = await self.db.fetch_one(
                "SELECT * FROM user_profiles WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            if not user_profile:
                return {"error": "User profile not found"}
            
            # Get documents
            documents = await self.db.fetch_all(
                """
                SELECT * FROM documents 
                WHERE return_id = :return_id AND status = 'extracted'
                """,
                {"return_id": return_id}
            )
            
            if not documents:
                return {"error": "No extracted documents found. Please upload and extract documents first."}
            
            # Aggregate income and withholding data
            income_data = await self._aggregate_income_from_documents(documents)
            withholding_data = await self._aggregate_withholding_from_documents(documents)
            
            # Prepare user data
            user_data = {
                "visa_type": user_profile.get("visa_class", "H1B"),
                "country_code": user_profile.get("residency_country", "IN"),
                "entry_date": "2020-01-01",  # Should be in profile
                "years_in_status": 2,
                "state_code": "CA"
            }
            
            # Days in US (simplified - should be from user input)
            days_in_us = {
                tax_return["tax_year"]: 300,
                tax_return["tax_year"] - 1: 280,
                tax_return["tax_year"] - 2: 250
            }
            
            # Compute tax
            tax_engine = get_tax_rules_engine(tax_return["tax_year"])
            computation = await tax_engine.compute_complete_tax_return(
                user_data=user_data,
                income_data=income_data,
                withholding_data=withholding_data,
                days_in_us=days_in_us
            )
            
            return {
                "return_id": return_id,
                "tax_year": tax_return["tax_year"],
                "computation": computation,
                "summary": {
                    "residency_status": computation["residency_determination"]["residency_status"],
                    "us_source_income": computation["income_sourcing"]["total_us_source_income"],
                    "taxable_income": computation["taxable_income_calculation"]["taxable_income"],
                    "federal_tax": computation["federal_tax"]["total_tax"],
                    "total_credits": computation["tax_credits"]["total_credits"],
                    "tax_liability": computation["final_computation"]["tax_liability"],
                    "refund_or_owed": computation["final_computation"]["refund_or_owed"],
                    "amount": computation["final_computation"]["amount"]
                }
            }
            
        except Exception as e:
            logger.error("Tax computation tool failed", error=str(e))
            return {"error": str(e)}
    
    async def _tool_check_residency_status(
        self,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check residency status using substantial presence test"""
        try:
            from datetime import date
            
            visa_type = args.get("visa_type")
            entry_date_str = args.get("entry_date", "2020-01-01")
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
            
            tax_year = args.get("tax_year", datetime.now().year)
            
            days_in_us = {
                tax_year: args.get("days_current_year", 0),
                tax_year - 1: args.get("days_prior_year", 0),
                tax_year - 2: args.get("days_two_years_ago", 0)
            }
            
            tax_engine = get_tax_rules_engine(tax_year)
            residency = await tax_engine.determine_residency_status(
                visa_type=visa_type,
                entry_date=entry_date,
                days_in_us=days_in_us
            )
            
            return residency
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_check_treaty_benefits(
        self,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check tax treaty benefits"""
        try:
            country_code = args.get("country_code")
            visa_type = args.get("visa_type")
            years_in_status = args.get("years_in_status", 0)
            
            # Sample income breakdown for treaty check
            income_breakdown = {
                "scholarship": 0,
                "fellowship": 0,
                "teaching": 0,
                "research": 0
            }
            
            tax_engine = get_tax_rules_engine()
            treaty_benefits = await tax_engine.apply_treaty_benefits(
                country_code=country_code,
                visa_type=visa_type,
                income_breakdown=income_breakdown,
                years_in_status=years_in_status
            )
            
            return treaty_benefits
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_check_fica_exemption(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if student is exempt from FICA taxes
        
        Per IRS rules: https://www.irs.gov/individuals/international-taxpayers/foreign-student-liability-for-social-security-and-medicare-taxes
        F-1, J-1, M-1, Q-1, Q-2 students are exempt from FICA for first 5 calendar years
        """
        try:
            visa_type = args.get("visa_type")
            entry_date = args.get("entry_date")
            tax_year = args.get("tax_year")
            
            is_exempt = self._check_fica_exemption(visa_type, entry_date, tax_year)
            
            # Calculate years in US
            from datetime import datetime
            entry = datetime.strptime(entry_date, '%Y-%m-%d')
            years_in_us = tax_year - entry.year + 1
            
            result = {
                "visa_type": visa_type,
                "entry_date": entry_date,
                "tax_year": tax_year,
                "years_in_us": years_in_us,
                "fica_exempt": is_exempt,
                "social_security_exempt": is_exempt,
                "medicare_exempt": is_exempt,
                "exemption_years_remaining": max(0, 5 - years_in_us) if is_exempt else 0,
                "message": ""
            }
            
            if is_exempt:
                result["message"] = (
                    f"✅ You ARE EXEMPT from FICA taxes for {tax_year}. "
                    f"You are in year {years_in_us} of your 5-year exemption period. "
                    f"Social Security and Medicare taxes should NOT be withheld from your wages. "
                    f"If your W-2 shows these taxes were withheld, you can file Form 843 for a refund."
                )
                result["action_required"] = "Check W-2 for incorrect FICA withholding"
                result["refund_form"] = "Form 843 + Form 8316"
            else:
                if years_in_us > 5:
                    result["message"] = (
                        f"❌ You are NOT EXEMPT from FICA taxes for {tax_year}. "
                        f"You have been in the US for {years_in_us} calendar years (exemption is only first 5 years). "
                        f"Social Security and Medicare taxes should be withheld from your wages."
                    )
                else:
                    result["message"] = (
                        f"❌ You are NOT EXEMPT from FICA taxes because your visa type ({visa_type}) "
                        f"is not eligible for the student FICA exemption. "
                        f"Only F-1, J-1, M-1, Q-1, and Q-2 visa holders qualify."
                    )
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_get_tax_return_summary(
        self,
        return_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get tax return summary"""
        try:
            tax_return = await self.db.fetch_one(
                """
                SELECT * FROM tax_returns 
                WHERE id = :return_id AND user_id = :user_id
                """,
                {"return_id": return_id, "user_id": user_id}
            )
            
            if not tax_return:
                return {"error": "Tax return not found"}
            
            return {
                "return_id": return_id,
                "tax_year": tax_return["tax_year"],
                "status": tax_return["status"],
                "ruleset_version": tax_return["ruleset_version"],
                "created_at": tax_return["created_at"].isoformat() if tax_return["created_at"] else None
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_start_document_extraction(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Start document extraction"""
        try:
            pipeline = ExtractionPipeline(self.db)
            result = await pipeline.start_extraction(document_id, user_id)
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_chat_history(self, session_id: str) -> List[Dict[str, Any]]: 
        """Get chat history for a session
        
        Args:
            session_id: The ID of the session to get chat history for

        Returns:
            A list of messages in the session

        Raises:
            Exception: If there is an error getting the chat history
        """
        try:
            messages = await self.db.fetch_all(
                """
                SELECT role, content, tool_calls_json, created_at 
                FROM chat_messages 
                WHERE session_id = :session_id
                ORDER BY created_at ASC
                LIMIT 50
                """,
                {"session_id": session_id}
            )
            
            history = []
            for msg in messages:
                history.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "tool_calls": json.loads(msg["tool_calls_json"]) if msg.get("tool_calls_json") else None
                })
            
            return history
            
        except Exception as e:
            logger.error("Failed to get chat history", error=str(e))
            return []
    
    async def _store_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ):
        """Store message in database for a session
        
        Args:
            session_id: The ID of the session to store the message for
            role: The role of the message (user or assistant)
            content: The content of the message
            tool_calls: The tool calls made in the message
        """
        try:
            await self.db.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, tool_calls_json)
                VALUES (:session_id, :role, :content, :tool_calls)
                """,
                {
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "tool_calls": json.dumps(tool_calls) if tool_calls else None
                }
            )
            
        except Exception as e:
            logger.error("Failed to store message", error=str(e))
    
    async def _aggregate_income_from_documents(self, documents: list) -> Dict[str, Any]:
        """Aggregate income from extracted documents"""
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
            
            print(f"Processing document: {doc['doc_type']}")
            
            try:
                extracted_data = json.loads(doc["extracted_json"])
                print(f"Extracted data: {extracted_data}")
                fields = extracted_data.get("extracted_fields", {})
                
                # W-2: Wage income
                if doc["doc_type"] == "W2":
                    wages = fields.get("wages", {}).get("value")
                    if wages:
                        income_data["wages"] += float(wages.replace(",", "").replace("$", ""))
                
                # 1099-INT: Interest income
                elif doc["doc_type"] == "1099INT":
                    interest = fields.get("interest_income", {}).get("value")
                    if interest:
                        income_data["interest"] += float(interest.replace(",", "").replace("$", ""))
                
                # 1099-NEC: Non-employee compensation
                elif doc["doc_type"] == "1099NEC":
                    comp = fields.get("nonemployee_compensation", {}).get("value")
                    if comp:
                        income_data["self_employment"] += float(comp.replace(",", "").replace("$", ""))
                
                # 1099-DIV: Dividends and capital gains
                elif doc["doc_type"] == "1099DIV":
                    ordinary_div = fields.get("total_ordinary_dividends", {}).get("value")
                    if ordinary_div:
                        income_data["dividends"] += float(ordinary_div.replace(",", "").replace("$", ""))
                    
                    qualified_div = fields.get("qualified_dividends", {}).get("value")
                    if qualified_div:
                        # Converts the qualified dividends to decimal value and replaces the $ sign with an empty string
                        income_data["qualified_dividends"] += float(qualified_div.replace(",", "").replace("$", ""))
                    
                    cap_gains = fields.get("total_capital_gain_distributions", {}).get("value")
                    if cap_gains:
                        income_data["capital_gains"] += float(cap_gains.replace(",", "").replace("$", ""))
                
                # 1099-G: Government payments
                elif doc["doc_type"] == "1099G":
                    unemployment = fields.get("unemployment_compensation", {}).get("value")
                    if unemployment:
                        income_data["unemployment"] += float(unemployment.replace(",", "").replace("$", ""))
                    
                    state_refund = fields.get("state_tax_refund", {}).get("value")
                    if state_refund:
                        income_data["state_refunds"] += float(state_refund.replace(",", "").replace("$", ""))
                
                # 1099-MISC: Miscellaneous income
                elif doc["doc_type"] == "1099MISC":
                    rents = fields.get("rents", {}).get("value")
                    if rents:
                        income_data["rents"] += float(rents.replace(",", "").replace("$", ""))
                    
                    royalties = fields.get("royalties", {}).get("value")
                    if royalties:
                        income_data["royalties"] += float(royalties.replace(",", "").replace("$", ""))
                    
                    other = fields.get("other_income", {}).get("value")
                    if other:
                        income_data["other_income"] += float(other.replace(",", "").replace("$", ""))
                
                # 1099-B: Broker transactions (capital gains/losses)
                elif doc["doc_type"] == "1099B":
                    gain_loss = fields.get("gain_or_loss", {}).get("value")
                    if gain_loss:
                        income_data["capital_gains"] += float(gain_loss.replace(",", "").replace("$", "").replace("-", ""))
                
                # 1099-R: Retirement distributions
                elif doc["doc_type"] == "1099R":
                    gross = fields.get("gross_distribution", {}).get("value")
                    if gross:
                        income_data["retirement_distributions"] += float(gross.replace(",", "").replace("$", ""))
                    
                    taxable = fields.get("taxable_amount", {}).get("value")
                    if taxable:
                        income_data["retirement_taxable"] += float(taxable.replace(",", "").replace("$", ""))
                
                # 1098-T: Tuition (for education credits)
                elif doc["doc_type"] == "1098T":
                    tuition = fields.get("qualified_tuition_expenses", {}).get("value")
                    if tuition:
                        income_data["tuition_paid"] += float(tuition.replace(",", "").replace("$", ""))
                    
                    scholarships = fields.get("scholarships_grants", {}).get("value")
                    if scholarships:
                        income_data["scholarships_grants"] += float(scholarships.replace(",", "").replace("$", ""))
                
                # 1042-S: Foreign person's U.S. income
                elif doc["doc_type"] == "1042S":
                    gross_income = fields.get("gross_income", {}).get("value")
                    if gross_income:
                        income_data["foreign_income"] += float(gross_income.replace(",", "").replace("$", ""))
                
            except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"Failed to process document {doc.get('id')}: {str(e)}")
                continue
        
        return income_data
    
    def _check_fica_exemption(self, visa_type: str, entry_date: str, tax_year: int) -> bool:
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
            from datetime import datetime
            entry = datetime.strptime(entry_date, '%Y-%m-%d')
            entry_year = entry.year
            
            # Calculate years in US (5 calendar year rule)
            years_in_us = tax_year - entry_year + 1
            
            # Exempt if 5 or fewer calendar years
            return years_in_us <= 5
            
        except (ValueError, AttributeError):
            # If we can't determine, assume FICA applies (safer)
            return False
    
    async def _aggregate_withholding_from_documents(self, documents: list, visa_type: str = None, entry_date: str = None, tax_year: int = None) -> Dict[str, Any]:
        """
        Aggregate withholding from extracted documents
        
        Checks for FICA exemption per:
        https://www.irs.gov/individuals/international-taxpayers/foreign-student-liability-for-social-security-and-medicare-taxes
        """
        withholding_data = {
            "federal_income_tax": 0,
            "social_security_tax": 0,
            "medicare_tax": 0,
            "state_income_tax": 0,
            "foreign_tax": 0,
            "fica_exempt": False,
            "incorrect_fica_withheld": 0,  # Amount that can be refunded
            "fica_refund_eligible": False
        }
        
        # Check if student is FICA exempt
        if visa_type and entry_date and tax_year:
            withholding_data["fica_exempt"] = self._check_fica_exemption(visa_type, entry_date, tax_year)
        
        for doc in documents:
            if not doc.get("extracted_json"):
                continue
            
            try:
                extracted_data = json.loads(doc["extracted_json"])
                fields = extracted_data.get("extracted_fields", {})
                
                # Federal income tax (all forms) FICA (Federal Insurance Contributions Act) tax withheld
                federal_tax = fields.get("federal_income_tax_withheld", {}).get("value")
                if not federal_tax:
                    federal_tax = fields.get("federal_tax_withheld", {}).get("value")  # 1042-S variation
                if federal_tax:
                    withholding_data["federal_income_tax"] += float(federal_tax.replace(",", "").replace("$", ""))
                
                # Social Security tax (W-2 only) - Check for FICA exemption
                ss_tax = fields.get("social_security_tax_withheld", {}).get("value")
                if ss_tax:
                    ss_amount = float(ss_tax.replace(",", "").replace("$", ""))
                    withholding_data["social_security_tax"] += ss_amount
                    
                    # If FICA exempt but SS tax was withheld, it's incorrect!
                    if withholding_data["fica_exempt"]:
                        withholding_data["incorrect_fica_withheld"] += ss_amount
                
                # Medicare tax (W-2 only) - Check for FICA exemption
                medicare_tax = fields.get("medicare_tax_withheld", {}).get("value")
                if medicare_tax:
                    medicare_amount = float(medicare_tax.replace(",", "").replace("$", ""))
                    withholding_data["medicare_tax"] += medicare_amount
                    
                    # If FICA exempt but Medicare tax was withheld, it's incorrect!
                    if withholding_data["fica_exempt"]:
                        withholding_data["incorrect_fica_withheld"] += medicare_amount
                
                # State income tax (1099-G mainly)
                state_tax = fields.get("state_income_tax_withheld", {}).get("value")
                if state_tax:
                    withholding_data["state_income_tax"] += float(state_tax.replace(",", "").replace("$", ""))
                
                # Foreign tax paid (1099-DIV)
                foreign_tax = fields.get("foreign_tax_paid", {}).get("value")
                if foreign_tax:
                    withholding_data["foreign_tax"] += float(foreign_tax.replace(",", "").replace("$", ""))
                
            except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"Failed to process withholding from document {doc.get('id')}: {str(e)}")
                continue
        
        # Flag if student can claim FICA refund
        if withholding_data["incorrect_fica_withheld"] > 0:
            withholding_data["fica_refund_eligible"] = True
        
        return withholding_data


async def get_chat_service():
    """Get chat service instance"""
    db = await get_database()
    return ChatService(db)
