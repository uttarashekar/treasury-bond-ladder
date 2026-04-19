"""
Treasury Bond Ladder Agent

Built with the Anthropic SDK's tool_runner and @beta_tool decorator.
Instead of hand-rolling tool schemas and the agentic loop, the SDK:
  - Auto-generates JSON schemas from type hints and docstrings (@beta_tool)
  - Automatically executes tools and feeds results back to Claude (tool_runner)
  - Manages conversation history internally
"""

import json
from anthropic import Anthropic, beta_tool
from planner import generate_investment_plan, verify_math, format_plan_table
from bonds import (
    get_purchase_details_for_month,
    get_next_purchase as _get_next_purchase,
    get_latest_tbill_rate,
)

client = Anthropic()

SYSTEM_PROMPT = """\
You are a Treasury Bond Ladder Advisor — an AI agent that helps users build \
a bond ladder using U.S. Treasury Bills from TreasuryDirect.gov.

Your job:
1. Generate a personalized bond ladder plan that splits a lump sum (default $100K) \
into monthly 52-week T-Bill purchases so that bonds mature one per month, \
returning ~$10K + interest each month.
2. Verify all math using Python — every number in the plan must be independently checked.
3. Provide exact purchase instructions: which bond to buy, when, for how much, \
and step-by-step form-filling details for TreasuryDirect.gov.
4. Tell the user which bond to buy THIS month, with a direct link to the purchase page.

Key facts about T-Bills:
- T-Bills are sold at a DISCOUNT to face value. You pay less upfront, get face value at maturity.
- 52-week T-Bills auction approximately every 4 weeks.
- Purchases are non-competitive bids — you get the market-clearing rate.
- All purchases happen on TreasuryDirect.gov.
- Interest earned on T-Bills is exempt from state/local income tax (federal only).

When presenting plans:
- Always show a clear table with purchase dates, maturity dates, amounts, and interest.
- Always run math verification and report the results.
- Always include TreasuryDirect URLs and step-by-step purchase instructions.
- Proactively fetch the latest T-Bill rate if the user hasn't specified one.
- Be specific about dollar amounts — no rounding or hand-waving.

When asked about the next purchase:
- Identify which month's bond is due for purchase.
- Provide the exact form fields and steps to complete the purchase.
- Include the direct URL to BuyDirect on TreasuryDirect.gov.
"""


# ── Tools ──
# Each @beta_tool function becomes a tool that Claude can call.
# The SDK auto-generates the JSON schema from:
#   - Function name → tool name
#   - First docstring line → tool description
#   - Type hints → parameter types
#   - Args section in docstring → parameter descriptions


@beta_tool
def generate_plan(
    total_investment: float = 100_000.0,
    num_batches: int = 10,
    start_date: str = "",
    annual_rate: float = 0.045,
) -> str:
    """Generate a treasury bond ladder investment plan with purchase dates, maturity dates, amounts, and interest.

    Args:
        total_investment: Total amount to invest in dollars. Default 100000.
        num_batches: Number of monthly batches (10-12). Default 10.
        start_date: First purchase date in YYYY-MM-DD format. Default next month.
        annual_rate: Estimated annual T-Bill discount rate as decimal (e.g. 0.045 for 4.5%).
    """
    kwargs = {"total_investment": total_investment, "num_batches": num_batches, "annual_rate": annual_rate}
    if start_date:
        kwargs["start_date"] = start_date
    plan = generate_investment_plan(**kwargs)
    table = format_plan_table(plan)
    return json.dumps({"plan": plan, "formatted_table": table})


@beta_tool
def verify_plan_math(plan: dict) -> str:
    """Independently verify all math in an investment plan — checks face values, discounts, interest, and maturity dates.

    Args:
        plan: The investment plan object as returned by generate_plan.
    """
    result = verify_math(plan)
    return json.dumps(result)


@beta_tool
def get_purchase_details(month_number: int, plan: dict) -> str:
    """Get detailed purchase instructions for a specific month including TreasuryDirect URLs and form fields.

    Args:
        month_number: The month number (1-based) in the plan to get details for.
        plan: The investment plan object.
    """
    purchases = plan["purchases"]
    if 1 <= month_number <= len(purchases):
        details = get_purchase_details_for_month(month_number, purchases[month_number - 1])
        return json.dumps(details)
    return json.dumps({"error": f"Month {month_number} is out of range (1-{len(purchases)})"})


@beta_tool
def get_next_purchase(plan: dict) -> str:
    """Determine which bond to purchase this month based on the current date and the plan.

    Args:
        plan: The investment plan object.
    """
    details = _get_next_purchase(plan)
    if details:
        return json.dumps(details)
    return json.dumps({"message": "All planned purchases are complete!"})


@beta_tool
def fetch_current_rate() -> str:
    """Fetch the latest average T-Bill interest rate from the U.S. Treasury Fiscal Data API."""
    rate = get_latest_tbill_rate()
    if rate is not None:
        return json.dumps({
            "current_rate": rate,
            "formatted": f"{rate * 100:.2f}%",
            "source": "U.S. Treasury Fiscal Data API",
        })
    return json.dumps({
        "error": "Could not fetch current rate. Using default 4.50%.",
        "fallback_rate": 0.045,
    })


# ── All tools in one list ──
ALL_TOOLS = [generate_plan, verify_plan_math, get_purchase_details, get_next_purchase, fetch_current_rate]


def run_agent(user_message: str, conversation_history: list | None = None) -> tuple[str, list]:
    """
    Run one turn of the agent.

    The tool_runner handles the entire loop:
      1. Sends the message to Claude
      2. If Claude calls a tool, executes it and feeds the result back
      3. Repeats until Claude produces a final text response

    No manual stop_reason checking, no tool_result plumbing.
    """
    if conversation_history is None:
        conversation_history = []

    conversation_history.append({"role": "user", "content": user_message})

    # tool_runner replaces the manual while-loop + tool dispatch.
    # It automatically calls our @beta_tool functions when Claude requests them.
    runner = client.beta.messages.tool_runner(
        model="claude-sonnet-4-6-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
        messages=conversation_history,
    )

    final_message = runner.until_done()

    # Extract text from the final response
    assistant_text = ""
    for block in final_message.content:
        if hasattr(block, "text"):
            assistant_text += block.text

    conversation_history.append({"role": "assistant", "content": final_message.content})
    return assistant_text, conversation_history


def main():
    """Interactive CLI for the Treasury Bond Ladder Agent."""
    print("=" * 60)
    print("  Treasury Bond Ladder Agent")
    print("  Powered by Claude — Anthropic Agent SDK")
    print("=" * 60)
    print()
    print("Ask me to generate a bond ladder plan, verify math,")
    print("or get purchase instructions for this month.")
    print("Type 'quit' to exit.")
    print()

    history = None
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not user_input:
            continue

        try:
            response_text, history = run_agent(user_input, history)
            print(f"\nAgent: {response_text}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
