"""Markdown message formatters for Telegram responses."""

import datetime
from typing import Dict, Any, List, Optional
from utils.ny_time import format_ny_time


def format_start_message(user_name: str) -> str:
    return (
        f"👋 *Welcome to Trade4U Quantitative Trading Bot, {user_name}!*\n\n"
        "⚡ *AN INSTITUTIONAL-GRADE US DAY TRADING ENGINE*\n"
        "High-performance quantitative analysis, real-time SEC intelligence, "
        "and automated bracket execution for NASDAQ & NYSE stocks.\n\n"
        "🔥 *11 CORE QUANT TRADING SKILLS:*\n"
        "1. 📊 *Market Scanner* - 5,900+ US stocks ORB & breakout screener\n"
        "2. 📰 *SEC News Monitor* - Live 8-K filings & breaking catalyst moves\n"
        "3. 🎯 *Entry Timer* - 5-min bar Opening Range Breakout tracking\n"
        "4. 🚪 *Exit Planner* - Mathematical profit targets & stop-losses\n"
        "5. ⏳ *Time Machine* - 10,000 historical Monte Carlo simulations\n"
        "6. 🛡 *Risk Engine* - 15 mandatory pre-trade safety validations\n"
        "7. 💰 *Capital Budget* - Exact mathematical position & risk sizing\n"
        "8. 📈 *Paper Broker* - Alpaca REST client with tamper-proof tickets\n"
        "9. 🔔 *Smart Alerts* - Price targets & NYSE market clock events\n"
        "10. 🏢 *SEC Analyst* - Audited 10-K/10-Q multi-quarter XBRL financials\n"
        "11. 🏛 *Pelosi Tracker* - US Congress public stock disclosures\n\n"
        "🤖 *AUTO-TRADE READY:* Auto-entry, bracket auto-exit & 15:55 flat-by close.\n"
        "🔒 *MODE:* Strict Paper Trading (Zero live-money risk).\n\n"
        "👑 *Owner:* @MeAwara\n\n"
        "Use /menu or tap the buttons below to begin:"
    )


def format_help_message() -> str:
    return (
        "📖 *DAY TRADER TELEGRAM BOT COMMANDS*\n\n"
        "🔹 *General*\n"
        "• /start - Welcome and setup check\n"
        "• /menu - Interactive button dashboard\n"
        "• /status - System, broker, and market status\n"
        "• /settings - View active trading configuration\n"
        "• /watchlist - Manage monitored stocks\n"
        "• /addstock `TICKER` - Add symbol to watchlist\n"
        "• /removestock `TICKER` - Remove symbol\n\n"
        "🔹 *11 Trading Skills*\n"
        "1. `/scan` - Scans charts for daily / ORB setups\n"
        "2. `/news [TICKER]` - Breaking headlines, 8-Ks & movers\n"
        "3. `/entry TICKER` - 5-min ORB entry timer\n"
        "4. `/exit TICKER` - Midpoint stop and target plan\n"
        "5. `/timemachine TICKER` - 10,000 Monte Carlo replays\n"
        "6. `/risk [TICKER]` - 15 pre-trade risk checks\n"
        "7. `/budget [set]` - Position sizing & max loss per trade\n"
        "8. `/broker` - Account balance, positions & orders\n"
        "9. `/alerts` - Price alerts, stop/target & NYSE bell\n"
        "10. `/analyst TICKER` - SEC EDGAR XBRL fundamentals\n"
        "11. `/pelosi` - House Periodic Transaction Reports\n\n"
        "🛒 *Trading & Execution*\n"
        "• `/order TICKER` - Generate and review an order proposal\n"
        "• `/positions` - List open paper positions\n"
        "• `/orders` - Review recent orders"
    )


