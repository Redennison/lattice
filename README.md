# 🤖 Lattice Bot - Automated Bug Fix Assistant

An intelligent Slack bot that automatically converts bug discussions into Jira tickets and creates GitHub pull requests with AI-generated fixes.

## 🎯 Features

- **Slack Integration**: Responds to @Lattice mentions in threads
- **Smart Bug Parsing**: Uses Cohere AI to extract structured bug reports from conversations
- **Jira Automation**: Creates detailed tickets with proper formatting
- **Code Analysis**: Analyzes your GitHub repository for context
- **Automated Fixes**: Generates code fixes using AI
- **Pull Request Creation**: Opens PRs with fixes directly on GitHub
- **Cost Optimization**: Uses Deimos/Martian routing to select optimal LLM models

## 🏗️ Architecture

```
Slack Thread (@Lattice mention)
        ↓
    Slack Bot
        ↓
    MCP Server
        ↓
  Deimos Router → Cohere LLM
        ↓
    Tools Layer
    ├── Jira Tool (ticket creation)
    ├── GitHub Tool (PR creation)
    └── Code Analyzer
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Slack workspace with admin access
- Jira account with API access
- GitHub repository access
- Cohere API key
- Deimos/Martian API key (optional, for routing)

### Installation

1. **Clone the repository**
```bash
git clone <your-repo>
cd lattice
```

2. **Run setup script**
```bash
python setup.py
```

3. **Configure environment variables**

Update `.env` with your credentials:

```env
# Cohere
CO_API_KEY=your_cohere_key

# Jira
JIRA_BASE_URL=yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_token
JIRA_PROJECT_KEY=YOUR_PROJECT

# GitHub
GITHUB_TOKEN=ghp_your_github_token
GITHUB_REPO=owner/repository
GITHUB_DEFAULT_BRANCH=main

# Slack (see setup instructions below)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret

# Optional
DEIMOS_API_KEY=your_deimos_key
```

### Slack App Setup

1. **Create a Slack App**
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Click "Create New App" → "From scratch"
   - Name it "Lattice" and select your workspace

2. **Configure OAuth & Permissions**
   - Add Bot Token Scopes:
     - `app_mentions:read`
     - `channels:history`
     - `chat:write`
     - `im:history`
     - `users:read`
   - Install to workspace

3. **Enable Socket Mode**
   - Go to Socket Mode settings
   - Enable Socket Mode
   - Generate an app-level token with `connections:write` scope

4. **Subscribe to Events**
   - Enable Events
   - Subscribe to bot events:
     - `app_mention`
     - `message.im`

5. **Copy Tokens to .env**
   - Bot User OAuth Token → `SLACK_BOT_TOKEN`
   - App-Level Token → `SLACK_APP_TOKEN`
   - Signing Secret → `SLACK_SIGNING_SECRET`

## 📖 Usage

### Start the Bot

```bash
python slack_bot.py
```

### Using in Slack

1. **Start a thread** discussing a bug
2. **Mention @Lattice** in the thread
3. The bot will:
   - Parse the conversation
   - Create a Jira ticket
   - Analyze your codebase
   - Generate a fix (if possible)
   - Create a GitHub PR
   - Reply with links to the ticket and PR

### Example Conversation

```
User1: We have a problem with the login button
User2: It's returning 500 error when clicked
User1: Happens only for users with special characters in email
@Lattice please fix this
```

Bot Response:
```
✅ Bug Report Processed Successfully!

📝 Jira Ticket: CCS-123
🏷️ Severity: High
🔧 Pull Request: View PR

The PR has been created and is ready for review.
```

## 🧪 Testing

Test individual components:

```bash
python test_components.py
```

Test specific services:

```python
# Test Jira connection
python -c "from tools.jira_tool import JiraTool; JiraTool().find_similar_issues('test')"

# Test GitHub access
python -c "from tools.github_tool import GitHubTool; print(GitHubTool().repo.full_name)"
```

## 📁 Project Structure

```
lattice/
├── slack_bot.py           # Main Slack bot
├── mcp_server.py          # MCP server orchestrator
├── config.py              # Configuration management
├── services/
│   ├── cohere_service.py  # Cohere LLM integration
│   └── deimos_service.py  # Deimos routing
├── tools/
│   ├── jira_tool.py       # Jira operations
│   └── github_tool.py     # GitHub operations
├── deimos-router/         # Deimos routing library
├── setup.py               # Setup script
├── test_components.py     # Component tests
└── requirements.txt       # Python dependencies
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CO_API_KEY` | Cohere API key | Yes |
| `JIRA_BASE_URL` | Jira instance URL | Yes |
| `JIRA_EMAIL` | Jira account email | Yes |
| `JIRA_API_TOKEN` | Jira API token | Yes |
| `JIRA_PROJECT_KEY` | Jira project key | Yes |
| `GITHUB_TOKEN` | GitHub personal access token | Yes |
| `GITHUB_REPO` | GitHub repository (owner/name) | Yes |
| `SLACK_BOT_TOKEN` | Slack bot token | For Slack |
| `SLACK_APP_TOKEN` | Slack app token | For Slack |
| `DEIMOS_API_KEY` | Deimos API key | Optional |
| `MAX_THREAD_MESSAGES` | Max messages to process | Optional (50) |

## 🤝 Workflow

1. **Message Processing**: Bot extracts up to 50 messages from thread
2. **Bug Parsing**: Cohere analyzes conversation and structures bug report
3. **Duplicate Check**: Searches for similar existing Jira issues
4. **Code Analysis**: Searches GitHub repo for relevant files
5. **Fix Generation**: AI generates code changes
6. **Ticket Creation**: Creates Jira ticket with all details
7. **PR Creation**: Opens GitHub PR with proposed fixes
8. **Linking**: Updates Jira ticket with PR link

## 🚨 Troubleshooting

### Common Issues

**Bot not responding to mentions**
- Check Socket Mode is enabled
- Verify bot is in the channel
- Check SLACK_APP_TOKEN is correct

**Jira ticket creation fails**
- Verify API token permissions
- Check project key exists
- Ensure issue type "Bug" exists

**GitHub PR creation fails**
- Check token has repo permissions
- Verify repository exists and is accessible
- Ensure default branch name is correct

**No automated fix generated**
- Some bugs require manual investigation
- Check Cohere API key is valid
- Review code context extraction

### Debug Mode

Enable debug logging in `.env`:
```env
DEBUG_MODE=True
```

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with [Cohere](https://cohere.ai) for LLM capabilities
- Uses [Deimos/Martian](https://withmartian.com) for intelligent routing
- Powered by [Slack Bolt](https://slack.dev/bolt-python) framework
