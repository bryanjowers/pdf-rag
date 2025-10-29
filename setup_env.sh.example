#!/bin/bash
# Phase 3 Environment Setup
# Run: source setup_env.sh

# OpenAI API Key (should already be set from Phase 2)
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set. Please export it:"
    echo "   export OPENAI_API_KEY='your-key-here'"
fi

# LangSmith Configuration (note: LANGCHAIN not LANGSMITH)
# Uncomment and set these if using LangSmith tracing:
# export LANGCHAIN_TRACING_V2=true
# export LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
# export LANGCHAIN_PROJECT="pr-formal-remote-93"
# export LANGCHAIN_API_KEY="your-langchain-api-key-here"

# Confirm settings
echo "✅ Phase 3 environment configured:"
if [ -n "$OPENAI_API_KEY" ]; then
    echo "   - OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}... ✅"
else
    echo "   - OPENAI_API_KEY: Not set ⚠️"
fi
if [ -n "$LANGCHAIN_TRACING_V2" ]; then
    echo "   - LANGCHAIN_TRACING_V2: $LANGCHAIN_TRACING_V2 ✅"
    echo "   - LANGCHAIN_PROJECT: $LANGCHAIN_PROJECT"
fi
echo ""
echo "Note: LangSmith tracing is disabled by default. Uncomment in setup_env.sh to enable."
