#!/usr/bin/env python3
"""
Quick Cycles AI Trading Bot Demo
Runs multiple cycles with 30-second intervals - great for testing!
"""
import asyncio
import logging
import sys
from datetime import datetime

from src.trading_bot import TradingBot
from src.config import Config
from src.logger import setup_logger

async def run_quick_cycles():
    """Run multiple quick trading cycles with 30-second intervals."""
    
    print("🚀 AI TRADING BOT - QUICK CYCLES DEMO")
    print("━" * 60)
    print("✅ Live GPT-4 AI Making Real Decisions")
    print("✅ Real Market Data from CoinGecko")
    print("✅ Quick 30-second intervals between cycles")
    print("✅ Press Ctrl+C to stop anytime")
    print("━" * 60)
    
    try:
        # Setup logging
        setup_logger()
        logger = logging.getLogger(__name__)
        
        # Load configuration
        config = Config()
        
        # Override trading interval for quick demo
        config.trading_interval = 30  # 30 seconds between cycles
        
        print(f"💰 Portfolio: $10,000 Demo Balance")
        print(f"🎯 Max Risk: {float(config.max_portfolio_risk)*100}% per trade")
        print(f"⏰ Cycle Interval: {config.trading_interval} seconds")
        print("━" * 60)
        
        # Initialize trading bot
        bot = TradingBot(config)
        await bot.initialize()
        
        cycle_count = 0
        
        print("🧠 Starting quick cycles with live GPT-4 decisions...")
        
        while True:
            cycle_count += 1
            print(f"\n🔄 === QUICK CYCLE #{cycle_count} ===")
            
            # Run one cycle
            await bot.run_cycle()
            
            print(f"✅ Cycle #{cycle_count} completed!")
            print(f"⏰ Waiting 30 seconds until next cycle...")
            print("💡 Press Ctrl+C to stop")
            
            # Quick countdown
            for remaining in range(30, 0, -5):
                print(f"⏳ Next cycle in: {remaining:02d} seconds", end="\r", flush=True)
                await asyncio.sleep(5)
            
            print()  # New line
        
    except KeyboardInterrupt:
        print("\n🛑 Quick cycles demo stopped by user")
        if 'bot' in locals():
            await bot.shutdown()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_quick_cycles()) 