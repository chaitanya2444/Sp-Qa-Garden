"""
View Triage Results
Simple script to view triaged test results from the bug triage engine
"""
import requests
import json
from datetime import datetime

# Configuration
API_URL = "http://localhost:8003/api/triage"

def view_latest():
    """View the latest triage result"""
    print("=" * 80)
    print("LATEST TRIAGE RESULT")
    print("=" * 80)
    print()
    
    try:
        response = requests.get(f"{API_URL}/latest", timeout=10)
        response.raise_for_status()
        result = response.json()
        
        print_result(result)
        
        print()
        print("=" * 80)
        print("TIP: To view all results, run:")
        print("  python view_results.py all")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print(f"✗ ERROR: Cannot connect to {API_URL}")
        print("  Make sure the triage engine is running: python main.py")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("✗ No results found. Run some tests first:")
            print("  python demo_playwright_failures.py")
        else:
            print(f"✗ ERROR: {e}")
    except Exception as e:
        print(f"✗ ERROR: {e}")

def view_all():
    """View all triage results"""
    print("=" * 80)
    print("ALL TRIAGE RESULTS")
    print("=" * 80)
    print()
    
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        total = data.get('total', 0)
        
        print(f"Total Results: {total}")
        print()
        
        if not results:
            print("No results found. Run some tests first:")
            print("  python demo_playwright_failures.py")
            return
        
        for i, result in enumerate(results, 1):
            print(f"[{i}/{total}]")
            print("-" * 80)
            print_result(result, compact=True)
            print()
        
    except requests.exceptions.ConnectionError:
        print(f"✗ ERROR: Cannot connect to {API_URL}")
        print("  Make sure the triage engine is running: python main.py")
    except Exception as e:
        print(f"✗ ERROR: {e}")

def print_result(result, compact=False):
    """Print a single triage result"""
    print(f"ID: {result.get('id', 'N/A')}")
    print(f"Created: {result.get('created_at', 'N/A')}")
    print()
    print(f"Title: {result.get('title', 'N/A')}")
    print()
    
    if not compact:
        print(f"Description:")
        print(f"  {result.get('description', 'N/A')}")
        print()
    
    print(f"Status: {result.get('status', 'N/A')}")
    print(f"Error Line: {result.get('error_line', 'N/A')}")
    
    if result.get('triage_label'):
        print(f"Triage Label: {result['triage_label']}")
    
    print()
    
    if result.get('playwright_script'):
        print(f"Playwright Script: {result['playwright_script']}")
    
    if result.get('test_url'):
        print(f"Test URL: {result['test_url']}")
    
    if result.get('playwright_script_endpoint'):
        print(f"Script Endpoint: {result['playwright_script_endpoint']}")
    
    if not compact and result.get('stack_trace'):
        print()
        print("Stack Trace:")
        print("-" * 40)
        print(result['stack_trace'][:500])  # First 500 chars
        if len(result['stack_trace']) > 500:
            print("... (truncated)")

def main():
    """Main menu"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "latest":
            view_latest()
        elif sys.argv[1] == "all":
            view_all()
        else:
            print("Usage:")
            print("  python view_results.py          # View latest result (default)")
            print("  python view_results.py latest   # View latest result")
            print("  python view_results.py all      # View all results")
            print()
            print("Examples:")
            print("  python view_results.py          → Shows most recent triage")
            print("  python view_results.py all      → Shows all triaged failures")
    else:
        view_latest()

if __name__ == "__main__":
    main()
