# Ultimate Smart Crawler - Production Ready

A robust, intelligent web crawler designed to extract comprehensive UI locators, handle complex authentication flows, and prevent infinite loops in dynamic web applications.

## Features

- **Deep Extraction**: Uses graph traversal and smart fallback mechanisms to find elements deep within the application.
- **Smart Stuck Prevention**: Detects and escapes infinite loops and "trap" pages (e.g., payment forms, infinite scrolls).
- **Sequential Flow Support**: Can follow strict user workflows (Dashboard -> Profile -> Settings).
- **Clean Output**: Generates hierarchical, deduplicated, and semantically named locators in JSON and CSV formats.
- **Production Ready**: Modular structure with type hinting and error handling.

## specific requirements
- **Python**: 3.8+
- **Playwright**: Installed and strictly configured

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Browsers**:
    ```bash
    playwright install chromium
    ```

3.  **Environment Configuration**:
    Create a `.env` file in the root directory (optional, can pass args via CLI):
    ```env
    LOGIN_EMAIL=your_email@example.com
    LOGIN_PASSWORD=your_password
    ```

## Usage

Run the crawler using the `main.py` entry point:

```bash
# Basic run (defaults to configured URL)
python main.py

# Specify URL
python main.py https://example.com

# Headless mode
python main.py --headless

# With credentials
python main.py --email user@test.com --password secret
```

## Output

Results are saved in the `locators/` directory:
- `all_locators.py`: Python dictionary format.
- `all_locators.json`: JSON format.
- `all_locators.csv`: Flat CSV format.
- `quality_report.txt`: Extraction metrics.
