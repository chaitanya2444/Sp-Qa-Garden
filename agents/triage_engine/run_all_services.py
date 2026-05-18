import subprocess
import time
import os
import sys

def start_service(name, command, cwd="."):
    print(f"Starting {name}...")
    # Use the venv python if available
    venv_python = os.path.join("venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = "python"
        
    cmd = [venv_python] + command
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )

def main():
    services = []
    
    print("=" * 80)
    print("Triage Engine - Service Orchestrator")
    print("=" * 80)
    print()
    
    try:
        # 1. Start BERT Server
        services.append(start_service("BERT Server", ["bert_server.py"]))
        
        # 2. Start Script Server
        services.append(start_service("Script Server", ["playwright_script_server.py"]))
        
        # Give them a moment to initialize
        print("Waiting for auxiliary services to initialize...")
        time.sleep(5)
        
        # 3. Start Main Triage Engine
        services.append(start_service("Triage Engine", ["main.py"]))
        
        print("\n" + "=" * 80)
        print("All services are starting in separate windows.")
        print("You can now run tests using: python run_all_tests.py")
        print("Press Ctrl+C in this window to stop all services (if running in same console).")
        print("=" * 80)
        
        # Keep the main script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping services...")
        for s in services:
            s.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