def format_scanner_message(scan_data: Dict[str, Any]) -> str:
    mode = scan_data.get("mode", "scan").upper()
    hits = scan_data.get("hits", [])
    provider = scan_data.get("provider", "Yahoo Finance")
    timestamp = scan_data.get("timestamp", format_ny_time())

    lines = [
        f"📊 *US MARKET SCANNER ({mode})*",
        f"• *Data Source:* {provider}",
        f"• *Time:* `{timestamp}`",
        f"• *Setups Found:* {len(hits)}",
        ""
    ]

    if not hits:
        lines.append("ℹ️ _No qualifying chart setups found matching criteria._")
        return "\n".join(lines)

    # Show top 5 hits
    for i, h in enumerate(hits[:5], 1):
        sym = h.get("symbol", "N/A")
        price = h.get("price")
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "N/A"
        setups = ", ".join(h.get("setups", [])) if "setups" in h else h.get("setup", "ORB Breakout")
        vol = h.get("volume")
        vol_str = f"{vol:,}" if isinstance(vol, int) else "N/A"

        lines.append(
            f"*{i}. {sym}* - {price_str}\n"
            f"   • Setup: `{setups}`\n"
            f"   • Volume: {vol_str}\n"
            f"   • Action: `/entry {sym}` | `/news {sym}`"
        )

    if len(hits) > 5:
        lines.append(f"\n_...and {len(hits) - 5} more candidate setups._")

    return "\n".join(lines)


def format_news_message(news_data: Dict[str, Any], symbol: Optional[str] = None) -> str:
    title = f"📰 *NEWS & SEC FILINGS: {symbol.upper()}*" if symbol else "📰 *MARKET NEWS & FILINGS*"
    provider = news_data.get("provider", "Yahoo Finance RSS + SEC EDGAR")
    moves = news_data.get("moves", [])
    items = news_data.get("items", [])

    lines = [
        title,
        f"• *Provider:* {provider}",
        ""
    ]

    if moves:
        lines.append("📈 *Today's Moves:*")
        for m in moves[:5]:
            t = m.get("ticker")
            pct = m.get("pct", 0.0)
            sign = "+" if pct >= 0 else ""
            moving = " 🔥 *MOVING*" if m.get("moving") else ""
            p = m.get("price", 0.0)
            lines.append(f"• `{t}`: ${p:.2f} ({sign}{pct:.2f}% vs prev close){moving}")
        lines.append("")

    if items:
        lines.append("📋 *Headlines & 8-K Disclosures:*")
        for item in items[:6]:
            tag_str = f"[{', '.join(item.get('tags', []))}]" if item.get("tags") else ""
            imp = "⚠️ " if item.get("important") else "• "
            t_title = item.get("title", "Headline")
            link = item.get("link", "")
            time_str = item.get("published", "")
            lines.append(f"{imp}*{item.get('ticker', '')}* {tag_str}\n  {t_title}\n  🔗 [Read Filing/Story]({link})")
    else:
        lines.append("ℹ️ _No recent headlines or SEC 8-K filings found._")

    return "\n".join(lines)


