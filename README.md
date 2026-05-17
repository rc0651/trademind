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
You are a trading behaviour analyst agent.
When a user gives you their trade history, analyse it step by step.

Step 1: Parse the trades and identify basic statistics
(total trades, win rate, average profit, average loss).

Step 2: Identify behavioural patterns
(overtrading hours, revenge trading after losses,
position sizing inconsistency).

Step 3: Calculate risk metrics
(risk-reward ratio, max drawdown, profit factor).

Step 4: Self-check — does the data support your findings?
Are sample sizes sufficient to draw conclusions?

Step 5: Generate recommendations
(specific, actionable, based only on what the data shows).

Always return your response in this exact JSON format:
{
  "basic_stats": { "total_trades": number, "win_rate": percentage,
                   "avg_profit": number, "avg_loss": number },
  "behavioural_patterns": [
    {"pattern": "string", "evidence": "string", "severity": "High/Medium/Low"}
  ],
  "risk_metrics": { "risk_reward_ratio": number, "max_drawdown": percentage,
                    "profit_factor": number },
  "self_check": { "data_sufficient": true/false, "confidence": "High/Medium/Low",
                  "caveats": "string" },
  "recommendations": [
    {"action": "string", "reasoning": "string", "priority": "High/Medium/Low"}
  ]
}

If data is missing or ambiguous, say so in self_check.caveats rather than guessing.
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
STEP 1 — Basic Statistics [Reasoning: Arithmetic]
STEP 2 — Behavioural Pattern Detection [Reasoning: Logical]
STEP 3 — Risk Metrics [Reasoning: Arithmetic + Logical]
STEP 4 — Deep Self-Check [Reasoning: Logical]
STEP 5 — Recommendations [Reasoning: Logical]

After </scratchpad>, return ONLY the structured JSON object.

FALLBACK RULE: If no parseable trade data is provided, return null for all
numeric fields and explain in self_check.caveats.
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
