"""
Configuration module for MCP Client with OpenRouter
Handles environment variables and default settings
"""
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration settings for MCP Client"""
    
    def __init__(self):
        # OpenRouter settings
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.default_model = os.getenv("DEFAULT_MODEL", "z-ai/glm-4.5-air:free")
        self.openrouter_endpoint = os.getenv("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Notion OAuth settings
        self.notion_client_id = os.getenv("NOTION_CLIENT_ID")
        self.notion_client_secret = os.getenv("NOTION_CLIENT_SECRET")
        self.notion_redirect_uri = os.getenv("NOTION_REDIRECT_URI", "http://localhost:8000/api/notion/callback")
        self.notion_oauth_url = "https://api.notion.com/v1/oauth/authorize"
        self.notion_token_url = "https://api.notion.com/v1/oauth/token"
        self.notion_mcp_url = os.getenv("NOTION_MCP_URL", "https://mcp.notion.com/mcp")
        self.notion_api_version = "2022-06-28"
        
        # Validate required settings
        self._validate_config()
    
    def _validate_config(self):
        """Validate that required configuration is present"""
        if not self.openrouter_api_key:
            import warnings
            warnings.warn(
                "OPENROUTER_API_KEY not found in environment variables. "
                "Please copy .env.example to .env and add your API key. "
                "Some features will not work without it.",
                UserWarning
            )
    
    @property
    def headers(self) -> dict:
        """Get default headers for OpenRouter API requests"""
        return {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "MCP Client"
        }

# Global config instance
config = Config()

# Export as direct variables for backward compatibility
OPENROUTER_API_KEY = config.openrouter_api_key
DEFAULT_MODEL = config.default_model
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_ENDPOINT = config.openrouter_endpoint

# Notion configuration exports
NOTION_CLIENT_ID = config.notion_client_id
NOTION_CLIENT_SECRET = config.notion_client_secret
NOTION_REDIRECT_URI = config.notion_redirect_uri
NOTION_OAUTH_URL = config.notion_oauth_url
NOTION_TOKEN_URL = config.notion_token_url
NOTION_MCP_URL = config.notion_mcp_url
NOTION_API_VERSION = config.notion_api_version
