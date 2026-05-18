import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Groq
api_key = os.getenv("GROQ_API_KEY")
client = None
if api_key:
    client = Groq(api_key=api_key)

def generate_bug_report_with_groq(failure_text: str) -> dict:
    """
    Generate a high-quality bug report using Groq AI (Llama3/Mixtral).
    """
    if not client:
        return {
            "title": "Groq API Error",
            "description": "GROQ_API_KEY not configured in .env file."
        }

    try:
        model_name = "llama-3.3-70b-versatile" # Updated to supported model
        print(f"Using Groq model: {model_name}")
        
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
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates bug reports."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=model_name,
            temperature=0.2, # Low temperature for more deterministic/factual output
            max_tokens=1024,
        )

        text = chat_completion.choices[0].message.content
        
        # Parse title and description
        title = "Automated Test Failure"
        description = text
        
        if "TITLE:" in text and "DESCRIPTION:" in text:
            parts = text.split("DESCRIPTION:", 1)
            title_part = parts[0].replace("TITLE:", "").strip()
            description = parts[1].strip()
            # Clean up title if it has extra newlines or markers
            title = title_part.split('\n')[0].strip()
            
        return {
            "title": title,
            "description": description
        }

    except Exception as e:
        print(f"Groq generation error: {str(e)}")
        # Raise exception so the caller can handle fallback
        raise e
