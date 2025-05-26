#!/bin/bash

echo "🔧 Checking Python..."
python3 --version || { echo "❌ Python 3 not installed"; exit 1; }

echo "📦 Installing requirements..."
pip3 install -r requirements.txt || { echo "❌ Install failed"; exit 1; }

echo "🚀 Starting all TKC bots (multi-bot mode)..."
python3 main_async.py