def format_entry_message(entry: Dict[str, Any]) -> str:
    sym = entry.get("symbol", "N/A")
    status = str(entry.get("status", "unknown")).upper()
    provider = entry.get("provider", "Yahoo Finance")
    reason = entry.get("reason", "")
    prev_close = entry.get("prev_close")
    next_open = entry.get("next_open")

    if status in ("TRIGGERED", "ACTIVE"):
        status_icon = "🟢"
    elif status in ("WAITING", "FORMING"):
        status_icon = "🟡"
    else:
        status_icon = "🔴"

    lines = [
        f"🎯 *ENTRY TIMER: {sym}*",
        f"• *Status:* {status_icon} `{status}`",
        f"• *Data Source:* {provider}",
        f"• *Time:* `{entry.get('now', format_ny_time())}`",
    ]

    if reason:
        lines.append(f"• *Market Note:* {reason}")
    if next_open:
        lines.append(f"• *Next Market Open:* `{next_open} ET`")
    if prev_close is not None:
        lines.append(f"• *Previous Close:* `${prev_close:.2f}`")

    lines.append("")

    if entry.get("opening_range"):
        rng = entry["opening_range"]
        high = rng.get("high")
        low = rng.get("low")
        high_str = f"${high:.2f}" if high is not None else "N/A"
        low_str = f"${low:.2f}" if low is not None else "N/A"
        lvl = entry.get("level")
        lvl_str = f"${lvl:.2f}" if lvl is not None else "N/A"
        lines.append(
            f"📊 *Opening Range (15m):*\n"
            f"• High: `{high_str}`\n"
            f"• Low: `{low_str}`\n"
            f"• Level to beat: `{lvl_str}`\n"
        )

    if status == "TRIGGERED" and entry.get("trigger"):
        trig = entry["trigger"]
        p = trig.get("price")
        p_str = f"${p:.2f}" if p is not None else "N/A"
        lines.append(
            f"⚡ *Trigger Event:*\n"
            f"• Price: `{p_str}`\n"
            f"• Bar Close Time: `{trig.get('time', 'N/A')}`\n"
            f"• Close above high: `+{trig.get('pct_over', 0.0):.2f}%`\n"
        )
    elif status == "WAITING" and entry.get("last"):
        last = entry["last"]
        close_p = last.get("close")
        close_str = f"${close_p:.2f}" if close_p is not None else "N/A"
        lines.append(
            f"⏳ *Currently Waiting:*\n"
            f"• Last Bar Close: `{close_str}`\n"
            f"• Distance to Level: `{last.get('vs_level_pct', 0.0):.2f}%`\n"
        )

    lines.append(f"👉 Plan exit with `/exit {sym}`")
    return "\n".join(lines)


def format_exit_message(plan: Dict[str, Any]) -> str:
    sym = plan.get("symbol", "N/A")
    lines = [
        f"🚪 *EXIT PLAN: {sym}*",
        f"• *Entry:* `${plan.get('entry', 0.0):.2f}`",
        f"• *Stop-Loss:* `${plan.get('stop', 0.0):.2f}` ({plan.get('stop_label', 'Rule')})",
        f"• *Target:* `${plan.get('target', 0.0):.2f}` ({plan.get('target_label', 'Rule')})",
        f"• *Risk a Share:* `${plan.get('risk_per_share', 0.0):.2f}`",
        f"• *Reward / Risk:* `{plan.get('reward_risk', 0.0):.2f}R`",
        f"• *Flat by Close:* `{plan.get('flat_by', '15:55')} ET`",
        "",
        f"⚠️ _{plan.get('note', 'A stop is a plan, not a guarantee.')}_",
        "",
        f"👉 Run simulation with `/timemachine {sym}`",
        f"👉 Preview paper order with `/order {sym}`"
    ]
    return "\n".join(lines)


def format_timemachine_message(tm: Dict[str, Any]) -> str:
    sym = tm.get("plan", {}).get("symbol") or tm.get("symbol", "N/A")
    verdict = tm.get("verdict", "Simulation complete")
    mc = tm.get("mc", {})
    odds = mc.get("odds", {})
    history = tm.get("history", {})
    provider = tm.get("provider", "Yahoo Finance (60d 5m bars)")

    lines = [
        f"⏳ *TIME MACHINE SIMULATION: {sym}*",
        f"• *Method:* 10,000 Historical Monte Carlo Replays",
        f"• *Data Source:* {provider}",
        f"• *Historical Basis:* TSLA 5-minute bars over prior 60 sessions",
        "",
        f"🎯 *Simulated Odds:*\n"
        f"• Target First: `{odds.get('target', 0.0):.1f}%`\n"
        f"• Stop First: `{odds.get('stop', 0.0):.1f}%`\n"
        f"• Still Open at Close: `{odds.get('neither', 0.0):.1f}%`\n"
        f"• Green at Close: `{odds.get('green', 0.0):.1f}%`\n",
        f"📜 *Real Historical Setup Record:*\n"
        f"• Setup Fired: `{history.get('fired', 0)} times` in 60 days\n"
        f"• Hit Target: `{history.get('target', 0)}` | Hit Stop: `{history.get('stop', 0)}`\n",
        f"⚖️ *Honest Verdict:*",
        f"👉 *{verdict}*",
        "",
        f"⚠️ _Simulation based on past 60 sessions, not a guarantee of future performance._"
    ]
    return "\n".join(lines)


