"""
Treasury Bond Ladder Agent

An AI agent built with the Anthropic SDK that helps plan, verify, and execute
a treasury bond ladder strategy. Uses Claude's tool use API with a dedicated
system prompt and tool definitions.
"""

import json
import os
from anthropic import Anthropic
from planner import generate_investment_plan, verify_math, format_plan_table
from bonds import (
    get_purchase_details_for_month,
    get_next_purchase,
    get_latest_tbill_rate,
    URLS,
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

TOOLS = [
    {
        "name": "generate_plan",
        "description": (
            "Generate a treasury bond ladder investment plan. Splits a total investment "
            "into monthly 52-week T-Bill purchases so bonds mature one per month. "
            "Returns a full plan with purchase dates, maturity dates, amounts, and interest."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "total_investment": {
                    "type": "number",
                    "description": "Total amount to invest in dollars. Default: 100000",
                },
                "num_batches": {
                    "type": "integer",
                    "description": "Number of monthly batches (10-12). Default: 10",
                },
                "start_date": {
                    "type": "string",
                    "description": "First purchase date in YYYY-MM-DD format. Default: next month's 1st.",
                },
                "annual_rate": {
                    "type": "number",
                    "description": "Estimated annual T-Bill discount rate as decimal (e.g., 0.045 for 4.5%). Default: 0.045",
                },
            },
            "required": [],
        },
    },
    {
        "name": "verify_math",
        "description": (
            "Independently verify all math in an investment plan using pure arithmetic. "
            "Checks total face values, discount calculations, interest amounts, and maturity dates. "
            "Returns a pass/fail report for each check."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "object",
                    "description": "The investment plan object to verify (as returned by generate_plan).",
                },
            },
            "required": ["plan"],
        },
    },
    {
        "name": "get_purchase_details",
        "description": (
            "Get detailed purchase instructions for a specific month's bond purchase, "
            "including TreasuryDirect.gov URLs, form fields, and step-by-step instructions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "month_number": {
                    "type": "integer",
                    "description": "The month number (1-based) in the plan to get details for.",
                },
                "plan": {
                    "type": "object",
                    "description": "The investment plan object.",
                },
            },
            "required": ["month_number", "plan"],
        },
    },
    {
        "name": "get_next_purchase",
        "description": (
            "Determine which bond to purchase this month based on the current date and the plan. "
            "Returns full purchase instructions with URLs and form details."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "object",
                    "description": "The investment plan object.",
                },
            },
            "required": ["plan"],
        },
    },
    {
        "name": "fetch_current_rate",
        "description": (
            "Fetch the latest average T-Bill interest rate from the U.S. Treasury Fiscal Data API. "
            "Returns the rate as a decimal (e.g., 0.045 for 4.5%)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return the result as a JSON string."""
    if tool_name == "generate_plan":
        plan = generate_investment_plan(**tool_input)
        table = format_plan_table(plan)
        return json.dumps({"plan": plan, "formatted_table": table})

    elif tool_name == "verify_math":
        result = verify_math(tool_input["plan"])
        return json.dumps(result)

    elif tool_name == "get_purchase_details":
        month = tool_input["month_number"]
        plan = tool_input["plan"]
        purchases = plan["purchases"]
        if 1 <= month <= len(purchases):
            details = get_purchase_details_for_month(month, purchases[month - 1])
            return json.dumps(details)
        return json.dumps({"error": f"Month {month} is out of range (1-{len(purchases)})"})

    elif tool_name == "get_next_purchase":
        details = get_next_purchase(tool_input["plan"])
        if details:
            return json.dumps(details)
        return json.dumps({"message": "All planned purchases are complete!"})

    elif tool_name == "fetch_current_rate":
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

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def run_agent(user_message: str, conversation_history: list | None = None) -> tuple[str, list]:
    """
    Run one turn of the agent loop.

    Args:
        user_message: The user's input message.
        conversation_history: Prior messages for multi-turn context.

    Returns:
        (assistant_text, updated_conversation_history)
    """
    if conversation_history is None:
        conversation_history = []

    conversation_history.append({"role": "user", "content": user_message})

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            assistant_content = response.content

            for block in response.content:
                if block.type == "tool_use":
                    result = handle_tool_call(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            conversation_history.append({"role": "assistant", "content": assistant_content})
            conversation_history.append({"role": "user", "content": tool_results})
            continue

        # End turn — extract text response
        assistant_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                assistant_text += block.text

        conversation_history.append({"role": "assistant", "content": response.content})
        return assistant_text, conversation_history


def main():
    """Interactive CLI for the Treasury Bond Ladder Agent."""
    print("=" * 60)
    print("  Treasury Bond Ladder Agent")
    print("  Powered by Claude — Anthropic SDK")
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
