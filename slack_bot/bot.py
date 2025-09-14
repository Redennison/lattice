import ssl
import certifi
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from config import SLACK_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET
from handlers import handle_app_mention

# Create SSL context with proper certificate verification
ssl_context = ssl.create_default_context(cafile=certifi.where())

web_client = WebClient(
    token=SLACK_TOKEN,
    ssl=ssl_context
)

app = App(
    client=web_client,
    signing_secret=SLACK_SIGNING_SECRET
)

# Register event handlers
app.event("app_mention")(handle_app_mention)

if __name__ == "__main__":
    # Start the bot
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
