import subprocess
import os

print("Running pytest tests/page_1/test_page_1.py...")
result = subprocess.run(['pytest', 'tests/page_1/test_page_1.py', '-v', '--tb=long'], capture_output=True)
print("STDOUT:")
print(result.stdout.decode('utf-8', errors='replace'))
print("STDERR:")
print(result.stderr.decode('utf-8', errors='replace'))
print(f"Exit Code: {result.returncode}")
