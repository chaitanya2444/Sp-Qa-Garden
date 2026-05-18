import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def generate_bug_report_with_gemini(failure_text: str) -> dict:
    """
    Generate a high-quality bug report using Google Gemini AI.
    """
    if not api_key:
        return {
            "title": "Gemini API Error",
            "description": "Gemini API key not configured in .env file."
        }

    try:

        # Use model from environment if provided, otherwise dynamic selection
        env_model = os.getenv("GEMINI_MODEL")
        if env_model:
            # Add 'models/' prefix if missing
            if not env_model.startswith('models/'):
                model_name = f"models/{env_model}"
            else:
                model_name = env_model
            logger.info(f"Using Gemini model from env: {model_name}")
        else:
            # Dynamic model selection - find the first available generative model
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # Prioritize 2.0 flash, then 1.5 flash, then any flash
            model_name = 'models/gemini-2.0-flash'
            if model_name not in available_models:
                flash_models = [m for m in available_models if 'flash' in m]
                if flash_models:
                    model_name = flash_models[0]
                else:
                    model_name = available_models[0] if available_models else 'models/gemini-pro'
            
            logger.info(f"Using dynamically selected Gemini model: {model_name}")
        
        model = genai.GenerativeModel(model_name)


        
        prompt = f"""
You are an elite Senior QA Automation Engineer and Bug Triage Specialist.

Read the FAILED TEST DETAILS below and synthesize a high-quality, professional bug report.
The report should be structured for a development team to immediately understand the root cause.

STRICT REQUIREMENTS:
1. TITLE: A concise, impactful title (max 80 characters).
2. DESCRIPTION: A detailed, narrative explanation (160-220 words).
3. Do NOT repeat raw stack traces or log dumps verbatim.
4. Use professional language.
5. Identify Expected vs Actual behavior clearly.
6. Suggest a likely root cause (UI, API, Data, or Infrastructure).

FAILED TEST DETAILS:
{failure_text}

Provide the output in the following format:
TITLE: [Your Title Here]
DESCRIPTION: [Your Detailed Description Here]
"""
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Parse title and description
        title = "Automated Test Failure"
        description = text
        
        if "TITLE:" in text and "DESCRIPTION:" in text:
            parts = text.split("DESCRIPTION:", 1)
            title_part = parts[0].replace("TITLE:", "").strip()
            description = parts[1].strip()
            title = title_part
            
        return {
            "title": title,
            "description": description
        }

    except Exception as e:
        print(f"Gemini generation error: {str(e)}")
        raise e
