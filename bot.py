import os
from flask import Flask
from threading import Thread

flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot is alive!"

def run():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Load environment variables from .env file
load_dotenv()

# Get tokens from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
print(f"Key loaded: {GEMINI_KEY is not None}")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_KEY)

# Dictionary to store user profiles and conversation state
user_profiles = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_profiles[user_id] = {"state": "waiting_for_role"}
    
    welcome_message = (
        "Hello! I'm Atlas, your AI Financial Assistant. "
        "To help me assist you better, could you tell me what best describes your role "
        "(e.g., Investor, Analyst, Founder) and which companies or markets you actively follow?"
    )
    await update.message.reply_text(welcome_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # Check if the user is responding during onboarding
    if user_id in user_profiles and user_profiles[user_id].get("state") == "waiting_for_role":
        user_profiles[user_id]["role"] = user_text
        user_profiles[user_id]["state"] = "active"
        
        reply_text = (
            f"Got it! Thanks for sharing. I have noted your focus ({user_text}). "
            f"How can I help you with your financial analysis today?"
        )
        await update.message.reply_text(reply_text)
        return

    # Get user role for customized financial guidance
    user_role = user_profiles.get(user_id, {}).get("role", "Finance Professional")

    try:
        # Generate content using the new Gemini client method with system instructions
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=user_text,
            config={
                'system_instruction': (
                    f"You are Atlas, an expert AI Financial Assistant. "
                    f"The user is a {user_role}. "
                    f"Provide concise, accurate, and actionable financial insights naturally."
                )
            }
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error occurred: {e}")
        await update.message.reply_text(f"Error: {e}")

if __name__ == '__main__':
    # Build and run the Telegram application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot is running...")
    keep_alive()
    app.run_polling()