def format_risk_message(risk_data: Dict[str, Any]) -> str:
    results = risk_data.get("results", [])
    cash_after = risk_data.get("cash_after", 0.0)

    lines = [
        "🛡 *PRE-TRADE RISK VALIDATION*",
        f"• *Paper Account:* `YES`",
        f"• *Orders Checked:* {len(results)}",
        ""
    ]

    for i, r in enumerate(results, 1):
        sym = r.get("symbol", "N/A")
        verdict = r.get("verdict", "UNKNOWN")
        icon = "✅" if verdict == "PASS" else "🚫"
        lines.append(f"*{i}. {sym}* - {icon} *{verdict}*")
        if r.get("reasons"):
            for reason in r["reasons"]:
                lines.append(f"   ❌ {reason}")
        if r.get("warnings"):
            for w in r["warnings"]:
                lines.append(f"   ⚠️ {w}")
        lines.append(f"   • Value: `${r.get('value_usd', 0.0):.2f}` | Max Loss: `${r.get('max_loss', 0.0):.2f}`")

    lines.append(f"\n💵 *Projected Cash After:* `${cash_after:.2f}`")
    return "\n".join(lines)


def format_order_preview_message(req: Any) -> str:
    """Format step 3 order approval preview."""
    order_type_str = req.order_type.upper()
    limit_str = f"${req.limit_price:.2f}" if req.limit_price else "N/A (Market Order)"

    return (
        "🚨 *PAPER ORDER REVIEW*\n\n"
        f"• *Symbol:* `{req.symbol}`\n"
        f"• *Side:* `{req.side.upper()}`\n"
        f"• *Quantity:* `{req.qty} shares`\n"
        f"• *Order Type:* `{order_type_str}`\n"
        f"• *Limit Price:* `{limit_str}`\n"
        f"• *Stop-Loss:* `${req.stop_loss:.2f}`\n"
        f"• *Take-Profit:* `${req.take_profit:.2f}`\n"
        f"• *Estimated Notional:* `${req.estimated_notional:.2f}`\n"
        f"• *Maximum Planned Risk:* `${req.max_planned_risk:.2f}`\n"
        f"• *Available Buying Power:* `${req.available_buying_power:.2f}`\n"
        f"• *Time in Force:* `DAY`\n"
        f"• *Account:* `ALPACA PAPER TRADING`\n"
        f"• *Risk Check:* `PASS`\n\n"
        "⚠️ *No order has been submitted yet.*\n"
        "Click below to manually approve or reject this trade.\n"
        "_(Approval request expires in 5 minutes)_"
    )


def format_order_execution_message(exec_data: Dict[str, Any]) -> str:
    """Format step 7 executed paper order confirmation."""
    return (
        "✅ *PAPER ORDER SUBMITTED TO BROKER*\n\n"
        f"• *Broker Order ID:* `{exec_data.get('broker_order_id')}`\n"
        f"• *Symbol:* `{exec_data.get('symbol')}`\n"
        f"• *Side:* `{exec_data.get('side')}`\n"
        f"• *Quantity:* `{exec_data.get('qty')} shares`\n"
        f"• *Status:* `{exec_data.get('status')}`\n"
        f"• *Submission Time:* `{exec_data.get('submitted_at')}`\n"
        f"• *Account:* `{exec_data.get('account_type', 'Alpaca Paper')}`\n\n"
        "ℹ️ _Order has been logged in database. Stop-loss and take-profit legs active._"
    )


