# Test Case Generator API

A production-ready FastAPI backend service that generates test cases and test data from software requirements using Large Language Models (LLMs).

## Features

- ✅ Accepts JSON file uploads containing software requirements
- ✅ Generates test cases using Gemini 2.5 Flash (primary) with OpenRouter as fallback
- ✅ Automatic fallback mechanism if primary LLM fails
- ✅ Production-ready error handling and logging
- ✅ CORS configuration for cross-origin requests
- ✅ Structured logging with loguru
- ✅ Pydantic models for request/response validation
- ✅ Modular, scalable architecture

## Project Structure

```
QA-Thota/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── routers/
│   │   └── testgen.py         # Test generation endpoints
│   ├── services/
│   │   ├── llm_orchestrator.py # LLM orchestration with fallback
│   │   ├── gemini_client.py    # Gemini API client
│   │   └── openrouter_client.py # OpenRouter API client (fallback)
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   ├── core/
│   │   ├── config.py           # Configuration settings
│   │   └── logger.py           # Logging configuration
│   └── utils/
│       └── file.py             # File utility functions
├── requirements.txt            # Python dependencies
├── start_server.bat            # Server startup script
├── sample_requirements.json    # Sample test file
├── .env.example                # Environment template
└── README.md                   # Documentation
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and add your API keys:
- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `OPENROUTER_API_KEY`: Your OpenRouter API key (optional, used as fallback)

### 3. Create Logs Directory (Optional)

The application will create a `logs/` directory automatically, but you can create it manually:

```bash
mkdir logs
```

## Running the Server

### 🚀 Quick Start

**Double-click `start_server.bat`** or run:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Manual Start

**Development Mode:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Or using Python:**
```bash
python app/main.py
```

**Production Mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

### Access the API

Once the server is running, open your browser and go to:
- **Swagger UI (Interactive):** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc
- **API Root:** http://localhost:8001

**To upload a file:**
1. Go to http://localhost:8001/docs
2. Find `/api/v1/generate-testcases`
3. Click "Try it out"
4. Click "Choose File" and select your JSON requirements file
5. Click "Execute"

## API Endpoints

### Generate Test Cases

**POST** `/api/v1/generate-testcases`

Upload a JSON file containing software requirements to generate test cases.

**Request:**
- Content-Type: `multipart/form-data`
- Body: JSON file upload

**Response:**
```json
{
  "testCases": [
    {
      "id": "TC001",
      "title": "Test case title",
      "steps": ["Step 1", "Step 2", "Step 3"],
      "expectedResult": "Expected result description",
      "testData": {}
    }
  ],
  "modelUsed": "gemini-2.5-flash",
  "success": true
}
```

### Health Check

**GET** `/api/v1/health`

Returns the health status of the service.

## Sample Request

### Using cURL

```bash
curl -X POST "http://localhost:8001/api/v1/generate-testcases" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@requirements.json"
```

### Using Python

```python
import requests

url = "http://localhost:8001/api/v1/generate-testcases"
files = {"file": open("requirements.json", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

### Sample Requirements JSON

```json
{
  "project": "E-commerce Platform",
  "requirements": [
    {
      "id": "REQ001",
      "description": "User should be able to login with email and password",
      "priority": "High"
    },
    {
      "id": "REQ002",
      "description": "User should be able to add items to shopping cart",
      "priority": "Medium"
    }
  ]
}
```

## Customizing the Prompt

The prompt template is located in `app/services/llm_orchestrator.py`. Look for the `PROMPT_TEMPLATE` variable:

```python
PROMPT_TEMPLATE = """
TODO: INSERT FINAL PROMPT HERE

Software Requirements:
{requirements_json}
...
"""
```

Replace the `TODO: INSERT FINAL PROMPT HERE` section with your custom prompt. The `{requirements_json}` placeholder will be automatically replaced with the uploaded requirements.

## Error Handling

The API includes comprehensive error handling:

- **400 Bad Request**: Invalid JSON format, wrong file type
- **500 Internal Server Error**: LLM API errors, processing errors

All errors return a structured JSON response:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "status_code": 400
}
```

## Logging

Logs are written to:
- **Console**: Structured logs with colors (DEBUG/INFO level)
- **File**: `logs/app_YYYY-MM-DD.log` (INFO level, rotated daily)

Log levels can be controlled via the `DEBUG` environment variable in `.env`.

## LLM Fallback Mechanism

1. **Primary**: Attempts to use Gemini 2.5 Flash (default: `gemini-2.5-flash`)
2. **Fallback**: If Gemini fails, automatically switches to OpenRouter (if configured)
3. **Error**: If both fail, returns an error response

All LLM interactions are logged for monitoring and debugging.

## Configuration

All configuration is managed through environment variables in `.env`:

- `GEMINI_API_KEY`: Gemini API key (required)
- `GEMINI_MODEL`: Gemini model name (default: `gemini-2.5-flash`)
- `OPENROUTER_API_KEY`: OpenRouter API key (optional, used as fallback)
- `OPENROUTER_MODEL`: OpenRouter model name (default: `meta-llama/llama-3-8b-instruct`)
- `DEBUG`: Enable debug mode (default: `False`)
- `CORS_ORIGINS`: Allowed CORS origins (default: `["*"]`)
- `REQUEST_TIMEOUT`: Request timeout in seconds (default: `600`)

## Development

### Code Structure

- **Routers**: Handle HTTP requests and responses
- **Services**: Business logic and LLM integration
- **Models**: Pydantic schemas for validation
- **Core**: Configuration and logging
- **Utils**: Utility functions

### Adding New Features

1. Add new endpoints in `app/routers/`
2. Add business logic in `app/services/`
3. Define schemas in `app/models/schemas.py`
4. Update configuration in `app/core/config.py` if needed

## License

This project is provided as-is for production use.

## Support

For issues or questions, please check the logs in the `logs/` directory or review the API documentation at `/docs`.

