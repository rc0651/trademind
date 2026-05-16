# TradeMind — Trade Behaviour Analyser

A FastAPI web app that analyses trading behaviour using Claude AI.

## Setup

```bash
# Install dependencies
uv sync

# Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# Run locally
uv run uvicorn main:app --reload --port 8000
```

Open http://localhost:8000
