#!/usr/bin/env python3
"""
Single Cycle AI Trading Bot Demo
Runs one trading cycle and exits - perfect for quick testing!
"""
import asyncio
import logging
import sys
from datetime import datetime

from src.trading_bot import TradingBot
from src.config import Config
from src.logger import setup_logger

async def run_single_cycle():
    """Run a single trading cycle and exit."""
    
    print("🚀 AI TRADING BOT - SINGLE CYCLE DEMO")
    print("━" * 60)
    print("✅ Live GPT-4 AI Making Real Decisions")
    print("✅ Real Market Data from CoinGecko")
    print("✅ Enhanced Demo Mode with $10K Balance")
    print("✅ Complete Trade Execution & Logging")
    print("━" * 60)
    
    try:
        # Setup logging
        setup_logger()
        logger = logging.getLogger(__name__)
        
        # Load configuration
        config = Config()
        print(f"💰 Portfolio: $10,000 Demo Balance")
        print(f"🎯 Max Risk: {float(config.max_portfolio_risk)*100}% per trade")
        print(f"🤖 AI Model: {config.ai_model}")
        print("━" * 60)
        
        # Initialize trading bot
        bot = TradingBot(config)
        await bot.initialize()
        
        print("🧠 Querying live GPT-4 for trading decision...")
        
        # Run one cycle
        await bot.run_cycle()
        
        # Shutdown
        await bot.shutdown()
        
        print("━" * 60)
        print("🎯 Single cycle demo completed!")
        print("📊 Check logs/trading_bot.log for detailed logs")
        print("💡 Run 'python3 main.py' for continuous trading")
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_single_cycle()) 