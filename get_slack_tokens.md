# Get Your Slack Tokens

## Token 1: Signing Secret
**Basic Information** → Copy **Signing Secret**
```
SLACK_SIGNING_SECRET=YOUR_SECRET_HERE
```

## Token 2: Bot Token  
**OAuth & Permissions** → Add these scopes:
- app_mentions:read
- channels:history
- chat:write
- im:history
- users:read

→ **Install to Workspace** → Copy **Bot User OAuth Token**
```
SLACK_BOT_TOKEN=xoxb-YOUR-TOKEN-HERE
```

## Token 3: App Token
**Socket Mode** → Enable → Create token with `connections:write` → **Generate**
```
SLACK_APP_TOKEN=xapp-YOUR-TOKEN-HERE
```

## Enable Events
**Event Subscriptions** → Enable → Add bot events:
- app_mention
- message.im

Save changes!
