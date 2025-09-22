#!/bin/bash

# التحقق من إصدار Python المتاح
if command -v python3 &>/dev/null; then
    echo "Using python3"
    python3 bot.py
elif command -v python &>/dev/null; then
    echo "Using python"
    python bot.py
else
    echo "Error: Python not found"
    exit 1
fi
