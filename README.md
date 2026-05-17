# TradeMind — Trade Behaviour Analyser Agent (EAG Week 5)

## Demo
[paste youtube link here after recording]

## What It Does
A multi-step AI agent that analyses trading history across 6 structured reasoning
steps to detect behavioural patterns, calculate risk metrics, and generate
data-backed recommendations — with Claude's full reasoning streamed live to the UI.

## Architecture

```
Browser (HTML/JS)
    │
    │  POST /analyze  (SSE stream)
    ▼
FastAPI Backend (main.py)
    │
    │  client.messages.stream()
    ▼
Claude Haiku (claude-haiku-4-5)
    │
    ├─ <scratchpad> — 6-step reasoning (streamed live to UI)
    └─ JSON output  — structured result rendered in 6 sections
```

## Live Streaming Flow
When you click **Analyse Trades**:
1. Backend opens a **streaming SSE connection** to Claude
2. Claude's scratchpad reasoning streams **word by word** to the browser in real-time
3. A **step progress bar** (0→5) highlights the current reasoning step
4. Once Claude finishes, the 6 result sections render instantly from the parsed JSON

No frozen wait — you watch the reasoning happen live.

## Multi-Step Reasoning Flow
| Step | Reasoning Type | What Happens |
|---|---|---|
| 0 | Entity Lookup | Parse instruments, date range, format anomalies |
| 1 | Arithmetic | Win rate, avg profit, avg loss (with shown workings) |
| 2 | Logical | Overtrading, revenge trading, sizing inconsistency |
| 3 | Arithmetic + Logical | Risk-reward ratio, max drawdown, profit factor |
| 4 | Logical | Data sufficiency check + internal logic consistency check |
| 5 | Logical | Data-backed recommendations only — no generic advice |

## Output Sections
| Section | What You See |
|---|---|
| Entity Context | Instruments detected, date range, record count |
| Basic Statistics | Total trades, win rate, avg profit, avg loss |
| Behavioural Patterns | Patterns with evidence, severity, data point count |
| Risk Metrics | Risk/reward ratio, max drawdown, profit factor |
| Confidence Check | Data sufficiency, logic consistency, caveats |
| Recommendations | Prioritised actions linked to specific findings |

## Original Prompt

```
i have trade data like date, stock name, buy/sell, qty, price, profit or loss
i want you to look at it and tell me how im trading, like am i making mistakes
also tell me the stats like winrate and average profit loss etc
and if i have any bad habits like trading too much or revenge trading after a loss
also tell me risk stuff like drawdown and risk reward
and give me some tips on what to do better
return everything in json format so i can use it in my app
```

## Qualified Prompt (Claude-improved)

```
You are TradeMind, a trading behaviour analyst agent. You operate in strict mode:
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
recommendations as [], and self_check.caveats explaining exactly what was missing.
```

## Edge Cases Handled
- Fewer than 5 trades → warning shown on UI, no API call made
- Missing PnL values → null returned, flagged in self_check.caveats
- Fewer than 30 trades → Low confidence flagged automatically
- Contradicting findings → explained in self_check.logic_consistent
- Model runs out of tokens → max_tokens set to 8192 to fit full scratchpad + JSON
- API key invalid → specific error message shown on UI

## Stack
| Layer | Technology |
|---|---|
| Language | Python 3.10 |
| Backend | FastAPI + Uvicorn |
| Streaming | Server-Sent Events (SSE) via `StreamingResponse` |
| AI Model | Claude Haiku (`claude-haiku-4-5-20251001`) |
| AI SDK | Anthropic Python SDK (`client.messages.stream`) |
| Frontend | Vanilla HTML + CSS + JavaScript |
| Package Manager | uv |
| Config | python-dotenv (.env) |

## Run Locally

```bash
# 1. Install dependencies
uv sync

# 2. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# 3. Start the server
uv run uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000**, click **Load Sample Data**, then **Analyse Trades**.
