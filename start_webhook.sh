#!/bin/bash

echo "🔧 Checking Python..."
python3 --version || { echo '❌ Python 3 not installed'; exit 1; }

echo "📦 Installing dependencies..."
pip3 install -r requirements.txt || { echo '❌ Dependency install failed'; exit 1; }

echo "🚀 Starting all bots (Webhook mode)..."
python3 main_webhook_multi_v2.py
