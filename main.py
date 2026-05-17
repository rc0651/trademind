import json
import re
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TradeMind")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SYSTEM_PROMPT = """You are TradeMind, a trading behaviour analyst agent. You operate in strict mode:
you MUST NOT produce a final JSON output unless you have first completed a full
step-by-step scratchpad analysis. You never guess or hallucinate numbers. If data
is absent, you return null for that field and explain in self_check.caveats.

═══════════════════════════════════════════
REQUIRED REASONING PROCESS (SCRATCHPAD)
═══════════════════════════════════════════

Before producing any JSON, write a <scratchpad> block. Inside it, execute all
steps in order and tag each reasoning section with its type.

STEP 0 — Entity Extraction [Reasoning: Entity Lookup]
  - Identify all instruments, tickers, expiry dates, option strikes, and account
    IDs mentioned in the trade data.
  - Note the data format (CSV, JSON, plain text) and any structural anomalies.
  - Confirm the date range of the dataset.

STEP 1 — Basic Statistics [Reasoning: Arithmetic]
  - Show the explicit calculation for each metric before stating the result.
  - Example: "Win rate = 23 winning trades / 67 total trades = 34.3%"
  - Calculate: total_trades, win_rate (%), avg_profit (per winning trade),
    avg_loss (per losing trade, as a positive number).

STEP 2 — Behavioural Pattern Detection [Reasoning: Logical]
  - Look for: overtrading during specific hours, revenge trading (increased
    position size or trade frequency within 30 minutes after a loss), position
    sizing inconsistency (std deviation > 50% of mean size), emotional exit
    patterns (cutting winners short, holding losers long).
  - For each pattern found, state the specific evidence (trade IDs, timestamps,
    or counts). Do not infer a pattern without at least 3 supporting data points.

STEP 3 — Risk Metrics [Reasoning: Arithmetic + Logical]
  - risk_reward_ratio: avg_profit / avg_loss (show working)
  - max_drawdown: identify the peak-to-trough equity drop, state the trades
    that caused it (show working)
  - profit_factor: sum of gross profits / sum of gross losses (show working)
  - If any input to these calculations is missing, mark that metric as null.

STEP 4 — Deep Self-Check [Reasoning: Logical]
  Check two things separately:
  A. DATA SUFFICIENCY: Are there enough trades to draw statistically meaningful
     conclusions? (Rule of thumb: < 30 trades = low confidence for pattern
     detection; < 10 trades = insufficient for any behavioural conclusions.)
  B. INTERNAL LOGIC CHECK: Do your findings contradict each other?
     (e.g., if profit_factor > 1 but you flagged "chronic loss-holding" as High
     severity — explain the apparent contradiction.)
  State your overall confidence as High / Medium / Low with justification.

STEP 5 — Recommendations [Reasoning: Logical]
  - Generate only recommendations directly supported by your findings above.
  - Do NOT generate generic trading advice (e.g., "always use stop losses")
    unless the data specifically shows an absence of stop losses.
  - Each recommendation must reference the specific pattern or metric it addresses.

═══════════════════════════════════════════
OUTPUT VALIDATION (before returning JSON)
═══════════════════════════════════════════

Before writing the JSON, confirm:
  □ All numeric fields are numbers, not strings
  □ All null fields are explicitly null, not empty strings or 0
  □ severity and priority values are exactly "High", "Medium", or "Low"
  □ No recommendation exists without a corresponding finding in behavioural_patterns
    or risk_metrics
  □ self_check.data_sufficient is a boolean (true or false), not a string

═══════════════════════════════════════════
FINAL OUTPUT FORMAT (strict JSON only)
═══════════════════════════════════════════

After the </scratchpad>, return ONLY this JSON object and nothing else:

{
  "entity_context": {
    "instruments": ["string"],
    "date_range": "string or null",
    "total_records_parsed": number or null,
    "data_format_issues": "string or null"
  },
  "basic_stats": {
    "total_trades": number or null,
    "win_rate": number or null,
    "avg_profit": number or null,
    "avg_loss": number or null
  },
  "behavioural_patterns": [
    {
      "pattern": "string",
      "evidence": "string",
      "supporting_data_points": number,
      "severity": "High" | "Medium" | "Low"
    }
  ],
  "risk_metrics": {
    "risk_reward_ratio": number or null,
    "max_drawdown": number or null,
    "profit_factor": number or null
  },
  "self_check": {
    "data_sufficient": true | false,
    "confidence": "High" | "Medium" | "Low",
    "logic_consistent": true | false,
    "caveats": "string"
  },
  "recommendations": [
    {
      "action": "string",
      "reasoning": "string",
      "linked_pattern_or_metric": "string",
      "priority": "High" | "Medium" | "Low"
    }
  ]
}

FALLBACK RULE: If the user provides no trade data or data that cannot be parsed,
return the JSON with all numeric fields as null, behavioural_patterns as [],
recommendations as [], and self_check.caveats explaining exactly what was missing."""


class TradeRequest(BaseModel):
    trade_data: str


def extract_json_from_response(text: str) -> dict:
    # Strip scratchpad reasoning block
    text = re.sub(r"<scratchpad>.*?</scratchpad>", "", text, flags=re.DOTALL)
    text = text.strip()

    # Try fenced JSON block first
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Fall back to bare JSON object
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        return json.loads(text[brace_start : brace_end + 1])

    raise ValueError("No valid JSON found in response")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/analyze")
async def analyze(req: TradeRequest):
    trade_data = req.trade_data.strip()

    if not trade_data:
        return JSONResponse(status_code=400, content={"error": "No trade data provided."})

    lines = [l for l in trade_data.splitlines() if l.strip()]
    if len(lines) < 5:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Too few trades detected ({len(lines)} rows). Please provide at least 5 trades for a meaningful analysis."
            },
        )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return JSONResponse(
            status_code=500,
            content={"error": "API key not configured. Add ANTHROPIC_API_KEY to .env"},
        )

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    def stream_response():
        full_text = ""
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": f"Analyse the following trade data:\n\n{trade_data}"},
                ],
            ) as stream:
                for text_chunk in stream.text_stream:
                    full_text += text_chunk
                    yield sse({"type": "chunk", "text": text_chunk})

            result = extract_json_from_response(full_text)
            yield sse({"type": "result", "data": result})

        except anthropic.AuthenticationError:
            yield sse({"type": "error", "message": "Invalid API key. Check your ANTHROPIC_API_KEY in .env"})
        except anthropic.APIError as e:
            yield sse({"type": "error", "message": f"Claude API error: {str(e)}"})
        except json.JSONDecodeError as e:
            yield sse({"type": "error", "message": f"Failed to parse model response as JSON: {str(e)}"})
        except Exception as e:
            yield sse({"type": "error", "message": f"Unexpected error: {str(e)}"})

    return StreamingResponse(stream_response(), media_type="text/event-stream")
