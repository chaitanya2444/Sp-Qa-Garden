"""
Persistent JSON storage service for triage results.
Results are stored in a JSON file to survive restarts.
"""
import uuid
import json
import os
import threading
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# File path for persistence
DB_FILE = Path("triage_db.json")
RUNS_FILE = Path("triage_runs.json")
_lock = threading.Lock()

def _load_db() -> Dict[str, dict]:
    """Load database from file safely."""
    with _lock:
        if not DB_FILE.exists():
            return {}
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

def _save_db(data: Dict[str, dict]):
    """Save database to file safely."""
    with _lock:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving triage DB: {e}")

# Initial load
_storage: Dict[str, dict] = _load_db()

def store_result(result: dict) -> str:
    """
    Store a triage result and return its unique ID.
    Persists to JSON file.
    """
    # Refresh storage from disk in case of external edits (simple concurrency)
    global _storage
    _storage = _load_db()
    
    result_id = str(uuid.uuid4())
    
    # Add metadata
    result_with_metadata = {
        **result,
        "id": result_id,
        "created_at": datetime.now().isoformat()
    }
    
    _storage[result_id] = result_with_metadata
    _save_db(_storage)
    return result_id


def get_result(result_id: str) -> Optional[dict]:
    """Retrieves a result by ID."""
    global _storage
    _storage = _load_db() # Reload to get latest
    return _storage.get(result_id)


def get_all_results() -> List[dict]:
    """Retrieves all results sorted by date."""
    global _storage
    _storage = _load_db()
    results = list(_storage.values())
    # Sort by created_at timestamp, newest first
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results


def get_latest_result() -> Optional[dict]:
    """Retrieves the most recent result."""
    results = get_all_results()
    return results[0] if results else None


def delete_result(result_id: str) -> bool:
    """Deletes a result by ID."""
    global _storage
    _storage = _load_db()
    
    if result_id in _storage:
        del _storage[result_id]
        _save_db(_storage)
        return True
    return False


def get_result_count() -> int:
    """Get the total number of stored results."""
    global _storage
    _storage = _load_db()
    return len(_storage)

def get_results_by_run_id(run_id: str) -> List[dict]:
    """Get all results for a specific run ID."""
    db = _load_db()
    return [res for res in db.values() if res.get("run_id") == run_id]

def mark_run_completed(run_id: str):
    """Mark a run as completed in a separate state file."""
    with _lock:
        state = {}
        if RUNS_FILE.exists():
            try:
                with open(RUNS_FILE, 'r') as f:
                    state = json.load(f)
            except: pass
        
        state[run_id] = {
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
        
        with open(RUNS_FILE, 'w') as f:
            json.dump(state, f, indent=2)

def is_run_completed(run_id: str) -> bool:
    """Check if a run has been marked as completed."""
    if not RUNS_FILE.exists():
        return False
    try:
        with open(RUNS_FILE, 'r') as f:
            state = json.load(f)
            return run_id in state
    except:
        return False
