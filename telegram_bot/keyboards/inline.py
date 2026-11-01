"""Inline keyboards and menus for Telegram bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main navigation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Scanner", callback_data="nav:scan"),
            InlineKeyboardButton("📰 News", callback_data="nav:news"),
        ],
        [
            InlineKeyboardButton("🎯 Entry Timer", callback_data="nav:entry"),
            InlineKeyboardButton("🚪 Exit Plan", callback_data="nav:exit"),
        ],
        [
            InlineKeyboardButton("⏳ Time Machine", callback_data="nav:timemachine"),
            InlineKeyboardButton("🛡 Risk Check", callback_data="nav:risk"),
        ],
        [
            InlineKeyboardButton("💰 Trading Budget", callback_data="nav:budget"),
            InlineKeyboardButton("📈 Paper Broker", callback_data="nav:broker"),
        ],
        [
            InlineKeyboardButton("🔔 Price Alerts", callback_data="nav:alerts"),
            InlineKeyboardButton("🏢 SEC Analyst", callback_data="nav:analyst"),
        ],
        [
            InlineKeyboardButton("🏛 Pelosi Tracker", callback_data="nav:pelosi"),
            InlineKeyboardButton("⭐ Watchlist", callback_data="nav:watchlist"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def order_approval_keyboard(approval_id: str) -> InlineKeyboardMarkup:
    """Mandatory order approval / rejection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ APPROVE ORDER", callback_data=f"order_approve:{approval_id}"),
            InlineKeyboardButton("❌ REJECT ORDER", callback_data=f"order_reject:{approval_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def scanner_keyboard() -> InlineKeyboardMarkup:
    """Scanner modes keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🌅 Daily Scan (Closes)", callback_data="scan:daily"),
            InlineKeyboardButton("⚡ 15m ORB Scan", callback_data="scan:orb"),
        ],
        [
            InlineKeyboardButton("⭐ Scan Watchlist", callback_data="scan:watchlist"),
            InlineKeyboardButton("🌐 Nasdaq Universe", callback_data="scan:universe"),
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def symbol_action_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """Quick action buttons for a single stock symbol."""
    sym = symbol.upper()
    keyboard = [
        [
            InlineKeyboardButton("📰 News", callback_data=f"act_news:{sym}"),
            InlineKeyboardButton("🎯 Entry", callback_data=f"act_entry:{sym}"),
        ],
        [
            InlineKeyboardButton("🚪 Exit Plan", callback_data=f"act_exit:{sym}"),
            InlineKeyboardButton("⏳ Time Machine", callback_data=f"act_tm:{sym}"),
        ],
        [
            InlineKeyboardButton("🏢 Analyst (SEC)", callback_data=f"act_analyst:{sym}"),
            InlineKeyboardButton("🛒 Order Preview", callback_data=f"act_order:{sym}"),
        ],
        [
            InlineKeyboardButton("➕ Add Alert", callback_data=f"act_alert:{sym}"),
            InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def broker_menu_keyboard() -> InlineKeyboardMarkup:
    """Broker account management keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("💼 Account Summary", callback_data="broker:account"),
            InlineKeyboardButton("📦 Open Positions", callback_data="broker:positions"),
        ],
        [
            InlineKeyboardButton("📋 Orders Today", callback_data="broker:orders"),
            InlineKeyboardButton("🔄 Sync Broker", callback_data="broker:sync"),
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def alerts_menu_keyboard() -> InlineKeyboardMarkup:
    """Alerts keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📋 List Active Alerts", callback_data="alerts:list"),
            InlineKeyboardButton("🕒 NYSE Market Clock", callback_data="alerts:clock"),
        ],
        [
            InlineKeyboardButton("🔔 Bell & Close Rules", callback_data="alerts:rules"),
            InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
