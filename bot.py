import os
import logging
import asyncio
import threading
import sys
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# --- CONFIGURATION ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", 8080))

if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN environment variable is not set!")
    sys.exit(1)

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MOTIVATIONAL DATA ---
QUOTES_HARD_WORK = [
    "Work hard in silence, let your success be your noise.",
    "The only place where success comes before work is in the dictionary.",
    "Opportunities are usually disguised as hard work, so most people don't recognize them.",
    "Don't stop when you're tired. Stop when you're done."
]

QUOTES_FUTURE = [
    "The best way to predict the future is to create it.",
    "Your future is created by what you do today, not tomorrow.",
    "Work now, enjoy tomorrow. Freedom is earned through discipline.",
    "The pain of discipline is far less than the pain of regret."
]

DEFAULT_REMINDER_TEXT = "Don't be lazy! Work now retire soon. Work now and enjoy tomorrow. Work today and gain tomorrow's freedom! 🔥"

# --- BOT LOGIC ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets the user and sets up the automatic 3-hour cycle."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Remove existing jobs for this user to avoid duplicates
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()

    # Schedule the 3-hour recurring "Don't be lazy" notification
    context.job_queue.run_repeating(
        send_auto_reminder, 
        interval=timedelta(hours=3), 
        first=10, # First one in 10 seconds
        chat_id=chat_id, 
        name=str(chat_id)
    )

    welcome_text = (
        f"Welcome {user.first_name}! 🚀\n\n"
        "I am your Productivity Guardian. I will haunt you every 3 hours to ensure you aren't procrastinating.\n\n"
        "**Current Status:** Automatic 3-hour reminders are ACTIVE.\n\n"
        "Need a specific nudge? Use the buttons below:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🕒 30 Min: Task Check", callback_data="remind_30m")],
        [InlineKeyboardButton("💪 1 Hr: Hard Work Nudge", callback_data="remind_1h")],
        [InlineKeyboardButton("🌅 3 Hrs: Future Vision", callback_data="remind_3h")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_auto_reminder(context: ContextTypes.DEFAULT_TYPE):
    """The recurring 3-hour notification."""
    job = context.job()
    await context.bot.send_message(
        chat_id=job.chat_id, 
        text=DEFAULT_REMINDER_TEXT,
        reply_markup=get_main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles custom reminder requests."""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    data = query.data

    if data == "remind_30m":
        seconds = 30 * 60
        msg = "Roger that. I'll check if you've completed your task in 30 minutes. Get to it! ⏱️"
        context.job_queue.run_once(alarm_30m, seconds, chat_id=chat_id)
        
    elif data == "remind_1h":
        seconds = 60 * 60
        msg = "One hour timer set. Prepare for a hard work quote. Focus! 🧠"
        context.job_queue.run_once(alarm_1h, seconds, chat_id=chat_id)
        
    elif data == "remind_3h":
        seconds = 3 * 60 * 60
        msg = "Three hour timer set. I'll remind you of the future you're building. 🏗️"
        context.job_queue.run_once(alarm_3h, seconds, chat_id=chat_id)

    await query.edit_message_text(f"{query.message.text}\n\n✅ **{msg}**", parse_mode='Markdown', reply_markup=get_main_keyboard())

# --- ALARM CALLBACKS ---

async def alarm_30m(context: ContextTypes.DEFAULT_TYPE):
    job = context.job()
    await context.bot.send_message(job.chat_id, "🔔 **CHECK-IN:** Have you completed today's task? No excuses!", parse_mode='Markdown')

async def alarm_1h(context: ContextTypes.DEFAULT_TYPE):
    import random
    job = context.job()
    quote = random.choice(QUOTES_HARD_WORK)
    await context.bot.send_message(job.chat_id, f"💪 **HARD WORK NUDGE:**\n\n\"{quote}\"", parse_mode='Markdown')

async def alarm_3h(context: ContextTypes.DEFAULT_TYPE):
    import random
    job = context.job()
    quote = random.choice(QUOTES_FUTURE)
    await context.bot.send_message(job.chat_id, f"🌅 **FUTURE VISION:**\n\n\"{quote}\"\n\nWork now and enjoy tomorrow!", parse_mode='Markdown')

# --- RENDER HEALTH CHECK ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Productivity Bot is active")
    def log_message(self, format, *args): return

def run_health_check():
    httpd = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    httpd.serve_forever()

# --- MAIN ---
async def main():
    threading.Thread(target=run_health_check, daemon=True).start()
    
    # Initialize application with JobQueue
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))

    async with application:
        await application.initialize()
        await application.start()
        logger.info(f"Productivity Bot started on port {PORT}")
        await application.updater.start_polling()
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot offline.")
