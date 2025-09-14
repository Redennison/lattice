"""Configuration management for the Lattice bot."""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""
    
    # Slack Configuration
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    
    # Deimos/Martian Configuration
    DEIMOS_API_URL = os.getenv("DEIMOS_API_URL", "https://api.withmartian.com/v1")
    DEIMOS_API_KEY = os.getenv("DEIMOS_API_KEY")
    
    # Cohere Configuration
    COHERE_API_KEY = os.getenv("CO_API_KEY")
    
    # Jira Configuration
    JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "CCS")
    
    # GitHub Configuration
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO = os.getenv("GITHUB_REPO")
    GITHUB_DEFAULT_BRANCH = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
    
    # Application Configuration
    MAX_THREAD_MESSAGES = int(os.getenv("MAX_THREAD_MESSAGES", "50"))
    DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent
    LOGS_DIR = PROJECT_ROOT / "logs"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        required = {
            "COHERE_API_KEY": cls.COHERE_API_KEY,
            "JIRA_BASE_URL": cls.JIRA_BASE_URL,
            "JIRA_EMAIL": cls.JIRA_EMAIL,
            "JIRA_API_TOKEN": cls.JIRA_API_TOKEN,
            "GITHUB_TOKEN": cls.GITHUB_TOKEN,
            "GITHUB_REPO": cls.GITHUB_REPO,
        }
        
        missing = [key for key, value in required.items() if not value]
        
        if missing:
            print(f"❌ Missing required configuration: {', '.join(missing)}")
            return False
        
        return True
    
    @classmethod
    def get_github_owner_repo(cls) -> tuple[str, str]:
        """Extract owner and repo name from GITHUB_REPO."""
        if "/" in cls.GITHUB_REPO:
            parts = cls.GITHUB_REPO.split("/")
            return parts[0], parts[1]
        raise ValueError(f"Invalid GITHUB_REPO format: {cls.GITHUB_REPO}")
