"""File utility functions."""
import json
import csv
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import UploadFile
from app.core.logger import app_logger


async def parse_json_file(file: UploadFile) -> Dict[str, Any]:
    """
    Parse JSON content from uploaded file.
    
    Args:
        file: Uploaded file object
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        ValueError: If file is not valid JSON
        Exception: For other file reading errors
    """
    try:
        content = await file.read()
        app_logger.debug(f"Read {len(content)} bytes from uploaded file: {file.filename}")
        
        # Decode bytes to string
        text_content = content.decode('utf-8')
        
        # Parse JSON
        json_data = json.loads(text_content)
        app_logger.info(f"Successfully parsed JSON file: {file.filename}")
        
        return json_data
        
    except json.JSONDecodeError as e:
        app_logger.error(f"JSON decode error in file {file.filename}: {str(e)}")
        raise ValueError(f"Invalid JSON format: {str(e)}")
    except UnicodeDecodeError as e:
        app_logger.error(f"Unicode decode error in file {file.filename}: {str(e)}")
        raise ValueError(f"File encoding error: {str(e)}")
    except Exception as e:
        app_logger.error(f"Error reading file {file.filename}: {str(e)}")
        raise Exception(f"Error processing file: {str(e)}")


async def parse_python_file(file: UploadFile) -> str:
    """
    Parse Python content from uploaded file.
    
    Args:
        file: Uploaded file object
        
    Returns:
        Python code content as string
        
    Raises:
        ValueError: If file encoding is invalid
        Exception: For other file reading errors
    """
    try:
        content = await file.read()
        app_logger.debug(f"Read {len(content)} bytes from uploaded file: {file.filename}")
        
        # Decode bytes to string
        text_content = content.decode('utf-8')
        app_logger.info(f"Successfully parsed Python file: {file.filename}")
        
        return text_content
        
    except UnicodeDecodeError as e:
        app_logger.error(f"Unicode decode error in file {file.filename}: {str(e)}")
        raise ValueError(f"File encoding error: {str(e)}")
    except Exception as e:
        app_logger.error(f"Error reading file {file.filename}: {str(e)}")
        raise Exception(f"Error processing file: {str(e)}")


def save_test_cases_to_file(
    test_cases: Dict[str, Any],
    output_dir: str = "output",
    filename: Optional[str] = None
) -> str:
    """
    Save generated test cases to a JSON file.
    
    Args:
        test_cases: Test cases data dictionary
        output_dir: Directory to save the file (default: "output")
        filename: Optional custom filename. If not provided, generates timestamp-based name
        
    Returns:
        Path to the saved file
        
    Raises:
        Exception: If file saving fails
    """
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            app_logger.info(f"Created output directory: {output_dir}")
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"testcases_{timestamp}.json"
        
        # Ensure filename ends with .json
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        file_path = os.path.join(output_dir, filename)
        
        # Save test cases to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(test_cases, f, indent=2, ensure_ascii=False)
        
        app_logger.info(f"Test cases saved to: {file_path}")
        return file_path
        
    except Exception as e:
        app_logger.error(f"Error saving test cases to file: {str(e)}")
        raise Exception(f"Error saving test cases: {str(e)}")


