#!/usr/bin/env python3
"""
Live AI Trading Demo with Relaxed Risk Management
Shows the full AI trading pipeline with actual trade execution
"""
import asyncio
import logging
import sys
from datetime import datetime

from src.trading_bot import TradingBot
from src.config import Config
from src.logger import setup_logger

async def demo_live_trading():
    """Run a live trading demo with relaxed risk management."""
    
    print("🔥 LIVE AI TRADING DEMO - FULL EXECUTION")
    print("━" * 60)
    print("🚀 Live GPT-4 AI + Binance Testnet")
    print("🎯 Relaxed Risk Management for Demo")
    print("💰 Real Trade Execution on Testnet")
    print("━" * 60)
    
    try:
        # Setup logging
        setup_logger()
        
        # Load configuration
        config = Config()
        
        # Temporary demo adjustments
        config.max_portfolio_risk = 0.50  # 50% for demo
        config.max_open_positions = 500   # Allow many positions
        config.max_trade_amount = 5000.0  # Higher trade limits
        
        print(f"💰 Max Trade Amount: ${config.max_trade_amount:.0f}")
        print(f"🎯 Max Risk: {float(config.max_portfolio_risk)*100}% per trade")
        print(f"📊 Max Positions: {config.max_open_positions}")
        print("━" * 60)
        
        # Initialize trading bot
        bot = TradingBot(config)
        
        # Temporarily relax risk manager for demo
        original_evaluate_trade_risk = bot.risk_manager.evaluate_trade_risk
        
        def demo_risk_manager(action, symbol, allocation_percentage, portfolio_data, market_data, current_positions):
            """Demo risk manager that's more permissive."""
            risk_assessment = {
                "approved": True,
                "risk_score": 2.0,  # Medium risk
                "reason": "Demo mode - trade approved",
                "warnings": [],
                "adjustments": {}
            }
            
            # Still check basic limits
            available_balance = portfolio_data.get("available_balance", 0)
            trade_amount = (allocation_percentage / 100) * available_balance
            
            if trade_amount < config.min_trade_amount:
                risk_assessment["approved"] = False
                risk_assessment["reason"] = f"Trade amount ${trade_amount:.2f} below minimum ${config.min_trade_amount}"
                return risk_assessment
            
            if trade_amount > config.max_trade_amount:
                # Adjust to max instead of rejecting
                max_allocation = (config.max_trade_amount / available_balance) * 100
                risk_assessment["adjustments"]["allocation_percentage"] = max_allocation
                risk_assessment["warnings"].append(f"Position size adjusted to ${config.max_trade_amount:.0f} limit")
            
            return risk_assessment
        
        # Replace risk manager temporarily
        bot.risk_manager.evaluate_trade_risk = demo_risk_manager
        
        await bot.initialize()
        
        print("🧠 LIVE AI ANALYSIS & TRADE EXECUTION...")
        print("━" * 60)
        
        # Run trading cycle
        await bot.run_cycle()
        
        print("━" * 60)
        print("✅ LIVE TRADING DEMO COMPLETED!")
        print("🎯 Check logs for detailed trade information")
        
        await bot.shutdown()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_live_trading()) 