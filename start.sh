#!/bin/bash

# เริ่มต้นระบบ tkc-telegram-bot

echo "🔧 Checking Python environment..."
python3 --version || { echo "❌ Python 3 is not installed."; exit 1; }

echo "📦 Installing dependencies..."
pip3 install -r requirements.txt || { echo "❌ Failed to install dependencies."; exit 1; }

echo "🚀 Starting bot..."
python3 main.py
