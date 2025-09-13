"""
Configuration module for Slack bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Slack configuration
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

# Bot configuration
DEFAULT_MODEL = "command-r-plus"
MAX_TOKENS = 500
