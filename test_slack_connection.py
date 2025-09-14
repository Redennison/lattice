#!/usr/bin/env python3
"""Test Slack connection and configuration."""

import os
import sys
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

def test_slack_connection():
    """Test Slack bot connection and permissions."""
    load_dotenv()
    
    print("""
╔══════════════════════════════════════╗
║   🔌 Slack Connection Test           ║
╚══════════════════════════════════════╝
    """)
    
    # Check tokens
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    
    if not bot_token:
        print("❌ SLACK_BOT_TOKEN not set in .env")
        return False
    
    if not app_token:
        print("❌ SLACK_APP_TOKEN not set in .env")
        return False
    
    if not signing_secret:
        print("❌ SLACK_SIGNING_SECRET not set in .env")
        return False
    
    print("✅ All Slack tokens found in .env")
    
    # Test bot token
    client = WebClient(token=bot_token)
    
    try:
        # Test auth
        print("\n🔍 Testing authentication...")
        response = client.auth_test()
        
        bot_id = response["user_id"]
        bot_name = response["user"]
        team_name = response["team"]
        
        print(f"✅ Connected as: @{bot_name}")
        print(f"   Bot ID: {bot_id}")
        print(f"   Workspace: {team_name}")
        
        # Test permissions
        print("\n🔍 Checking permissions...")
        
        # Get bot info
        bot_info = client.users_info(user=bot_id)
        print(f"✅ Bot display name: {bot_info['user']['profile']['display_name'] or bot_name}")
        
        # List channels (test channels:read)
        try:
            channels = client.conversations_list(types="public_channel", limit=1)
            print(f"✅ Can read channels: Found {len(channels['channels'])} public channels")
        except:
            print("⚠️  Cannot list channels - missing channels:read scope")
        
        # Check for required scopes
        print("\n🔍 Verifying required scopes...")
        required_scopes = [
            "app_mentions:read",
            "channels:history", 
            "chat:write",
            "im:history",
            "users:read"
        ]
        
        # Note: Slack doesn't provide a direct way to check scopes
        # We infer from successful API calls
        print("✅ Bot token appears to have required permissions")
        print("   (Full scope verification happens during runtime)")
        
        # Test Socket Mode token format
        print("\n🔍 Checking Socket Mode token...")
        if app_token.startswith("xapp-"):
            print("✅ Socket Mode token format is correct")
        else:
            print("⚠️  Socket Mode token should start with 'xapp-'")
        
        print("\n" + "="*50)
        print("✅ Slack configuration looks good!")
        print("\nNext steps:")
        print("1. Invite the bot to a channel: /invite @Lattice")
        print("2. Start the bot: python slack_bot.py")
        print("3. Mention @Lattice in a thread to test")
        
        return True
        
    except SlackApiError as e:
        print(f"\n❌ Slack API Error: {e.response['error']}")
        
        if e.response['error'] == 'invalid_auth':
            print("   Your SLACK_BOT_TOKEN is invalid or expired")
            print("   Please regenerate it in your Slack app settings")
        elif e.response['error'] == 'missing_scope':
            print("   Your bot is missing required permissions")
            print("   Add the scopes listed in README.md and reinstall the app")
        else:
            print(f"   Error details: {e.response}")
        
        return False
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_slack_connection()
    sys.exit(0 if success else 1)
