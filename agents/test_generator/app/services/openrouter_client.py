"""OpenRouter LLM client service."""
import httpx
import json
import re
from typing import Dict, Any
from app.core.config import settings
from app.core.logger import app_logger


class OpenRouterClient:
    """Client for interacting with OpenRouter API."""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = settings.request_timeout
    
    async def generate_test_cases(
        self, 
        requirements: Dict[str, Any], 
        prompt_template: str,
        requirements_json: str = None,
        input_context_label: str = "UI Locators & Elements JSON",
        input_context_data: str = ""
    ) -> Dict[str, Any]:
        """
        Generate test cases using OpenRouter API.
        
        Args:
            requirements: Software requirements as dictionary
            prompt_template: Prompt template string
            requirements_json: Deprecated: Pre-formatted JSON string (optional)
            input_context_label: Label for the input data (e.g., "UI Locators")
            input_context_data: The actual input data (JSON string or source code)
            
        Returns:
            Parsed JSON response from OpenRouter
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Construct the full prompt
            # Handle backward compatibility if input_context_data is empty but requirements_json is provided
            if not input_context_data and requirements_json:
                input_context_data = requirements_json
                
            # If still empty, try to convert requirements
            if not input_context_data and requirements:
                input_context_data = json.dumps(requirements, indent=2, ensure_ascii=False)
                
            # Use string replacement to avoid conflicts with JSON braces
            prompt = prompt_template.replace(
                "INPUT_CONTEXT_LABEL_PLACEHOLDER", input_context_label
            ).replace(
                "INPUT_CONTEXT_DATA_PLACEHOLDER", input_context_data
            )
            
            app_logger.info(f"Calling OpenRouter API with model: {self.model}")
            app_logger.debug(f"Prompt length: {len(prompt)} characters")
            
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com",  # Optional: for analytics
                "X-Title": "QA-Garden Test Case Generator"  # Optional: for analytics
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Lower temperature for more deterministic JSON output
                "max_tokens": 10000,  # Maximum tokens to generate
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload
                )
                
                app_logger.debug(f"OpenRouter API response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
                
                response_data = response.json()
                
                # Extract text from OpenRouter response
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})
                    text_response = message.get("content", "")
                    
                    if not text_response:
                        raise Exception("No content in OpenRouter response")
                    
                    # Try to parse as JSON
                    try:
                        json_response = json.loads(text_response.strip())
                        app_logger.info("Successfully generated test cases using OpenRouter")
                        return json_response
                    except json.JSONDecodeError:
                        # If response is not JSON, try to extract from markdown code blocks
                        # This is common - LLMs often wrap JSON in markdown code blocks
                        
                        # Try to extract JSON from markdown code blocks (more robust regex)
                        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text_response, re.DOTALL)
                        if json_match:
                            try:
                                json_response = json.loads(json_match.group(1).strip())
                                app_logger.debug("Extracted JSON from markdown code blocks")
                                app_logger.info("Successfully generated test cases using OpenRouter")
                                return json_response
                            except json.JSONDecodeError:
                                app_logger.warning("Failed to parse JSON even after extracting from markdown")
                        
                        # Fallback: Try to find JSON object in the response (even without code blocks)
                        json_object_match = re.search(r'\{[\s\S]*\}', text_response)
                        if json_object_match:
                            try:
                                json_response = json.loads(json_object_match.group(0))
                                app_logger.debug("Extracted JSON object from response")
                                app_logger.info("Successfully generated test cases using OpenRouter")
                                return json_response
                            except json.JSONDecodeError:
                                pass
                        
                        # If all extraction attempts failed
                        app_logger.warning("OpenRouter response is not valid JSON and could not be extracted")
                        return {"testCases": [{"raw_response": text_response}]}
                else:
                    raise Exception("No choices in OpenRouter response")
                    
        except httpx.TimeoutException:
            error_msg = "OpenRouter API request timeout"
            app_logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"OpenRouter API request error: {str(e)}"
            app_logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"OpenRouter API error: {str(e)}"
            app_logger.error(error_msg)
            raise Exception(error_msg)

