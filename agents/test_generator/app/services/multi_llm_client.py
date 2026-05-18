"""LLM client service with Multi-Provider Fallback (OpenRouter -> Hugging Face)."""
import httpx
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logger import app_logger

class LLMClient:
    """Generic LLM Client supporting OpenRouter and Hugging Face fallback."""
    
    def __init__(self):
        self.gemini_key = settings.gemini_api_key
        self.gemini_model = settings.gemini_model
        
        self.xai_key = settings.xai_api_key
        self.xai_model = settings.xai_model
        
        self.groq_keys = settings.groq_api_keys_list
        app_logger.info(f"LLMClient initialized with {len(self.groq_keys)} Groq keys.")
        self.groq_current_key_index = 0
        self.groq_model = settings.groq_model
        
        self.or_key = settings.openrouter_api_key
        self.or_model = settings.openrouter_model
        
        self.hf_key = settings.effective_hf_key  # Picks up HF_TOKEN auto-injected by HF Spaces
        self.hf_model = settings.huggingface_model
        
        self.ollama_url = settings.ollama_base_url
        self.ollama_model = settings.ollama_model
        
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
        Generate test cases using priority fallback: Gemini -> Groq -> OpenRouter -> Ollama -> Hugging Face.
        """
        # Prepare Context
        if not input_context_data and requirements_json:
            input_context_data = requirements_json
        if not input_context_data and requirements:
            input_context_data = json.dumps(requirements, indent=2, ensure_ascii=False)
            
        full_prompt = prompt_template.replace(
            "INPUT_CONTEXT_LABEL_PLACEHOLDER", input_context_label
        ).replace(
            "INPUT_CONTEXT_DATA_PLACEHOLDER", input_context_data
        )

        # 1. Try Gemini (Primary per user request)
        if self.gemini_key:
            try:
                return await self._call_gemini(full_prompt)
            except Exception as e:
                app_logger.warning(f"Gemini failed: {e}. Attempting next fallback (Groq)...")

        # 2. Try Grok (xAI) - Keeping as secondary
        if self.xai_key and "your_" not in self.xai_key:
            try:
                return await self._call_xai(full_prompt)
            except Exception as e:
                app_logger.warning(f"Grok (xAI) failed: {e}. Attempting next fallback...")

        # 2. Try Groq (High Speed with Key Rotation)
        if self.groq_keys:
            for i in range(len(self.groq_keys)):
                # Use round-robin to start with a fresh key next time
                idx = (self.groq_current_key_index + i) % len(self.groq_keys)
                key = self.groq_keys[idx]
                try:
                    result = await self._call_groq(full_prompt, key)
                    # Success! Advance the index for next time
                    self.groq_current_key_index = (idx + 1) % len(self.groq_keys)
                    return result
                except Exception as e:
                    if "429" in str(e):
                        app_logger.warning(f"Groq key {idx+1}/{len(self.groq_keys)} rate limited (429).")
                        if i < len(self.groq_keys) - 1:
                            app_logger.info("Rotating to next Groq key...")
                            import asyncio
                            await asyncio.sleep(1.5)
                            continue
                    app_logger.warning(f"Groq failed: {e}. Attempting next fallback...")
                    break

        # 4. Try Ollama (Local) — only if URL is configured and not empty
        if self.ollama_url:
            try:
                return await self._call_ollama(full_prompt)
            except Exception as e:
                app_logger.warning(f"Ollama failed: {e}. Attempting final fallback...")

        # 5. Try Hugging Face (Final Fallback)
        if self.hf_key:
            try:
                return await self._call_huggingface(full_prompt)
            except Exception as e:
                app_logger.error(f"Hugging Face failed: {e}")
        
        # 6. Zero-Key Dummy Fallback (Think Out of the Box!)
        # If the user has provided absolutely zero API keys, we MUST not crash. 
        # We return a dummy test case so the pipeline continues gracefully.
        app_logger.warning("No API keys configured or all providers failed. Using Zero-Key Dummy Fallback!")
        return {
            "testCases": [
                {
                    "id": "TC-DUMMY-01",
                    "title": "Verify basic page load (Auto-Generated Dummy)",
                    "description": "Dummy test case generated because no LLM API keys were provided.",
                    "steps": ["Navigate to the page", "Verify the page title exists"],
                    "expectedResults": ["Page loads successfully"]
                }
            ]
        }

    async def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Call Google Gemini API."""
        app_logger.info(f"Calling Gemini with model: {self.gemini_model}")
        
        import google.generativeai as genai
        genai.configure(api_key=self.gemini_key)
        model = genai.GenerativeModel(self.gemini_model)
        
        # Consistent system instruction via prepending/wrapping if needed, 
        # but let's just use simple generate_content.
        response = await asyncio.to_thread(model.generate_content, prompt)
        return self._parse_json(response.text)

    async def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call local Ollama API."""
        app_logger.info(f"Calling Ollama with model: {self.ollama_model}")
        
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.ollama_url, json=payload)
            response.raise_for_status()
            data = response.json()
            return self._parse_json(data.get("response", ""))

    async def _call_xai(self, prompt: str) -> Dict[str, Any]:
        """Call xAI (Grok) API (OpenAI compatible)."""
        app_logger.info(f"Calling Grok (xAI) with model: {self.xai_model}")
        
        url = f"{settings.xai_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.xai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.xai_model,
            "messages": [
                {"role": "system", "content": "You are an expert QA automation engineer. Respond ONLY in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            return self._parse_json(content)

    async def _call_groq(self, prompt: str, api_key: str = None) -> Dict[str, Any]:
        """Call Groq API (OpenAI compatible)."""
        app_logger.info(f"Calling Groq with model: {self.groq_model}")
        
        url = f"{settings.groq_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key or self.groq_keys[0]}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": "You are an expert QA automation engineer. Respond ONLY in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            return self._parse_json(content)

    async def _call_openrouter(self, prompt: str) -> Dict[str, Any]:
        """Call OpenRouter API (OpenAI compatible)."""
        app_logger.info(f"Calling OpenRouter with model: {self.or_model}")
        
        url = f"{settings.openrouter_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.or_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://qa-garden.com", # Required by OpenRouter
            "X-Title": "QA Garden"
        }
        payload = {
            "model": self.or_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"} # Force JSON mode
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            return self._parse_json(content)

    async def _call_huggingface(self, prompt: str) -> Dict[str, Any]:
        """Call Hugging Face Inference API via Router."""
        app_logger.info(f"Calling Hugging Face with model: {self.hf_model}")
        
        hf_url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
        headers = {"Authorization": f"Bearer {self.hf_key}"}
        
        # Payload for the Hugging Face Router
        payload = {
            "model": self.hf_model,
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 4096,
                "temperature": 0.1,
                "return_full_text": False
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(hf_url, headers=headers, json=payload)
            if response.status_code != 200:
                app_logger.error(f"Hugging Face API Error {response.status_code}: {response.text}")
            response.raise_for_status()
            result = response.json()
            
            # Router typically returns list of dicts
            if isinstance(result, list) and len(result) > 0:
                content = result[0].get('generated_text', '')
                return self._parse_json(content)
            elif isinstance(result, dict) and 'generated_text' in result:
                return self._parse_json(result['generated_text'])
            else:
                raise Exception(f"Unexpected response format from HF: {result}")

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Robust JSON parsing helper."""
        import re
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Extract JSON block
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            # Try raw brace search
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group(0))
            raise
