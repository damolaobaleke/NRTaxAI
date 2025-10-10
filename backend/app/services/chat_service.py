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
                                "description": "Visa classification (e.g., H1B, F-1, J-1)"
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
                        "required": ["visa_type", "days_current_year"]
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
                        "required": ["country_code", "visa_type"]
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
            logger.info("Processing chat message", 
                       session_id=session_id,
                       user_id=user_id)
            
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
        """Get chat history for session"""
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
        """Store message in database"""
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
            "self_employment": 0,
            "us_work_days": 0,
            "total_work_days": 0
        }
        
        for doc in documents:
            if not doc.get("extracted_json"):
                continue
            
            try:
                extracted_data = json.loads(doc["extracted_json"])
                fields = extracted_data.get("extracted_fields", {})
                
                if doc["doc_type"] == "W2":
                    wages = fields.get("wages", {}).get("value")
                    if wages:
                        income_data["wages"] += float(wages.replace(",", "").replace("$", ""))
                
                elif doc["doc_type"] == "1099INT":
                    interest = fields.get("interest_income", {}).get("value")
                    if interest:
                        income_data["interest"] += float(interest.replace(",", "").replace("$", ""))
                
                elif doc["doc_type"] == "1099NEC":
                    comp = fields.get("nonemployee_compensation", {}).get("value")
                    if comp:
                        income_data["self_employment"] += float(comp.replace(",", "").replace("$", ""))
                
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        return income_data
    
    async def _aggregate_withholding_from_documents(self, documents: list) -> Dict[str, Any]:
        """Aggregate withholding from extracted documents"""
        withholding_data = {
            "federal_income_tax": 0,
            "social_security_tax": 0,
            "medicare_tax": 0
        }
        
        for doc in documents:
            if not doc.get("extracted_json"):
                continue
            
            try:
                extracted_data = json.loads(doc["extracted_json"])
                fields = extracted_data.get("extracted_fields", {})
                
                federal_tax = fields.get("federal_income_tax_withheld", {}).get("value")
                if federal_tax:
                    withholding_data["federal_income_tax"] += float(federal_tax.replace(",", "").replace("$", ""))
                
                ss_tax = fields.get("social_security_tax_withheld", {}).get("value")
                if ss_tax:
                    withholding_data["social_security_tax"] += float(ss_tax.replace(",", "").replace("$", ""))
                
                medicare_tax = fields.get("medicare_tax_withheld", {}).get("value")
                if medicare_tax:
                    withholding_data["medicare_tax"] += float(medicare_tax.replace(",", "").replace("$", ""))
                
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        return withholding_data


async def get_chat_service():
    """Get chat service instance"""
    db = await get_database()
    return ChatService(db)
