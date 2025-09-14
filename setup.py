#!/usr/bin/env python3
"""Setup script for Lattice Bot - installs dependencies and configures environment."""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command with error handling."""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("""
╔══════════════════════════════════════╗
║   🤖 Lattice Bot Setup Script        ║
║   Automated Bug Fix Assistant        ║
╚══════════════════════════════════════╝
    """)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install main dependencies
    if not run_command("pip install -r requirements.txt", "Installing main dependencies"):
        print("\n⚠️ Failed to install main dependencies")
        print("Try: pip install -r requirements.txt manually")
        sys.exit(1)
    
    # Install deimos-router
    deimos_path = Path("deimos-router")
    if deimos_path.exists():
        if not run_command("pip install -e ./deimos-router", "Installing deimos-router"):
            print("\n⚠️ Failed to install deimos-router")
            print("Try: pip install -e ./deimos-router manually")
    else:
        print("⚠️ deimos-router directory not found - skipping")
    
    # Check .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("\n❌ .env file not found!")
        print("Please create .env with required configuration")
        sys.exit(1)
    
    # Validate environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("\n⚠️ python-dotenv not found, skipping validation")
        print("Install with: pip install python-dotenv")
        return
    
    required_vars = {
        "Core": ["COHERE_API_KEY", "DEIMOS_API_KEY"],
        "Jira": ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
        "GitHub": ["GITHUB_TOKEN", "GITHUB_REPO"],
        "Slack (for bot)": ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET"]
    }
    
    print("\n📋 Checking configuration:")
    all_good = True
    
    for category, vars in required_vars.items():
        print(f"\n{category}:")
        for var in vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if "KEY" in var or "TOKEN" in var or "SECRET" in var:
                    display = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
                else:
                    display = value
                print(f"  ✅ {var}: {display}")
            else:
                print(f"  ❌ {var}: NOT SET")
                if category != "Slack (for bot)":
                    all_good = False
    
    if not all_good:
        print("\n⚠️ Some required variables are missing")
        print("Please update .env file with missing values")
    
    # Create logs directory
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir()
        print("\n✅ Created logs directory")
    
    print("\n" + "="*50)
    
    if all_good or not any(os.getenv(var) for var in required_vars["Slack (for bot)"]):
        print("\n✅ Setup complete!")
        print("\nNext steps:")
        
        if not any(os.getenv(var) for var in required_vars["Slack (for bot)"]):
            print("\n📱 To use with Slack:")
            print("1. Create a Slack app at https://api.slack.com/apps")
            print("2. Enable Socket Mode")
            print("3. Add bot token scopes: app_mentions:read, channels:history, chat:write, im:history, users:read")
            print("4. Install app to workspace")
            print("5. Add tokens to .env file")
            print("6. Run: python slack_bot.py")
        else:
            print("\n🚀 To start the Slack bot:")
            print("   python slack_bot.py")
        
        print("\n🧪 To test components:")
        print("   python test_components.py")
        
        print("\n📚 For more info, see README.md")
    else:
        print("\n⚠️ Setup incomplete - fix configuration issues above")
        sys.exit(1)

if __name__ == "__main__":
    main()
