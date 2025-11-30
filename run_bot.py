"""Launch Telegram bot"""

import asyncio
import os
import logging
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from services.bot.telegram_bot import main

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/healthz' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logging

def start_health_server():
    """Start HTTP server for Cloud Run health checks"""
    port = int(os.getenv('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server listening on port {port}")
    print(f"Health check server listening on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    logger.info("Starting TabSage Telegram Bot...")
    print("Starting TabSage Telegram Bot...")
    print("Bot: @tabsage_bot")
    print()
    
    # Start health check server in background thread FIRST
    health_thread = Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Wait a bit for health server to start
    time.sleep(1)
    logger.info("Health check server started, starting bot...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
        print("\nBot stopped")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        raise

