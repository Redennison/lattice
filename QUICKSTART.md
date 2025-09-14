# 🚀 Lattice Bot Quick Start Guide

## Step 1: Create Slack App (2 minutes)

1. Open [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Name: **Lattice**, Select your workspace

## Step 2: Get Tokens (3 minutes)

### A. Get Signing Secret
- In **Basic Information** → Copy **Signing Secret**
- Add to `.env`: `SLACK_SIGNING_SECRET=your_secret_here`

### B. Set Bot Permissions & Get Bot Token
- Go to **OAuth & Permissions**
- Add these Bot Token Scopes:
  - `app_mentions:read`
  - `channels:history`
  - `chat:write`
  - `im:history`
  - `users:read`
- Click **Install to Workspace** → **Allow**
- Copy **Bot User OAuth Token** (xoxb-...)
- Add to `.env`: `SLACK_BOT_TOKEN=xoxb-your-token`

### C. Enable Socket Mode & Get App Token
- Go to **Socket Mode** → Toggle **ON**
- Create token: Name: "Socket Token", Scope: `connections:write`
- Click **Generate**
- Copy token (xapp-...)
- Add to `.env`: `SLACK_APP_TOKEN=xapp-your-token`

### D. Subscribe to Events
- Go to **Event Subscriptions** → Toggle **ON**
- Add Bot Events:
  - `app_mention`
  - `message.im`
- **Save Changes**

## Step 3: Test Without Slack First

```bash
# Test the workflow without Slack
python3 example_workflow.py
```

## Step 4: Start the Bot

```bash
# Once Slack tokens are added
python3 slack_bot.py
```

## Step 5: Use in Slack

1. Invite bot to channel: `/invite @Lattice`
2. Create a thread about a bug
3. Mention `@Lattice` in the thread
4. Bot will process and create Jira ticket + GitHub PR

## 📝 Example Message

```
User: The login page crashes when email has special characters
User: Getting 500 error in auth_handler.py
@Lattice please fix this
```

## 🧪 Testing Commands

```bash
# Test components individually
python3 test_components.py

# Test Slack connection (after adding tokens)
python3 test_slack_connection.py

# Run integration tests
python3 test_integration.py

# Run example workflow (no Slack needed)
python3 example_workflow.py
```

## 🔧 Troubleshooting

If bot doesn't respond:
- Check Socket Mode is enabled
- Verify bot is in the channel
- Check logs for errors
- Run `python3 test_slack_connection.py`

## 📚 Files Overview

- `slack_bot.py` - Main bot application
- `mcp_server.py` - Orchestrates the workflow
- `config.py` - Configuration management
- `services/` - LLM services (Cohere, Deimos)
- `tools/` - Jira and GitHub integrations
- `.env` - Your credentials (keep private!)
