#!/usr/bin/env python3
"""Main entry point to start the Day Trader Telegram Bot."""

import asyncio
import logging
import os
import sys
from config.settings import settings
from utils.logging_setup import setup_logging
from database.database import init_db
from telegram_bot.bot import build_application
from services.scheduler_service import SchedulerService


async def main():
    # 1. Setup secure logging with secret redaction
    secrets = [settings.TELEGRAM_BOT_TOKEN, settings.ALPACA_API_KEY, settings.ALPACA_SECRET_KEY]
    logger = setup_logging(level=settings.LOG_LEVEL, secrets=secrets)
    logger.info("Starting Day Trader Telegram Bot...")

    # 2. Strict Security Check
    if not settings.PAPER_TRADING_ONLY:
        logger.critical("SECURITY VIOLATION: PAPER_TRADING_ONLY must be True. Live trading is strictly blocked.")
        sys.exit(1)

    if "paper" not in settings.ALPACA_BASE_URL.lower():
        logger.critical("SECURITY VIOLATION: Non-paper Alpaca URL detected: %s", settings.ALPACA_BASE_URL)
        sys.exit(1)

    logger.info("Security verified: Paper trading mode active. Broker: %s", settings.ALPACA_BASE_URL)

    # 3. Initialize SQLite Database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully.")

    # 4. Check Telegram Bot Token
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning(
            "TELEGRAM_BOT_TOKEN is not set in .env! "
            "Please copy .env.example to .env and configure your bot token and authorized user IDs."
        )
        print("\n" + "=" * 60)
        print(" DAY TRADER TELEGRAM BOT - SETUP NOTICE")
        print("=" * 60)
        print("TELEGRAM_BOT_TOKEN is not configured in .env.")
        print("1. Open .env and add your TELEGRAM_BOT_TOKEN from @BotFather.")
        print("2. Add your Telegram user ID to AUTHORIZED_TELEGRAM_USER_IDS.")
        print("3. Re-run: python run_bot.py\n")
        sys.exit(1)

    # 5. Build Bot Application
    app = build_application()

    # 6. Start Background Market Scheduler
    scheduler = SchedulerService(bot_app=app)
    scheduler.start()

    logger.info("Authorized Telegram User IDs: %s", settings.get_authorized_user_ids() or "(None configured yet)")
    logger.info("Bot is polling for updates. Press Ctrl+C to stop.")

    # 7. Start Healthcheck Server for Cloud Hosts (Render, Railway, Heroku) if PORT is set
    health_server = None
    port_env = os.environ.get("PORT")
    if port_env:
        try:
            port = int(port_env)

            async def handle_health_check(reader, writer):
                await reader.read(1024)
                resp = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK"
                writer.write(resp)
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            health_server = await asyncio.start_server(handle_health_check, "0.0.0.0", port)
            logger.info("Cloud deployment health server listening on port %d", port)
        except Exception as e:
            logger.warning("Could not start cloud health server on port %s: %s", port_env, e)

    try:
        # Run polling loop
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        # Keep running until cancelled
        while True:
            await asyncio.sleep(3600)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Stopping bot gracefully...")
    finally:
        if health_server:
            health_server.close()
            await health_server.wait_closed()
        scheduler.stop()
        if app.updater and app.updater.running:
            await app.updater.stop()
        if app.running:
            await app.stop()
        await app.shutdown()
        logger.info("Day Trader Telegram Bot stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot process terminated by user.")
