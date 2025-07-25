#!/usr/bin/env python3
"""
Web Dashboard Demo
Launch the real-time monitoring dashboard for the trading bot
"""
import asyncio
import logging
import sys
import webbrowser
from datetime import datetime

from src.trading_bot import TradingBot
from src.config import Config
from src.logger import setup_logger
from src.dashboard import start_dashboard

async def demo_dashboard():
    """Start the web dashboard with a trading bot instance."""
    
    print("🌐 AI TRADING BOT - WEB DASHBOARD")
    print("━" * 60)
    print("🚀 Starting real-time monitoring dashboard")
    print("📊 Features: Portfolio tracking, Trade history, AI decisions")
    print("⚡ Live data updates every 30 seconds")
    print("━" * 60)
    
    try:
        # Setup logging
        setup_logger()
        
        # Load configuration
        config = Config()
        
        print("🏗️ Initializing trading bot...")
        
        # Initialize trading bot
        bot = TradingBot(config)
        await bot.initialize()
        
        print("✅ Trading bot initialized successfully")
        print("🌐 Starting web dashboard server...")
        
        # Start dashboard server
        dashboard_url = "http://127.0.0.1:8000"
        print(f"📊 Dashboard will be available at: {dashboard_url}")
        print("💡 The dashboard will open automatically in your browser")
        print("🛑 Press Ctrl+C to stop the dashboard")
        print("━" * 60)
        
        # Try to open browser after a short delay
        async def open_browser():
            await asyncio.sleep(3)  # Wait for server to start
            try:
                webbrowser.open(dashboard_url)
                print("🌐 Dashboard opened in your default browser")
            except Exception as e:
                print(f"⚠️ Could not auto-open browser: {e}")
                print(f"📋 Please manually open: {dashboard_url}")
        
        # Start browser opening task
        asyncio.create_task(open_browser())
        
        # Start the dashboard (this will run indefinitely)
        await start_dashboard(bot, host="127.0.0.1", port=8000)
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Dashboard failed to start: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔄 Starting dashboard demo...")
    asyncio.run(demo_dashboard()) 