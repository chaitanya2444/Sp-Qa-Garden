"""Configuration settings for the application."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
    )
    
    # API Keys
    openrouter_api_key: Optional[str] = None  # Primary (Legacy Fallback)
    xai_api_key: Optional[str] = None         # Primary (Grok)
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None        # High-Speed (Groq - Single/Legacy)
    # Default includes user provided keys for robustness
    groq_api_keys: Optional[str] = None  # Comma-separated list for rotation (read from .env)
    huggingface_api_key: Optional[str] = None # Fallback
    jira_api_key: Optional[str] = None
    
    # LLM Configuration
    # Models
    gemini_model: str = "gemini-2.0-flash"
    xai_model: str = "grok-beta"
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_model: str = "mistralai/mistral-7b-instruct:free"
    huggingface_model: str = "google/gemma-2-9b-it"
    ollama_model: str = "llama3"

    xai_base_url: str = "https://api.x.ai/v1"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ollama_base_url: str = "http://localhost:11434/api/generate"
    
    # Application Settings
    app_name: str = "Test Case Generator API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # CORS Settings - stored as strings, converted to lists by properties
    cors_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"
    
    # Request Settings
    max_upload_size: int = 20 * 1024 * 1024  # 20MB
    request_timeout: int = 600  # seconds (10 minutes - for Gemini test case generation)
    
    # Jira Configuration
    jira_url: Optional[str] = None  # Jira base URL (e.g., https://your-domain.atlassian.net - use base URL only, not full path)
    jira_project_key: Optional[str] = None  # Jira project key (e.g., DEV)
    jira_email: Optional[str] = None  # Jira account email (for API authentication)
    
    def _parse_list(self, value: str) -> list[str]:
        """Parse string value to list."""
        if not value or value.strip() == "*":
            return ["*"]
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]
        return [value.strip()]
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        return self._parse_list(self.cors_origins)
    
    @property
    def cors_allow_methods_list(self) -> list[str]:
        """Get CORS methods as list."""
        return self._parse_list(self.cors_allow_methods)
    
    @property
    def cors_allow_headers_list(self) -> list[str]:
        """Get CORS headers as list."""
        return self._parse_list(self.cors_allow_headers)
    
    @property
    def groq_api_keys_list(self) -> list[str]:
        """Get Groq API keys as list for rotation, merging env and hardcoded defaults."""
        keys = []
        
        # 1. Add keys from .env (if any)
        if self.groq_api_keys:
            keys.extend(self._parse_list(self.groq_api_keys))
        
        # 2. Add individual key from .env
        if self.groq_api_key:
            keys.append(self.groq_api_key)
            
        # 3. No hardcoded keys - all keys must come from environment variables
        
        # 4. Remove duplicates and empty strings
        unique_keys = list(set([k.strip() for k in keys if k and k.strip() and "gsk_" in k]))
        return unique_keys


settings = Settings()

