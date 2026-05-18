"""Jira API client service for creating test case issues."""
import httpx
import base64
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logger import app_logger


class JiraClient:
    """Client for interacting with Jira API."""
    
    def __init__(self):
        self.api_key = settings.jira_api_key
        self.jira_url = settings.jira_url
        self.project_key = settings.jira_project_key
        self.email = settings.jira_email
        self.timeout = 30  # 30 seconds for Jira API calls
        
        if not self.jira_url:
            raise ValueError("JIRA_URL is required. Please configure it in your .env file.")
        if not self.project_key:
            raise ValueError("JIRA_PROJECT_KEY is required. Please configure it in your .env file.")
        if not self.api_key:
            raise ValueError("JIRA_API_KEY is required. Please configure it in your .env file.")
        if not self.email:
            raise ValueError("JIRA_EMAIL is required. Please configure it in your .env file.")
        
        # Ensure URL doesn't have trailing slash
        self.base_url = self.jira_url.rstrip('/')
        self.api_base = f"{self.base_url}/rest/api/3"
        
        # Create basic auth header
        auth_string = f"{self.email}:{self.api_key}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        self.auth_header = f"Basic {auth_b64}"
    
    async def _get_issue_type_id(self, issue_type_name: str) -> Optional[str]:
        """
        Get issue type ID from issue type name.
        
        Args:
            issue_type_name: Name of the issue type (e.g., "Test", "Bug", "Story")
            
        Returns:
            Issue type ID if found, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get project metadata
                project_response = await client.get(
                    f"{self.api_base}/project/{self.project_key}",
                    headers={
                        "Authorization": self.auth_header,
                        "Accept": "application/json"
                    }
                )
                
                if project_response.status_code == 200:
                    project_info = project_response.json()
                    for issue_type in project_info.get("issueTypes", []):
                        if issue_type.get("name", "").lower() == issue_type_name.lower():
                            return issue_type.get("id")
                
                # Try createmeta endpoint as fallback
                createmeta_response = await client.get(
                    f"{self.api_base}/issue/createmeta?projectKeys={self.project_key}&expand=projects.issuetypes",
                    headers={
                        "Authorization": self.auth_header,
                        "Accept": "application/json"
                    }
                )
                
                if createmeta_response.status_code == 200:
                    createmeta_data = createmeta_response.json()
                    for project in createmeta_data.get("projects", []):
                        if project.get("key") == self.project_key:
                            for issue_type in project.get("issuetypes", []):
                                if issue_type.get("name", "").lower() == issue_type_name.lower():
                                    return issue_type.get("id")
                            break
                
                return None
        except Exception as e:
            app_logger.warning(f"Could not fetch issue type ID for '{issue_type_name}': {str(e)}")
            return None
    
    async def create_test_case_issue(
        self,
        test_case: Dict[str, Any],
        issue_type: str = "Task"
    ) -> Dict[str, Any]:
        """
        Create a Jira issue (Task) for a test case.
        
        Args:
            test_case: Test case dictionary with id, title, steps, expected, etc.
            issue_type: Type of Jira issue (default: "Task")
            
        Returns:
            Created Jira issue data
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Format test case description
            description = self._format_test_case_description(test_case)
            
            # Get issue type ID (preferred) or use name as fallback
            issue_type_id = await self._get_issue_type_id(issue_type)
            
            # Build issue type field - prefer ID, fallback to name
            if issue_type_id:
                issue_type_field = {"id": issue_type_id}
            else:
                issue_type_field = {"name": issue_type}
            
            # Create issue payload
            issue_data = {
                "fields": {
                    "project": {
                        "key": self.project_key
                    },
                    "summary": test_case.get("title", f"Test Case {test_case.get('id', 'Unknown')}"),
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": description
                    },
                    "issuetype": issue_type_field
                }
            }
            
            # Add custom fields if needed (test case ID, URL, etc.)
            if test_case.get("id"):
                issue_data["fields"]["summary"] = f"[{test_case.get('id')}] {issue_data['fields']['summary']}"
            
            app_logger.info(f"Creating Jira issue for test case: {test_case.get('id')}")
            
            # Make API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base}/issue",
                    json=issue_data,
                    headers={
                        "Authorization": self.auth_header,
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 201:
                    issue = response.json()
                    app_logger.info(f"Successfully created Jira issue: {issue.get('key')}")
                    return issue
                else:
                    error_text = response.text
                    # If issue type error, provide helpful message
                    if response.status_code == 400 and "issuetype" in error_text.lower():
                        # Try to get available issue types for better error message
                        try:
                            project_response = await client.get(
                                f"{self.api_base}/project/{self.project_key}",
                                headers={
                                    "Authorization": self.auth_header,
                                    "Accept": "application/json"
                                }
                            )
                            if project_response.status_code == 200:
                                project_info = project_response.json()
                                available_types = [it.get("name") for it in project_info.get("issueTypes", [])]
                                if available_types:
                                    error_msg = (
                                        f"Invalid issue type '{issue_type}'. "
                                        f"Available issue types for project {self.project_key}: {', '.join(available_types)}. "
                                        f"Original error: {error_text}"
                                    )
                                else:
                                    error_msg = f"Jira API error: {response.status_code} - {error_text}"
                            else:
                                error_msg = f"Jira API error: {response.status_code} - {error_text}"
                        except Exception as e:
                            app_logger.warning(f"Could not fetch available issue types: {str(e)}")
                            error_msg = f"Jira API error: {response.status_code} - {error_text}"
                    else:
                        error_msg = f"Jira API error: {response.status_code} - {error_text}"
                    
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except httpx.TimeoutException:
            error_msg = "Jira API request timeout"
            app_logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Jira API error: {str(e)}"
            app_logger.error(error_msg)
            raise Exception(error_msg)
    
    def _format_test_case_description(self, test_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format test case data as Jira description (using ADF - Atlassian Document Format).
        
        Args:
            test_case: Test case dictionary
            
        Returns:
            ADF document structure
        """
        content = []
        
        # Test Case ID
        if test_case.get("id"):
            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Test Case ID: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": test_case.get("id")}
                ]
            })
        
        # URL
        if test_case.get("url"):
            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "URL: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": test_case.get("url")}
                ]
            })
        
        # Inputs
        if test_case.get("inputs"):
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": "Inputs:", "marks": [{"type": "strong"}]}]
            })
            inputs_text = ", ".join([f"{k}: {v}" for k, v in test_case.get("inputs", {}).items()])
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": inputs_text}]
            })
        
        # Steps
        if test_case.get("steps"):
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": "Steps:", "marks": [{"type": "strong"}]}]
            })
            steps_list = []
            for i, step in enumerate(test_case.get("steps", []), 1):
                steps_list.append({
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"{i}. {step}"}]
                        }
                    ]
                })
            content.append({
                "type": "bulletList",
                "content": steps_list
            })
        
        # Expected Results
        if test_case.get("expected"):
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": "Expected Results:", "marks": [{"type": "strong"}]}]
            })
            expected_list = []
            for exp in test_case.get("expected", []):
                expected_list.append({
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": exp}]
                        }
                    ]
                })
            content.append({
                "type": "bulletList",
                "content": expected_list
            })
        
        return content
    
    async def create_multiple_test_case_issues(
        self,
        test_cases: List[Dict[str, Any]],
        issue_type: str = "Task"
    ) -> List[Dict[str, Any]]:
        """
        Create multiple Jira issues for test cases.
        
        Args:
            test_cases: List of test case dictionaries
            issue_type: Type of Jira issue (default: "Test")
            
        Returns:
            List of created Jira issues
        """
        created_issues = []
        errors = []
        
        for test_case in test_cases:
            try:
                issue = await self.create_test_case_issue(test_case, issue_type)
                created_issues.append({
                    "testCaseId": test_case.get("id"),
                    "jiraIssueKey": issue.get("key"),
                    "jiraIssueUrl": f"{self.base_url}/browse/{issue.get('key')}",
                    "issueType": issue_type,
                    "status": "success"
                })
            except Exception as e:
                errors.append({
                    "testCaseId": test_case.get("id"),
                    "error": str(e),
                    "issueType": issue_type,
                    "status": "failed"
                })
                app_logger.error(f"Failed to create Jira issue for test case {test_case.get('id')}: {str(e)}")
        
        return {
            "created": created_issues,
            "failed": errors,
            "total": len(test_cases),
            "successCount": len(created_issues),
            "failureCount": len(errors)
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Jira API connection and configuration.
        
        Returns:
            Dictionary with connection status and project information
            
        Raises:
            Exception: If connection test fails
        """
        try:
            app_logger.info("Testing Jira connection...")
            
            # Test 1: Get current user info (validates authentication)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                user_response = await client.get(
                    f"{self.api_base}/myself",
                    headers={
                        "Authorization": self.auth_header,
                        "Accept": "application/json"
                    }
                )
                
                if user_response.status_code != 200:
                    raise Exception(f"Authentication failed: {user_response.status_code} - {user_response.text}")
                
                user_info = user_response.json()
                
                # Test 2: Get project info (validates project key)
                project_response = await client.get(
                    f"{self.api_base}/project/{self.project_key}",
                    headers={
                        "Authorization": self.auth_header,
                        "Accept": "application/json"
                    }
                )
                
                if project_response.status_code != 200:
                    raise Exception(f"Project not found or inaccessible: {project_response.status_code} - {project_response.text}")
                
                project_info = project_response.json()
                
                # Test 3: Get issue types for the project (from project metadata)
                issue_types = []
                if "issueTypes" in project_info:
                    # Extract issue type names from project metadata
                    for issue_type in project_info.get("issueTypes", []):
                        issue_type_name = issue_type.get("name")
                        if issue_type_name and issue_type_name not in issue_types:
                            issue_types.append(issue_type_name)
                
                # If no issue types found in project metadata, try createmeta endpoint
                if not issue_types:
                    createmeta_response = await client.get(
                        f"{self.api_base}/issue/createmeta?projectKeys={self.project_key}&expand=projects.issuetypes",
                        headers={
                            "Authorization": self.auth_header,
                            "Accept": "application/json"
                        }
                    )
                    
                    if createmeta_response.status_code == 200:
                        createmeta_data = createmeta_response.json()
                        for project in createmeta_data.get("projects", []):
                            if project.get("key") == self.project_key:
                                for issue_type in project.get("issuetypes", []):
                                    issue_type_name = issue_type.get("name")
                                    if issue_type_name and issue_type_name not in issue_types:
                                        issue_types.append(issue_type_name)
                                break
                
                app_logger.info("Jira connection test successful")
                
                return {
                    "connected": True,
                    "jiraUrl": self.base_url,
                    "projectKey": self.project_key,
                    "projectName": project_info.get("name", "Unknown"),
                    "userEmail": user_info.get("emailAddress", "Unknown"),
                    "userDisplayName": user_info.get("displayName", "Unknown"),
                    "availableIssueTypes": issue_types[:10] if issue_types else ["Test", "Bug", "Story"],  # Limit to first 10
                    "message": "Jira connection successful"
                }
                
        except httpx.TimeoutException:
            error_msg = "Jira API request timeout"
            app_logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Jira connection test failed: {str(e)}"
            app_logger.error(error_msg)
            raise Exception(error_msg)

