#!/usr/bin/env python3
"""
Script to get your Telegram chat_id

This script helps you get your Telegram chat_id, which is needed
for sending messages and files via Telegram bot.

Process:
1. Starts temporary Telegram bot
2. Waits for message from user
3. Shows user's chat_id
4. Sends chat_id to Telegram

Usage:
    python scripts/get_my_chat_id.py

Requirements:
    - TELEGRAM_BOT_TOKEN set in config.py
    - python-telegram-bot library installed

Example result:
    ============================================================
    🔍 GETTING TELEGRAM CHAT_ID
    ============================================================
    
    1. Open Telegram
    2. Find bot @tabsage_bot
    3. Send it any message (e.g.: /start)
    4. Script will show your chat_id
    
    ⏳ Waiting for message...
    
    ✅ Your chat_id: 123456789
       Name: John
    
    💡 Now you can use:
       export TELEGRAM_CHAT_ID=123456789
       or
       python scripts/send_audio_to_telegram.py <audio_file> 123456789
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for importing project modules

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from core.config import TELEGRAM_BOT_TOKEN


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Message handler for getting chat_id
    
    When user sends message to bot, this handler:
    1. Extracts chat_id from message
    2. Shows chat_id in console
    3. Sends chat_id to user in Telegram
    4. Stops bot
    """
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "User"
    username = update.effective_user.username or "N/A"
    
    print("\n" + "=" * 70)
    print("✅ Chat ID received!")
    print("=" * 70)
    print(f"\n👤 User information:")
    print(f"   Name: {user_name}")
    print(f"   Username: @{username}")
    print(f"   Chat ID: {chat_id}")
    print()
    print("=" * 70)
    print("💡 How to use chat_id:")
    print("=" * 70)
    print()
    print("Option 1: Set environment variable")
    print(f"   export TELEGRAM_CHAT_ID={chat_id}")
    print()
    print("Option 2: Pass as argument")
    print(f"   python scripts/send_audio_to_telegram.py <audio_file> {chat_id}")
    print()
    print("Option 3: Use in code")
    print(f"   chat_id = {chat_id}")
    print()
    print("=" * 70)
    print("👋 Script completed. Bot stopped.")
    print("=" * 70)
    
    # Send chat_id to user in Telegram
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Your chat_id: `{chat_id}`\n\n"
             f"Use it to send audio files via TabSage scripts.\n\n"
             f"Example:\n"
             f"```bash\n"
             f"export TELEGRAM_CHAT_ID={chat_id}\n"
             f"python scripts/send_audio_to_telegram.py audio.mp3\n"
             f"```",
        parse_mode="Markdown"
    )
    
    # Stop bot after getting chat_id
    context.application.stop()


def main():
    """
    Main function - starts temporary Telegram bot to get chat_id
    
    Process:
    1. Creates Telegram bot
    2. Sets up message handlers
    3. Starts polling to receive messages
    4. On receiving message shows chat_id and stops
    """
    print("=" * 70)
    print("🔍 GETTING TELEGRAM CHAT_ID")
    print("=" * 70)
    print()
    print("This script will help you get your Telegram chat_id.")
    print("Chat ID is needed for sending messages and files via bot.")
    print()
    print("📋 Instructions:")
    print("   1. Open Telegram on your device")
    print("   2. Find bot @tabsage_bot (or use token from config.py)")
    print("   3. Send bot any message (e.g.: /start or 'Hello')")
    print("   4. Script will automatically show your chat_id")
    print()
    print("💡 Tips:")
    print("   - If bot doesn't respond, check TELEGRAM_BOT_TOKEN in config.py")
    print("   - Chat ID is unique for each user")
    print("   - Save chat_id for use in other scripts")
    print()
    print("-" * 70)
    print()
    print("⏳ Waiting for message from user...")
    print("   (Press Ctrl+C to cancel)")
    print()
    
    # Create Telegram bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Set up message handlers
    # Handle both text messages and commands
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.COMMAND, handle_message))
    
    try:
        # Start polling to receive messages
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("👋 Bot stopped by user")
        print("=" * 70)
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ Error: {e}")
        print("=" * 70)
        print()
        print("💡 Troubleshooting:")
        print("   - Check TELEGRAM_BOT_TOKEN in config.py")
        print("   - Make sure token is valid")
        print("   - Check internet connection")


if __name__ == "__main__":
    main()