def format_broker_account_message(account: Dict[str, Any], positions: List[Dict[str, Any]]) -> str:
    cash = account.get("cash", 0.0)
    bp = account.get("buying_power", 0.0)
    pv = account.get("portfolio_value", 0.0)
    status = account.get("status", "ACTIVE")
    broker_name = account.get("broker", "Alpaca Paper")

    lines = [
        f"📈 *PAPER BROKER ACCOUNT ({broker_name})*",
        f"• *Account Status:* `{status}`",
        f"• *Portfolio Value:* `${pv:,.2f}`",
        f"• *Cash:* `${cash:,.2f}`",
        f"• *Buying Power:* `${bp:,.2f}`",
        f"• *Day Trades Count:* `{account.get('daytrade_count', 0)}`",
        ""
    ]

    if positions:
        lines.append("📦 *Open Positions:*")
        for p in positions:
            sym = p.get("symbol")
            qty = p.get("qty")
            val = p.get("market_value", 0.0)
            pl = p.get("unrealized_pl", 0.0)
            pl_sign = "+" if pl >= 0 else ""
            lines.append(f"• `{sym}`: {qty} shares | Val: `${val:,.2f}` | P&L: `{pl_sign}${pl:.2f}`")
    else:
        lines.append("ℹ️ _No open positions._")

    return "\n".join(lines)


def format_analyst_message(data: Dict[str, Any]) -> str:
    ticker = data.get("ticker", "N/A")
    provider = data.get("provider", "SEC EDGAR")
    result = data.get("result", {})
    filings = data.get("filings", {})
    changes = data.get("changes", [])

    lines = [
        f"🏢 *SEC EARNINGS ANALYST: {ticker}*",
        f"• *Data Source:* {provider}",
        ""
    ]

    if "revenue_ttm" in result:
        rev_ttm = result.get("revenue_ttm", 0.0)
        eps_ttm = result.get("eps_ttm", 0.0)
        lines.append(
            f"📊 *Trailing Twelve Months (TTM):*\n"
            f"• Revenue: `${rev_ttm / 1e9:.2f}B`\n"
            f"• Diluted EPS: `${eps_ttm:.2f}`\n"
        )

    if filings:
        latest_10q = filings.get("latest_10q", {})
        latest_8k = filings.get("latest_8k", {})
        lines.append(
            f"📑 *Latest SEC Filings:*\n"
            f"• 10-Q / 10-K: `{latest_10q.get('form', 'N/A')}` filed `{latest_10q.get('filed', 'N/A')}`\n"
            f"• Earnings 8-K: filed `{latest_8k.get('filed', 'N/A')}`\n"
        )

    if changes:
        lines.append("📝 *Quarterly Changes Summary:*")
        for ch in changes[:3]:
            lines.append(f"• {ch}")

    return "\n".join(lines)


def format_pelosi_message(ptr_list: List[Dict[str, Any]], member: str = "Nancy Pelosi") -> str:
    lines = [
        f"🏛 *CONGRESSIONAL TRADING DISCLOSURES ({member.upper()})*",
        f"• *Source:* US House Clerk Periodic Transaction Reports (STOCK Act)",
        f"• *Disclosures Found:* {len(ptr_list)}",
        ""
    ]

    if not ptr_list:
        lines.append("ℹ️ _No recent periodic transaction reports found on file._")
        return "\n".join(lines)

    for item in ptr_list[:5]:
        doc_id = item.get("doc_id", "N/A")
        filed = item.get("filed", "N/A")
        url = item.get("url", "")
        name = item.get("name", member)
        district = item.get("district", "")

        lines.append(
            f"📄 *Doc #{doc_id}* - `{name} ({district})`\n"
            f"   • Filing Date: `{filed}`\n"
            f"   • Type: Periodic Transaction Report\n"
            f"   • 🔗 [Official House Clerk PDF Filing]({url})"
        )

    lines.append("\n⚠️ _Public filings are reported up to 45 days after execution, not inside information._")
    return "\n".join(lines)
