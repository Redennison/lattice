# Slack App Setup Guide for Lattice Bot

## Step-by-Step Slack App Configuration

### 1. Create the Slack App

1. Navigate to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter:
   - **App Name**: Lattice
   - **Pick a workspace**: Select your workspace
5. Click **"Create App"**

### 2. Configure Basic Information

1. Go to **"Basic Information"**
2. Save the **Signing Secret** (you'll need this for `SLACK_SIGNING_SECRET`)

### 3. Set Up OAuth & Permissions

1. Navigate to **"OAuth & Permissions"** in the sidebar
2. Scroll to **"Scopes"** → **"Bot Token Scopes"**
3. Add these OAuth scopes:
   - `app_mentions:read` - Read messages that mention your app
   - `channels:history` - View messages in public channels
   - `chat:write` - Send messages as the bot
   - `im:history` - View direct messages
   - `users:read` - View user information
   - `groups:history` - View messages in private channels (if needed)
4. Scroll up and click **"Install to Workspace"**
5. Authorize the app
6. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
   - Save this as `SLACK_BOT_TOKEN` in your `.env`

### 4. Enable Socket Mode

1. Go to **"Socket Mode"** in the sidebar
2. Toggle **"Enable Socket Mode"** to ON
3. You'll be prompted to create an app-level token:
   - **Token Name**: Lattice Socket Token
   - **Scope**: Add `connections:write`
4. Click **"Generate"**
5. Copy the token (starts with `xapp-`)
   - Save this as `SLACK_APP_TOKEN` in your `.env`

### 5. Configure Event Subscriptions

1. Navigate to **"Event Subscriptions"** in the sidebar
2. Toggle **"Enable Events"** to ON
3. Under **"Subscribe to bot events"**, add:
   - `app_mention` - When someone mentions @Lattice
   - `message.im` - Direct messages to the bot
4. Click **"Save Changes"**

### 6. Update App Manifest (Optional - Advanced)

For quick setup, you can use this app manifest:

```yaml
display_information:
  name: Lattice
  description: Automated Bug Fix Assistant
  background_color: "#2c2d30"
features:
  bot_user:
    display_name: Lattice
    always_online: true
oauth_config:
  scopes:
    bot:
      - app_mentions:read
      - channels:history
      - chat:write
      - im:history
      - users:read
      - groups:history
settings:
  event_subscriptions:
    bot_events:
      - app_mention
      - message.im
  socket_mode_enabled: true
```

### 7. Add Bot to Channels

After installation:
1. Go to your Slack workspace
2. Open any channel where you want to use the bot
3. Type `/invite @Lattice`
4. The bot is now ready to respond to mentions

## Environment Variables Summary

Add these to your `.env` file:

```bash
# From Basic Information
SLACK_SIGNING_SECRET=your_signing_secret_here

# From OAuth & Permissions
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# From Socket Mode
SLACK_APP_TOKEN=xapp-your-app-token-here
```

## Testing Your Setup

1. Start the bot:
   ```bash
   python slack_bot.py
   ```

2. In Slack, create a test thread:
   ```
   User: There's a bug in the login system
   User: It crashes when email has special characters
   User: @Lattice please help fix this
   ```

3. The bot should respond with:
   - Acknowledgment message
   - Processing status
   - Links to created Jira ticket and GitHub PR

## Troubleshooting

### Bot Not Responding

- **Check Socket Mode**: Ensure it's enabled and token is correct
- **Verify Events**: Check Event Subscriptions are enabled
- **Bot in Channel**: Make sure bot is invited to the channel
- **Check Logs**: Run with `DEBUG_MODE=True` in `.env`

### Permission Errors

- **Missing Scopes**: Re-check OAuth scopes are all added
- **Reinstall App**: After adding scopes, reinstall to workspace
- **Token Issues**: Verify tokens start with correct prefixes

### Connection Issues

- **Socket Mode Token**: Must have `connections:write` scope
- **Network**: Check firewall/proxy settings
- **Python Version**: Ensure Python 3.8+

## Security Best Practices

1. **Never commit tokens** to version control
2. **Rotate tokens** periodically
3. **Limit bot to specific channels** if possible
4. **Monitor bot activity** in Slack admin console
5. **Use environment variables** for all sensitive data

## Support

For issues with:
- **Slack API**: Check [Slack API Documentation](https://api.slack.com)
- **Bot Framework**: See [Slack Bolt Python](https://slack.dev/bolt-python)
- **Lattice Bot**: Open an issue in the repository
