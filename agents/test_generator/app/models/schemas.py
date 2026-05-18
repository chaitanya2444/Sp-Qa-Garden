"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class TestData(BaseModel):
    """Test data model for individual test case."""
    pass  # Flexible structure - can contain any JSON data


class TestCase(BaseModel):
    """Test case model."""
    id: str = Field(..., description="Unique test case identifier")
    title: str = Field(..., description="Test case title")
    url: str = Field(..., description="URL or path for the page being tested (e.g., '/login', '/signup')")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input parameters for the test")
    steps: List[str] = Field(..., description="List of test steps")
    expected: List[str] = Field(..., description="List of expected results/assertions")


class TestCaseGenerationResponse(BaseModel):
    """Response model for test case generation (returns count only)."""
    testCaseCount: int = Field(..., description="Number of test cases generated")
    modelUsed: Optional[str] = Field(None, description="LLM model that generated the test cases")
    success: bool = Field(True, description="Whether the generation was successful")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")


class TestCaseCount(BaseModel):
    """Test case count model."""
    testCaseCount: int = Field(..., description="Number of test cases in the latest generation")


class PageGroup(BaseModel):
    """Page group model containing URL and its test cases."""
    url: str = Field(..., description="URL/path for the page")
    testCases: List[TestCase] = Field(..., description="Test cases for this page")


class TestCasesResponse(BaseModel):
    """Response model for getting test cases."""
    testCases: List[TestCase] = Field(..., description="List of generated test cases (flat array)")
    totalTestCases: int = Field(..., description="Total number of test cases")
    pages: Optional[List[PageGroup]] = Field(None, description="Test cases grouped by URL/page")
    generatedAt: Optional[str] = Field(None, description="Timestamp when test cases were generated")
    modelUsed: Optional[str] = Field(None, description="LLM model that generated the test cases")
    filename: Optional[str] = Field(None, description="Name of the file containing test cases")


class JiraIssueResult(BaseModel):
    """Individual Jira issue creation result."""
    testCaseId: str = Field(..., description="Test case ID")
    jiraIssueKey: Optional[str] = Field(None, description="Created Jira issue key (e.g., DEV-123)")
    jiraIssueUrl: Optional[str] = Field(None, description="URL to the created Jira issue")
    issueType: Optional[str] = Field(None, description="Type of Jira issue created (e.g., Task, Bug, Story)")
    status: str = Field(..., description="Status: 'success' or 'failed'")
    error: Optional[str] = Field(None, description="Error message if creation failed")


class JiraIssuesResponse(BaseModel):
    """Response model for Jira issue creation."""
    created: List[JiraIssueResult] = Field(..., description="Successfully created issues")
    failed: List[JiraIssueResult] = Field(..., description="Failed issue creations")
    total: int = Field(..., description="Total number of test cases processed")
    successCount: int = Field(..., description="Number of successfully created issues")
    failureCount: int = Field(..., description="Number of failed issue creations")


class JiraConnectionTestResponse(BaseModel):
    """Response model for Jira connection test."""
    connected: bool = Field(..., description="Whether connection is successful")
    jiraUrl: str = Field(..., description="Jira base URL")
    projectKey: str = Field(..., description="Jira project key")
    projectName: str = Field(..., description="Jira project name")
    userEmail: str = Field(..., description="Authenticated user email")
    userDisplayName: str = Field(..., description="Authenticated user display name")
    availableIssueTypes: List[str] = Field(..., description="Available issue types in the project")
    message: str = Field(..., description="Status message")


class CrawlerHandoverRequest(BaseModel):
    """Request model for handover from Crawler agent."""
    run_id: str = Field(..., description="ID of the current run")
    locators_path: str = Field(..., description="Absolute path to the locators JSON file")
    target_url: Optional[str] = Field(None, description="The base URL of the website being tested")

