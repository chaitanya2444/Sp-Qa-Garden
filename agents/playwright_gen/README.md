# QA Garden Test Automation Framework

Professional test automation framework for SnapPod AI web application using Playwright and Python.

## 🏗️ Architecture

```
src/
├── api/           # FastAPI service
├── config/        # Configuration management
├── core/          # Base classes and utilities
├── pages/         # Page object models
└── utils/         # Helper utilities

tests/
├── e2e/           # End-to-end tests
├── integration/   # Integration tests
└── unit/          # Unit tests

artifacts/
├── screenshots/   # Test screenshots
├── videos/        # Test recordings
├── logs/          # Test execution logs
└── traces/        # Playwright traces
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js (for Playwright browsers)

### Installation
```bash
# Clone repository
git clone <repository-url>
cd QA_GARDEN_UIUX

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Setup environment
cp .env.example .env
# Edit .env with your configuration
```

### Running Tests
```bash
# Run all tests
pytest tests/e2e/

# Run specific test suite
pytest tests/e2e/test_login.py

# Run with markers
pytest -m smoke
pytest -m "login and not slow"

# Generate HTML report
pytest --html=artifacts/reports/report.html
```

### API Service
```bash
# Start API server
python src/api/main.py

# Run tests via API
curl -X POST http://localhost:8000/tests/run/login

# Get artifacts
curl http://localhost:8000/artifacts/login
```

## 📋 Test Suites

### Login Tests (`test_login.py`)
- Page element visibility
- Valid/invalid credentials
- Form validation
- Password toggle
- Forgot password flow

### Signup Tests (`test_signup.py`)
- Registration form validation
- Required field checks
- Email format validation
- Password matching

### Welcome Tests (`test_welcome.py`)
- Authenticated page access
- Script generation
- Dropdown interactions
- Form submissions

## 🔧 Configuration

Environment variables in `.env`:
```bash
# Application URLs
BASE_URL=https://dev.vox.snappod.ai

# API Keys
GROQ_API_KEY=your_groq_key
JIRA_API_TOKEN=your_jira_token

# Test Configuration
BROWSER_HEADLESS=false
TEST_TIMEOUT=30000
```

## 📊 Artifacts

All test artifacts are organized by page type:
- **Screenshots**: Captured during test execution
- **Videos**: Full test recordings
- **Logs**: Detailed execution logs
- **Traces**: Playwright debug traces

## 🧪 Page Objects

Professional page object pattern with:
- Locator management
- Reusable methods
- Base page inheritance
- Type hints and documentation

## 📈 Reporting

- HTML reports with screenshots
- JSON test results
- Execution logs
- Performance metrics

## 🔍 Debugging

```bash
# Run with trace
pytest --tracing=on

# Debug mode
pytest --headed --slowmo=1000

# Specific test with debug
pytest tests/e2e/test_login.py::TestLogin::test_successful_login -s
```

## 🏷️ Test Markers

- `@pytest.mark.smoke` - Critical path tests
- `@pytest.mark.regression` - Full regression suite
- `@pytest.mark.login` - Login functionality
- `@pytest.mark.slow` - Long-running tests

## 📚 Documentation

Generate documentation:
```bash
mkdocs serve
```

## 🤝 Contributing

1. Follow PEP 8 style guide
2. Add type hints
3. Write docstrings
4. Include tests for new features
5. Update documentation