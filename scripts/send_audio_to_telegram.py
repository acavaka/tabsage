#!/usr/bin/env python3
"""
Script to send audio file via Telegram bot

This script sends audio file (e.g., generated podcast)
to user via Telegram bot.

Usage:
    python scripts/send_audio_to_telegram.py <audio_file_path> [chat_id]
    
Examples:
    # With chat_id from environment variable
    export TELEGRAM_CHAT_ID=123456789
    python scripts/send_audio_to_telegram.py audio_summary.mp3
    
    # With chat_id as argument
    python scripts/send_audio_to_telegram.py audio_summary.mp3 123456789
    
    # Get chat_id via:
    python scripts/get_my_chat_id.py

Requirements:
    - TELEGRAM_BOT_TOKEN set in config.py
    - python-telegram-bot library installed
    - File exists and is readable

Example result:
    📤 Sending audio file...
       File: audio_summary_20251129.mp3
       Size: 5.23 MB
       Chat ID: 123456789
    ✅ Audio successfully sent!
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path

from telegram import Bot
from core.config import TELEGRAM_BOT_TOKEN
from observability.logging import get_logger

logger = get_logger(__name__)


async def send_audio_file(audio_path: str, chat_id: str = None):
    """
    Sends audio file via Telegram bot
    
    Args:
        audio_path: Path to audio file to send
        chat_id: Telegram chat ID of recipient (optional, can be taken from TELEGRAM_CHAT_ID)
    
    Returns:
        True on successful send, False on error
    """
    # Check file existence
    if not os.path.exists(audio_path):
        print(f"❌ File not found: {audio_path}")
        print()
        print("💡 Check:")
        print("   - File path correctness")
        print("   - That file exists")
        print("   - File access permissions")
        return False
    
    # Get chat_id
    # First check argument, then environment variable
    if not chat_id:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not chat_id:
            print("❌ chat_id not specified")
            print()
            print("💡 Solutions:")
            print("   1. Set environment variable:")
            print("      export TELEGRAM_CHAT_ID=your_chat_id")
            print()
            print("   2. Pass chat_id as argument:")
            print(f"      python scripts/send_audio_to_telegram.py {audio_path} <chat_id>")
            print()
            print("   3. Get chat_id via:")
            print("      python scripts/get_my_chat_id.py")
            return False
    
    try:
        # Create bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Get file information
        file_size_bytes = os.path.getsize(audio_path)
        file_size_mb = file_size_bytes / (1024 * 1024)  # Size in MB
        file_name = Path(audio_path).name
        
        print("=" * 70)
        print("📤 Sending audio file via Telegram")
        print("=" * 70)
        print()
        print("📁 File information:")
        print(f"   File: {file_name}")
        print(f"   Size: {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")
        print(f"   Chat ID: {chat_id}")
        print()
        print("⏳ Sending...")
        
        # Send audio file
        with open(audio_path, "rb") as audio_file:
            await bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                title=file_name.replace(".mp3", "").replace("_", " "),
                performer="TabSage AI"
            )
        
        print()
        print("=" * 70)
        print("✅ Audio successfully sent!")
        print("=" * 70)
        print()
        print("💡 File sent to user in Telegram")
        return True
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Error sending: {e}")
        print("=" * 70)
        print()
        print("💡 Troubleshooting:")
        print("   - Check TELEGRAM_BOT_TOKEN in config.py")
        print("   - Make sure chat_id is correct")
        print("   - Check file size (Telegram limits to 50 MB)")
        print("   - Check internet connection")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/send_audio_to_telegram.py <audio_file_path> [chat_id]")
        print()
        print("Examples:")
        print("  python scripts/send_audio_to_telegram.py ~/Downloads/audio_summary_*.mp3")
        print("  python scripts/send_audio_to_telegram.py ~/Downloads/audio_summary_*.mp3 123456789")
        print()
        print("Or set TELEGRAM_CHAT_ID:")
        print("  export TELEGRAM_CHAT_ID=your_chat_id")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    chat_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = await send_audio_file(audio_path, chat_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

