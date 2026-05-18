# Bug Triage Engine - Knowledge Transfer (KT)

## 📋 What This System Does

**Automatically converts Playwright test failures into professional bug reports using AI**

**Input:** Failed test  
**Output:** Complete bug report with title, description, error location, and category label

**Time Saved:** 10-15 minutes → 30 seconds per bug

---

## 🏗️ System Components

### **1. Triage Engine (Port 8003)**
- Main service that coordinates everything
- Receives test failures and returns bug reports

### **2. BERT Server (Port 8001)**
- Real machine-learning server for error classification
- Automatically categorizes failures (e.g., "Timed Out", "Assertion Mismatch")
- Uses `distilbart-mnli-12-1` for intelligent classification

### **3. Playwright Script Server (Port 8005)**
- Serves the source code of failing tests via HTTP
- Enables "Deep Linking" directly to the failing line in the dashboard

### **4. Ollama LLM (Port 11434)**
- Generates human-readable bug descriptions (Gemma:2b)

---

## ⚙️ Configuration (Dashbaord Ready)

The system is fully environment-driven via the **`.env`** file.

### **Key Environment Variables**
| Variable | Description | Default |
|----------|-------------|---------|
| `TRIAGE_ENGINE_PORT` | Main backend port | 8003 |
| `BERT_SERVER_PORT` | BERT classification port | 8001 |
| `SCRIPT_SERVER_PORT` | Code script server port | 8005 |
| `CORS_ORIGINS` | Dashboard URLs (comma separated) | `http://localhost:3000` |

---

## 🚀 How to Start (One-Click)

To start the entire intelligent ecosystem at once:
```powershell
python run_all_services.py
```
This single command launches the Triage Engine, BERT Server, and Script Server in separate windows.

**Running Tests & Triaging:**
```powershell
python run_all_tests.py
```

---

## 🧩 Dashboard Integration

To connect this to your **QA Garden Dashboard**:
1. Open your dashboard's `.env.local` file.
2. Set `NEXT_PUBLIC_TRIAGE_ENGINE_URL=http://localhost:8003`.
3. Start the triage services using `python run_all_services.py`.
4. Run your tests. The dashboard will now automatically receive and display AI-triaged reports.

---

## 📁 Important Files & Directories

- `.env` - Centralized configuration
- `run_all_services.py` - Single-entry service orchestrator
- `main.py` - Core API logic
- `bert_server.py` - Intelligent classification server
- `playwright_script_server.py` - Deep-linking source server
- `processed/` - Directory where triaged JSON reports are stored

---

## 🔑 Key Features
- **Intelligent deep-linking**: Click a link in the dashboard to jump to the exact line of code in the test.
- **AI Classification**: BERT models identify if a bug is a real failure or just a network fluke.
- **Narrative Generation**: Ollama writes professional bug reports so you don't have to.

**Project Owner:** Tulasiram01  
**Last Updated:** 2026-02-01 (Integration Ready)
