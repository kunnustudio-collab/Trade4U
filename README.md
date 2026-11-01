# The Day Trader skill

11 Claude skills for day trading: scan thousands of charts, track breaking news, time every entry and exit, and replay every outcome before you risk a dollar.

Free, MIT, no signup, no API key. The tools are plain Python that read free
public data: Yahoo Finance charts, Nasdaq Trader's symbol lists, SEC EDGAR
and the House Clerk.

One scans thousands of charts for setups. Another tracks breaking news on
every stock you watch. One watches a setup bar by bar and tells you the moment
to get in, and another sets your stop and your target before you do. And the
craziest one is the Time Machine: before you risk a dollar, it replays the
rest of the session 10,000 times from the stock's own recent bars, plus every
past day the same setup fired, and tells you the honest odds.

And no trade goes through until you say yes. Nothing in this pack can place
an order on its own. Paper trading is the default.

> **Looking for the original Trader skill?** Copy an investor's 13F, the
> stock screener, tax lots and rebalancing live in
> [github.com/Jakeschincariol/trader-skill](https://github.com/Jakeschincariol/trader-skill).
> This repo is its day-trading sequel: the Trader skill v2.

## Install

Paste this into Claude:

```
https://github.com/Jakeschincariol/day-trader-skill

install skill
```

Or as a plugin, in Claude Code:

```
/plugin marketplace add Jakeschincariol/day-trader-skill
/plugin install day-trader-skill@day-trader-skill
```

Claude Code namespaces plugin skills, so installed as a plugin they show up as
`/day-trader-skill:trader-scanner` and so on. Copy the folders instead if you want
plain `/trader-scanner`:

```bash
git clone https://github.com/Jakeschincariol/day-trader-skill.git
cp -r day-trader-skill/trader-* ~/.claude/skills/
```

Project-local instead of global: copy the same folders into your repo's
`.claude/skills/`. No Claude Code at all? Paste any single `SKILL.md` at the
top of a chat and it runs as a mode. You lose the Python tools, but the method
works.

The tools need Python 3.8 or newer. Nothing to pip install. The SEC tools
(news filings, the analyst) ask you to identify yourself: put your name and
email in `trader/config.json` (`"sec_user_agent": "Your Name you@example.com"`)
or in the `SEC_USER_AGENT` environment variable.

## The eleven

| command | job | what it does |
| --- | --- | --- |
| `/trader-scanner` | Chart Scanner | Scans thousands of charts for setups: opening-range breakouts, flags, oversold bounces. |
| `/trader-news` | News Monitor | Tracks breaking news on every stock you watch and flags what moves it. |
| `/trader-entry` | Entry Timer | Watches a setup bar by bar and tells you the moment to get in. |
| `/trader-exit` | Exit Planner | Sets your stop and your target before you enter, so you know when to get out. |
| `/trader-timemachine` | Time Machine | Replays every possible outcome of a trade before you risk a dollar: 10,000 simulated sessions plus every past time the setup fired. |
| `/trader-risk` | Risk Manager | Checks every trade against your limits and stops anything over them. |
| `/trader-budget` | Budget Manager | Sizes every position to your budget and your max loss per trade. |
| `/trader-broker` | Order Executor | Sends approved orders to your broker, paper trading by default, never without your yes. |
| `/trader-alerts` | Price Alerts | Rings when a price, a stop or the opening bell hits. |
| `/trader-analyst` | Earnings Analyst | Reads earnings reports and sums up what changed. |
| `/trader-pelosi` | Pelosi Tracker | Reads Congress's stock-trade disclosures the minute they are filed. |

## How to use it

Everything lands in a `trader/` folder in your project, and each skill reads
what the last one wrote:

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker   (one trade)
alerts: stop, target, flat by the close                                       (while it is open)
news / analyst / pelosi                                                        (on a schedule)
```

An example, the trade in the reel: Tesla, Monday October 19 2026, real data.

1. **`/trader-scanner`** at 10:15 AM ET: of the 231 charts in the reel's
   scan, 42 had closed above their 15-minute opening range. TSLA is one: range 354.47 to 362.18,
   the 10:10 candle closed at 364.18, 0.55 % over the top.
2. **`/trader-news`**: the morning's TSLA headlines, in New York time
   ("Tesla-SpaceX Merger Mania Strikes Wall Street Ahead of Earnings", 8:04,
   tagged earnings and deal). Tesla reports this week: a day trade is out
   before the close, so it is not exposed to the report.
3. **`/trader-entry`** watched TSLA bar by bar. At 10:12 it said waiting (the
   10:10 bar was still forming). At 10:15 it said triggered: the first
   5-minute close above the range, 364.18.
4. **`/trader-exit`** set the plan before the entry: stop at the range's
   midpoint, 358.32, so 5.86 a share at risk; target one times that risk,
   370.04; flat by 3:55 PM either way.
5. **`/trader-timemachine`** replayed the rest of the day 10,000 times, each
   5-minute candle drawn from TSLA's own candles at that time of day over the
   previous 59 sessions (seed 19, so anyone can repeat it): target first
   29.4 %, stop first 25.5 %, still open at the close 45.1 %. It also re-ran
   the same rule on those 59 real sessions: it fired 33 times, 13 hit the
   target, 15 the stop, 5 neither. Its verdict: close to a coin flip. That is
   the point of looking before you risk a dollar.
6. **`/trader-budget`** with a $5,000 account and a $50 max loss per trade:
   50 / 5.86 = 8 shares ($2,913.44). If the stop fills at 358.32, the loss is
   $46.88. It writes one bracket order: buy 8 TSLA, stop-loss 358.32,
   take-profit 370.04.
7. **`/trader-risk`** checks it against your limits: the max loss, the daily
   loss limit, trades per day, reward to risk, the entry window, position
   size and cash. PASS or BLOCK, with the reason.
8. **`/trader-broker`** shows you the ticket in plain words. You type yes for
   that exact order. Claude calls your brokerage connector (Alpaca's MCP
   server, paper account by default), and Claude's own "Allow once / Deny"
   card asks you one more time.
9. **`/trader-alerts`** rings on the stop, the target and at 3:55 PM to
   flatten whatever is still open.

## The tools

All standard-library Python. The data tools read public endpoints and are
polite about it.

```bash
python3 trader-scanner/scan.py universe                                # ~5,900 US stocks, Nasdaq Trader
python3 trader-scanner/scan.py daily                                   # pre-market setups, whole universe
python3 trader-scanner/scan.py orb --at 10:15                          # opening-range breakouts so far
python3 trader-news/news.py --tickers TSLA --hours 12                  # headlines, 8-Ks, today's move
python3 trader-entry/entry.py check TSLA --setup orb                   # waiting / triggered / expired
python3 trader-entry/entry.py watch TSLA --every 30                    # bar by bar until it triggers
python3 trader-exit/exit.py plan --stop or-mid --target 1R --write     # -> trader/plan.json
python3 trader-timemachine/timemachine.py run --write                  # 10,000 replays + the history
python3 trader-budget/size.py --write                                  # -> trader/orders.json
python3 trader-risk/check.py                                           # PASS / BLOCK per order
python3 trader-broker/ticket.py show                                   # the tickets, READY or not
python3 trader-alerts/alerts.py add --from-plan                        # stop, target, flat by close
python3 trader-alerts/alerts.py check                                  # rings what hit, once
python3 trader-analyst/facts.py TSLA                                   # quarters, growth, EPS
python3 trader-pelosi/ptr.py index --member pelosi                     # her PTRs this year
```

```bash
python3 -m unittest discover -s tests -v
```

The tests run offline, on fixtures cut from real data: TSLA's 5-minute bars
for the 60 days to October 19 2026, the 10:15 AM opening-range scan, Yahoo's
TSLA headlines that morning, the House Clerk's 2026 index, real PTR text and
real XBRL facts. They reproduce every number in the example above.

## Fine print

**Not financial advice.** This is software that reads public data and does
arithmetic. It does not know your situation and it cannot see the future.
Most people who day trade lose money. You can lose money. Decide for
yourself, and talk to a licensed professional if you need advice.

**No trade goes through until you say yes.** Only `/trader-broker` can lead to
an order, and only after `/trader-risk` passes that exact order and you type
yes for it in the chat. Set your brokerage tool to "Needs approval" in Claude
(Customize, Connectors, tool permissions), never "Always allow", so Claude's
own "Allow once / Deny" card is a second check. No options, margin, short
selling or leverage unless you turn them on.

**Paper first.** `"paper": true` is the default in `config.example.json`, and
Alpaca's MCP server defaults to its paper account. Keys live in environment
variables, never in the chat.

**The Time Machine is a simulation, not a prediction.** It is built from the
stock's own last 60 days of 5-minute bars. The future can do things those 60
days never did: an earnings report, a halt, a headline. Treat its odds as a
reality check, never as a promise.

**A stop is a plan, not a guarantee.** In a fast market or across a gap, a
stop order can fill well past its price. The max loss shown is the loss at
the stop price.

**The data is free and unofficial.** Yahoo Finance's chart endpoint is not an
official API: it can lag, change or rate-limit you. The scanner and the entry
timer read 1-minute or 5-minute bars, not every tick. Check anything that
matters against your broker before you act on it.

**Day-trading rules.** FINRA removed the $25,000 pattern-day-trader minimum
on June 4, 2026 (Regulatory Notice 26-10), and brokers may phase the change
in until October 20, 2027, so yours may still apply the old rule. If it does,
set `"pdt_guard": true` and `/trader-risk` counts your day trades.

**Congress's trades are public, not inside information.** Members must disclose
trades over $1,000 within 45 days (the STOCK Act). The Pelosi skill reads those
public filings the minute they post.

**Taxes.** Day-trading gains are short-term gains, and frequent trading makes
wash sales likely. Nothing here is tax advice.

## Files

```
trader-scanner/     SKILL.md, scan.py
trader-news/        SKILL.md, news.py
trader-entry/       SKILL.md, entry.py
trader-exit/        SKILL.md, exit.py
trader-timemachine/ SKILL.md, timemachine.py
trader-risk/        SKILL.md, check.py
trader-budget/      SKILL.md, size.py, config.example.json, targets.example.json
trader-broker/      SKILL.md, ticket.py, claude_desktop_config.example.json
trader-alerts/      SKILL.md, alerts.py, alerts.example.json
trader-analyst/     SKILL.md, facts.py, metrics.example.json
trader-pelosi/      SKILL.md, ptr.py
tests/              unittest suite + offline fixtures
telegram_bot/       Telegram bot handlers, keyboards, formatters, and auth
core/               Adapters for all 11 skills
services/           Broker adapter, approval service, alert & scheduler services
database/           Async SQLite database models and repository
config/             Pydantic settings and security validators
run_bot.py          Main bot application entrypoint
```

---

# Day Trader Telegram Assistant (Production Edition)

A complete conversion of the 11 original trading skills into a fully functional, production-grade Telegram assistant for US stock markets (NASDAQ, NYSE, TSLA, NVDA, AAPL, MSFT, AMZN, and broader universe).

## 1. Key Features
- **All 11 Skills Integrated**: Chart scanner, breaking news and 8-Ks, bar-by-bar entry timer, midpoint stop and target exit planner, 10,000-run Monte Carlo time machine, 15 pre-trade risk checks, budget position sizing, Alpaca paper trading executor, price/clock alerts, SEC EDGAR XBRL fundamentals, and House congressional trade disclosures.
- **Strict Security & Paper Trading Only**: Operates strictly in paper trading mode (`https://paper-api.alpaca.markets`). Live broker endpoints are blocked.
- **Mandatory Order Approval System**: Every order requires individual manual approval via interactive Telegram buttons (`[ APPROVE ORDER ]` / `[ REJECT ORDER ]`). Auto-execution is prohibited.
- **Idempotency & Re-validation**: Orders expire after 5 minutes (TTL), verify user authorization, reject duplicate submissions, and re-run all 15 risk checks at approval time.
- **Persistent SQLite Database**: Stores watchlists, custom budgets, risk limits, pending approval previews, executed paper orders, and alerts across restarts.
- **Market Hours Scheduler**: Background scheduler operating in `America/New_York` timezone for opening bell, price checks, breaking news, and flat-by-close reminders.

## 2. Requirements & Installation

- Python 3.10+ (compatible with 3.8+)
- SQLite3

```bash
# Clone or navigate to the repository
cd day-trader-skill-main

# Create virtual environment
python -m venv .venv
# Activate:
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

## 3. Configuration & Environment Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

1. **Telegram Bot Token**: Create a bot via `@BotFather` on Telegram and copy the token:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ```

2. **Authorized Telegram User IDs**:
   Open Telegram and message `@userinfobot` to retrieve your numeric User ID:
   ```env
   AUTHORIZED_TELEGRAM_USER_IDS=123456789
   ```

3. **Alpaca Paper Trading API Keys**:
   Sign in to your free Alpaca dashboard at `https://alpaca.markets`, switch to Paper Trading, and generate API keys:
   ```env
   ALPACA_API_KEY=your_paper_key_here
   ALPACA_SECRET_KEY=your_paper_secret_here
   ALPACA_BASE_URL=https://paper-api.alpaca.markets
   PAPER_TRADING_ONLY=true
   ```

4. **SEC EDGAR User Agent**:
   Required by the SEC for free EDGAR API access (Format: `Name email@example.com`):
   ```env
   SEC_USER_AGENT=DayTraderBot your_email@domain.com
   ```

## 4. Running the Bot

```bash
python run_bot.py
```

The bot will initialize the SQLite database, verify configuration security, start the market scheduler, and begin polling Telegram.

## 5. Telegram Commands Reference

### General Commands
- `/start` - Start bot and check user authorization
- `/help` - View complete command manual
- `/menu` - Interactive dashboard with inline buttons
- `/status` - Market hours, NYSE calendar status, and broker connection
- `/settings` - View active trading budget and risk limits
- `/watchlist` - View monitored stocks
- `/addstock TICKER` - Add symbol to watchlist (e.g. `/addstock TSLA`)
- `/removestock TICKER` - Remove symbol from watchlist

### 11 Core Trading Skills
1. `/scan` - Chart scanner menu (`/scan daily`, `/scan orb`, `/scan breakout`, `/scan momentum`, `/scan watchlist`)
2. `/universe` - Query Nasdaq Trader directories (~5,900 US common stocks & ADRs)
3. `/news [TICKER]` - Breaking headlines, today's price move, and SEC 8-K filings
4. `/entry TICKER` - Intraday 15-minute Opening Range Breakout (ORB) entry timer
5. `/watch TICKER` - Monitor symbol bar-by-bar until breakout triggers
6. `/unwatch TICKER` - Stop monitoring symbol
7. `/exit [plan] TICKER` - Calculate opening-range midpoint stop and 1R/2R target
8. `/timemachine TICKER` - Run 10,000 historical Monte Carlo simulations and rule backtest
9. `/risk [TICKER]` - Evaluate 15 pre-trade risk checks
10. `/budget [status|set]` - View and configure capital, position caps, and max loss per trade
11. `/broker` - Account balance, buying power, open positions, and orders
12. `/positions` - List currently open paper positions
13. `/orders` - Review recent orders on broker
14. `/order TICKER` - Generate an order proposal with manual approval buttons
15. `/alerts` - Manage price, stop, target, and NYSE opening bell alerts
16. `/analyst TICKER` - SEC EDGAR XBRL company facts, revenue, margins, and EPS growth
17. `/pelosi` - House Periodic Transaction Reports under the STOCK Act

## 6. Mandatory Order Approval Workflow

To ensure total capital protection, the system executes trades through 8 strict steps:
1. **Signal**: Identified via scanner or `/order TICKER`.
2. **Risk Check**: Sized by Budget Manager and validated by Risk Manager against 15 rules.
3. **Order Preview**: Interactive Telegram card displaying symbol, side, shares, price, stop loss, take profit, notional value, and max risk.
4. **Manual Approval**: Two inline buttons presented: `[ APPROVE ORDER ]` and `[ REJECT ORDER ]`.
5. **Approval Validation**: Verifies authorizing user ID, 5-minute expiration TTL, idempotency (no double submissions), and re-runs risk checks.
6. **Execution**: Dispatched to Alpaca Paper Trading API.
7. **Confirmation**: Sends live broker order ID, status, and fill details to Telegram.
8. **Persistence**: Saves order and execution state to SQLite database.

## 7. Automated Testing

Run the complete test suite (357 tests including all 315 original skill tests):

```bash
python -m unittest discover -s tests -v
```

MIT. Made by [Jake Schincariol](https://opusjake.ai).
