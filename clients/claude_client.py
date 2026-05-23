import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("ANTHROPIC_API_KEY")

_PROMPTS = {
    "live": """\
You are a market analyst. Based on the following live screener output, write a concise daily market brief.

Structure it with these sections:
1. Macro Environment — VIX, SPY trend, risk signal
2. Today's Picks — for each stock: what the setup is, why conviction is what it is, key risk
3. Action Summary — one sentence on what to do (enter, wait, avoid)

Be specific with tickers, strikes, and numbers. Keep it tight — this is a daily actionable brief.\
""",
    "research": """\
You are a market analyst. Based on the following weekend research screener output, write a concise market analysis report.

Structure it with these sections:
1. Macro Environment — VIX level, SPY trend, overall risk-on/risk-off read
2. Sector Rotation — which sectors are leading and lagging, what that signals
3. LEAP Opportunities — any stocks that passed all criteria; be specific about conviction and why
4. Watchlist Candidates — fundamental candidates worth monitoring for entry
5. Key Takeaway — one paragraph summary of what to watch next week

Be specific with tickers and numbers. Professional but readable — no fluff.\
""",
    "backtest": """\
You are a quantitative analyst. Based on the following backtest results for a LEAP options strategy, write a concise performance report.

Structure it with these sections:
1. Strategy Overview — overall hit rate, average return, total trades
2. Top Performers — best stocks historically for this strategy and what they have in common
3. Underperformers — worst stocks and what to watch out for
4. Sector Breakdown — if sector patterns are visible in the results
5. Key Takeaway — what the data says about the strategy's edge and where it works best

Be specific with tickers and numbers. Focus on actionable insights.\
""",
}


def generate_report(raw_output: str, report_type: str) -> str:
    """Generate a market analysis report from raw screener output. Falls back to raw output if no API key."""
    if not _API_KEY:
        return raw_output

    client = anthropic.Anthropic(api_key=_API_KEY)
    prompt = _PROMPTS.get(report_type, _PROMPTS["research"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"{prompt}\n\nScreener Output:\n{raw_output}"}],
    )
    return message.content[0].text