def get_latest_test_cases_count(output_dir: str = "output") -> Dict[str, Any]:
    """
    Get statistics about the most recently generated test cases.
    
    Args:
        output_dir: Directory containing generated test case files (default: "output")
        
    Returns:
        Dictionary with latest generation info:
        - testCaseCount: Number of test cases in the latest generation
        - filename: Name of the latest file
        - generatedAt: When it was generated
        - modelUsed: Model that was used
    """
    try:
        if not os.path.exists(output_dir):
            return {
                "testCaseCount": 0,
                "filename": None,
                "generatedAt": None,
                "modelUsed": None
            }
        
        latest_file = None
        latest_timestamp = None
        
        # Get all JSON files in output directory
        for filename in os.listdir(output_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(output_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Get test case count
                    test_cases = data.get("testCases", [])
                    count = len(test_cases) if isinstance(test_cases, list) else 0
                    
                    # Get metadata
                    generated_at = data.get("generatedAt", "")
                    model_used = data.get("modelUsed", "unknown")
                    
                    # Track latest file
                    if generated_at and (latest_timestamp is None or generated_at > latest_timestamp):
                        latest_timestamp = generated_at
                        latest_file = {
                            "testCaseCount": count,
                            "filename": filename,
                            "generatedAt": generated_at,
                            "modelUsed": model_used
                        }
                        
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    app_logger.warning(f"Error reading file {filename}: {str(e)}")
                    continue
        
        if latest_file is None:
            return {
                "testCaseCount": 0,
                "filename": None,
                "generatedAt": None,
                "modelUsed": None
            }
        
        return latest_file
        
    except Exception as e:
        app_logger.error(f"Error getting latest test cases count: {str(e)}")
        raise Exception(f"Error getting statistics: {str(e)}")


def get_latest_test_cases(output_dir: str = "output") -> Dict[str, Any]:
    """
    Get the full test cases data from the most recently generated file.
    
    Args:
        output_dir: Directory containing generated test case files (default: "output")
        
    Returns:
        Dictionary with full test cases data:
        - testCases: List of test cases
        - totalTestCases: Number of test cases
        - generatedAt: When it was generated
        - modelUsed: Model that was used
        - filename: Name of the file
    """
    try:
        if not os.path.exists(output_dir):
            raise Exception("No test cases found. Output directory does not exist.")
        
        latest_file = None
        latest_timestamp = None
        latest_file_path = None
        
        # Get all JSON files in output directory
        for filename in os.listdir(output_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(output_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Get metadata
                    generated_at = data.get("generatedAt", "")
                    
                    # Track latest file
                    if generated_at and (latest_timestamp is None or generated_at > latest_timestamp):
                        latest_timestamp = generated_at
                        latest_file = data
                        latest_file_path = filename
                        
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    app_logger.warning(f"Error reading file {filename}: {str(e)}")
                    continue
        
        if latest_file is None:
            raise Exception("No test cases found in output directory.")
        
        # Return full data - include pages structure with page names as keys
        result = {
            "testCases": latest_file.get("testCases", []),
            "totalTestCases": len(latest_file.get("testCases", [])),
            "generatedAt": latest_file.get("generatedAt"),
            "modelUsed": latest_file.get("modelUsed"),
            "filename": latest_file_path
        }
        
        # Include pages structure with page names as keys (e.g., {"login": {...}, "signup": {...}})
        # Extract all keys that are page names (not metadata keys)
        metadata_keys = {"testCases", "totalTestCases", "generatedAt", "modelUsed", "filename", "pages"}
        for key, value in latest_file.items():
            if key not in metadata_keys and isinstance(value, dict) and ("url" in value or "testCases" in value):
                result[key] = value
        
        # Also include pages array if it exists (for backward compatibility)
        if "pages" in latest_file:
            result["pages"] = latest_file["pages"]
        
        return result
        
    except Exception as e:
        app_logger.error(f"Error getting latest test cases: {str(e)}")
        raise Exception(f"Error retrieving test cases: {str(e)}")


def convert_json_to_csv(
    json_file_path: str,
    output_dir: str = "output",
    output_filename: Optional[str] = None
) -> str:
    """
    Convert JSON test cases file to CSV format.
    
    Args:
        json_file_path: Path to the JSON file to convert
        output_dir: Directory to save the CSV file (default: "output")
        output_filename: Optional custom filename. If not provided, generates from JSON filename
        
    Returns:
        Path to the saved CSV file
        
    Raises:
        Exception: If conversion fails
    """
    try:
        # Read JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract test cases
        test_cases = data.get("testCases", [])
        
        if not test_cases:
            raise Exception("No test cases found in JSON file")
        
        # Generate CSV filename
        if output_filename is None:
            base_name = os.path.splitext(os.path.basename(json_file_path))[0]
            output_filename = f"{base_name}.csv"
        
        # Ensure filename ends with .csv
        if not output_filename.endswith('.csv'):
            output_filename = f"{output_filename}.csv"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            app_logger.info(f"Created output directory: {output_dir}")
        
        csv_file_path = os.path.join(output_dir, output_filename)
        
        # Write CSV file with proper formatting
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'ID',
                'Title',
                'URL',
                'Inputs',
                'Steps',
                'Expected'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            for test_case in test_cases:
                # Convert inputs dict to formatted string
                inputs_dict = test_case.get("inputs", {})
                if inputs_dict:
                    # Format as key: value pairs for better readability
                    inputs_list = [f"{k}: {v}" for k, v in inputs_dict.items()]
                    inputs_str = " | ".join(inputs_list)
                else:
                    inputs_str = ""
                
                # Convert steps list to string (newline-separated for better readability in CSV)
                steps_list = test_case.get("steps", [])
                steps_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps_list)])
                
                # Convert expected list to string (newline-separated for better readability)
                expected_list = test_case.get("expected", [])
                expected_str = "\n".join([f"• {exp}" for exp in expected_list])
                
                writer.writerow({
                    'ID': test_case.get("id", ""),
                    'Title': test_case.get("title", ""),
                    'URL': test_case.get("url", ""),
                    'Inputs': inputs_str,
                    'Steps': steps_str,
                    'Expected': expected_str
                })
        
        app_logger.info(f"CSV file saved to: {csv_file_path}")
        return csv_file_path
        
    except FileNotFoundError:
        app_logger.error(f"JSON file not found: {json_file_path}")
        raise Exception(f"JSON file not found: {json_file_path}")
    except json.JSONDecodeError as e:
        app_logger.error(f"Invalid JSON format in file {json_file_path}: {str(e)}")
        raise Exception(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        app_logger.error(f"Error converting JSON to CSV: {str(e)}")
        raise Exception(f"Error converting to CSV: {str(e)}")


def convert_latest_json_to_csv(
    output_dir: str = "output",
    output_filename: Optional[str] = None
) -> str:
    """
    Convert the latest JSON test cases file to CSV format.
    
    Args:
        output_dir: Directory containing JSON files (default: "output")
        output_filename: Optional custom filename. If not provided, generates from JSON filename
        
    Returns:
        Path to the saved CSV file
        
    Raises:
        Exception: If conversion fails or no JSON files found
    """
    try:
        if not os.path.exists(output_dir):
            raise Exception("Output directory does not exist")
        
        latest_file = None
        latest_timestamp = None
        latest_file_path = None
        
        # Find latest JSON file
        for filename in os.listdir(output_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(output_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    generated_at = data.get("generatedAt", "")
                    
                    if generated_at and (latest_timestamp is None or generated_at > latest_timestamp):
                        latest_timestamp = generated_at
                        latest_file_path = file_path
                        
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    app_logger.warning(f"Error reading file {filename}: {str(e)}")
                    continue
        
        if latest_file_path is None:
            raise Exception("No JSON test case files found in output directory")
        
        # Convert to CSV
        return convert_json_to_csv(latest_file_path, output_dir, output_filename)
        
    except Exception as e:
        app_logger.error(f"Error converting latest JSON to CSV: {str(e)}")
        raise Exception(f"Error converting to CSV: {str(e)}")