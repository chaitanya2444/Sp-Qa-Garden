import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Playwright Script Server", version="1.0.0")

# Configure CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for script server (read-only)
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# Configuration
# derivation of base directory to ensure robustness
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.getenv("SCRIPTS_DIR", BASE_DIR)
PORT = int(os.getenv("SCRIPT_SERVER_PORT", 8005))
HOST = os.getenv("SCRIPT_SERVER_HOST", "0.0.0.0")

class ScriptInfo(BaseModel):
    """Response model for script information"""
    script_name: str
    script_path: str
    file_size: int
    exists: bool
    endpoint_url: str
    download_url: str

class ScriptContent(BaseModel):
    """Response model for script content"""
    script_name: str
    content: str
    file_size: int
    lines: int


@app.get("/")
def root():
    """API root endpoint"""
    return {
        "service": "Playwright Script Server",
        "version": "1.0.0",
        "endpoints": {
            "list_scripts": "/api/scripts",
            "get_script_info": "/api/scripts/{filename}",
            "get_script_content": "/api/scripts/{filename}/content",
            "download_script": "/api/scripts/{filename}/download"
        }
    }


@app.get("/api/scripts")
def list_scripts():
    """List all available Playwright test scripts"""
    scripts = []
    
    # Find all .spec.js files in script directory
    for file in Path(SCRIPTS_DIR).glob("*.spec.js"):
        scripts.append({
            "name": file.name,
            "size": file.stat().st_size,
            "endpoint": f"http://localhost:{PORT}/api/scripts/{file.name}"
        })
    
    return {
        "total": len(scripts),
        "scripts": scripts
    }


@app.get("/api/scripts/{filename}", response_model=ScriptInfo)
def get_script_info(filename: str):
    """Get information about a specific script"""
    # Security: Only allow .spec.js files
    if not filename.endswith('.spec.js'):
        raise HTTPException(status_code=400, detail="Only .spec.js files are allowed")
    
    script_path = os.path.join(SCRIPTS_DIR, filename)
    
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail=f"Script '{filename}' not found")
    
    file_size = os.path.getsize(script_path)
    
    return ScriptInfo(
        script_name=filename,
        script_path=script_path,
        file_size=file_size,
        exists=True,
        endpoint_url=f"http://localhost:{PORT}/api/scripts/{filename}",
        download_url=f"http://localhost:{PORT}/api/scripts/{filename}/download"
    )


@app.get("/api/scripts/{filename}/content", response_model=ScriptContent)
def get_script_content(filename: str):
    """Get the actual content of a script"""
    # Security: Only allow .spec.js files
    if not filename.endswith('.spec.js'):
        raise HTTPException(status_code=400, detail="Only .spec.js files are allowed")
    
    script_path = os.path.join(SCRIPTS_DIR, filename)
    
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail=f"Script '{filename}' not found")
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = len(content.splitlines())
        file_size = os.path.getsize(script_path)
        
        return ScriptContent(
            script_name=filename,
            content=content,
            file_size=file_size,
            lines=lines
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading script: {str(e)}")


@app.get("/api/scripts/{filename}/download")
def download_script(filename: str):
    """Download a script file"""
    # Security: Only allow .spec.js files
    if not filename.endswith('.spec.js'):
        raise HTTPException(status_code=400, detail="Only .spec.js files are allowed")
    
    script_path = os.path.join(SCRIPTS_DIR, filename)
    
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail=f"Script '{filename}' not found")
    
    return FileResponse(
        path=script_path,
        media_type='application/javascript',
        filename=filename
    )


if __name__ == "__main__":
    print("=" * 80)
    print("Playwright Script Server")
    print("=" * 80)
    print(f"Starting server on http://localhost:{PORT}")
    print(f"Serving scripts from: {SCRIPTS_DIR}")
    print()
    
    uvicorn.run(app, host=HOST, port=PORT)

