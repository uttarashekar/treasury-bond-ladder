# Treasury Bond Ladder Agent

An AI-powered tool to plan and execute a **$100K treasury bond ladder** using U.S. Treasury Bills. It splits your investment into 10 monthly purchases of 52-week T-Bills so that starting ~12 months later, one bond matures each month returning ~$10K + interest.

## What It Does

- **Generates a bond ladder plan** — 10 batches × $10K face value, staggered monthly
- **Verifies all math with Python** — independent checks on every discount, price, and interest calculation
- **Gives you exact purchase instructions** — security type, term, amount, and step-by-step form fields for TreasuryDirect.gov
- **Sends monthly email reminders** — HTML emails with everything you need to buy that month's bond
- **Interactive AI agent** (optional) — chat with Claude to ask questions about your plan

## Quick Start

### Option 1: Run Locally with Claude CLI (No Setup Required)

If you have [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed, you can use it directly in this project directory without any API keys or email configuration:

```bash
git clone https://github.com/uttarashekar/treasury-bond-ladder.git
cd treasury-bond-ladder
```

Then just open Claude Code and ask it questions:

```bash
claude

# Inside Claude Code, try:
# "Run buy_now.py --plan and show me my full investment plan"
# "Run buy_now.py 2026-05 and tell me what to buy in May"
# "Run planner.py and verify the math"
```

Claude Code can read and run the scripts for you, explain the plan, and help you adjust parameters — no API key needed.

### Option 2: Run the Scripts Directly

```bash
git clone https://github.com/uttarashekar/treasury-bond-ladder.git
cd treasury-bond-ladder
pip install -r requirements.txt
```

**See the full plan:**
```bash
python3 buy_now.py --plan
```

**See what to buy this month:**
```bash
python3 buy_now.py
```

**See what to buy in a specific month:**
```bash
python3 buy_now.py 2026-07
```

**Run the planner with math verification:**
```bash
python3 planner.py
```

### Option 3: Interactive AI Agent (Requires Anthropic API Key)

Chat with Claude about your bond ladder — ask questions, adjust parameters, get advice:

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
python3 agent.py
```

The agent has 5 tools it can call:
| Tool | What It Does |
|------|-------------|
| `generate_plan` | Create a bond ladder with custom parameters |
| `verify_math` | Independently verify all calculations |
| `get_purchase_details` | Get form instructions for a specific month |
| `get_next_purchase` | Get instructions for this month's purchase |
| `fetch_current_rate` | Pull the latest T-Bill rate from the Treasury API |

Example conversation:
```
You: Generate a plan with $50K split into 5 batches at 4.2% rate
Agent: [calls generate_plan, then verify_math, shows table and verification]

You: What should I buy this month?
Agent: [calls get_next_purchase, shows form details and URLs]
```

## Monthly Email Reminders

Get an email at the start of each month telling you exactly what to buy, with links and form instructions.

### Setup

```bash
cp .env.example .env
```

Edit `.env` with your SMTP credentials:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
RECIPIENT_EMAIL=your-email@gmail.com
```

> **Gmail users:** You need an [App Password](https://support.google.com/accounts/answer/185833), not your regular password. Go to Google Account → Security → 2-Step Verification → App Passwords.

### Test locally

```bash
python3 scheduler.py
```

### Deploy to Cloud

The included `Dockerfile` makes deployment simple on any cloud platform:

#### AWS (ECS + EventBridge)

```bash
# Build and push to ECR
docker build -t treasury-agent .
aws ecr create-repository --repository-name treasury-agent
docker tag treasury-agent:latest <account-id>.dkr.ecr.<region>.amazonaws.com/treasury-agent
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/treasury-agent

# Create an EventBridge rule to trigger on the 1st of each month
# Schedule expression: cron(0 9 1 * ? *)
```

#### Railway / Render

1. Connect your GitHub repo
2. Set environment variables from `.env.example`
3. Add a cron job: `0 9 1 * *` → `python3 scheduler.py`

#### Simple Cron (Any Linux Server)

```bash
# Edit crontab
crontab -e

# Add this line (runs at 9am on the 1st of each month):
0 9 1 * * cd /path/to/treasury-bond-ladder && /usr/bin/python3 scheduler.py
```

## How the Bond Ladder Works

```
Month 1  ──► Buy $10K 52-Wk T-Bill  ──────────────────────────► Matures → $10,000 + interest
Month 2  ──► Buy $10K 52-Wk T-Bill  ──────────────────────────► Matures → $10,000 + interest
Month 3  ──► Buy $10K 52-Wk T-Bill  ──────────────────────────► Matures → $10,000 + interest
  ...                                                              ...
Month 10 ──► Buy $10K 52-Wk T-Bill  ──────────────────────────► Matures → $10,000 + interest
```

- **T-Bills are sold at a discount.** You pay ~$9,545 for a $10,000 face value bill (at 4.5% rate).
- **At maturity, you get the full $10,000** deposited to your bank account.
- **The difference ($455) is your interest**, taxed at federal level only (exempt from state/local tax).
- **You're buying at auction** via a non-competitive bid — you get the market-clearing rate.

## Customization

Edit the parameters in `planner.py` or pass them to the agent:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `total_investment` | $100,000 | Total amount to invest |
| `num_batches` | 10 | Number of monthly purchases |
| `annual_rate` | 4.50% | Estimated T-Bill discount rate |
| `start_date` | Next month | When to start buying |

You can also set these as environment variables for the scheduler:
```env
TOTAL_INVESTMENT=50000
NUM_BATCHES=5
TBILL_RATE=0.042
START_DATE=2026-06-01
```

## Project Structure

```
treasury-bond-ladder/
├── buy_now.py        # CLI: what to buy this month / full plan view
├── planner.py        # Core math: generates plan + verifies calculations
├── bonds.py          # Treasury data: URLs, form fields, rate fetching
├── agent.py          # AI agent with system prompt + tools (Anthropic SDK)
├── emailer.py        # HTML email builder + SMTP sender
├── scheduler.py      # Cron entry point for monthly reminders
├── Dockerfile        # Cloud deployment container
├── requirements.txt  # Python dependencies
└── .env.example      # Environment variable template
```

## Links

- [TreasuryDirect.gov](https://www.treasurydirect.gov/) — where you buy the bonds
- [BuyDirect Page](https://www.treasurydirect.gov/RS/UN-Display.do) — direct link to purchase
- [Upcoming Auctions](https://www.treasurydirect.gov/auctions/upcoming/) — auction schedule
- [T-Bill Info](https://www.treasurydirect.gov/marketable-securities/treasury-bills/) — how T-Bills work
