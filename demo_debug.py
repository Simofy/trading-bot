#!/usr/bin/env python3
"""
Debug AI Trading Bot Demo
Shows detailed risk analysis and AI decision process
"""
import asyncio
import logging
import sys
from datetime import datetime

from src.trading_bot import TradingBot
from src.config import Config
from src.logger import setup_logger

async def debug_trading_cycle():
    """Run a detailed debug of the trading cycle."""
    
    print("🔬 AI TRADING BOT - DEBUG MODE")
    print("━" * 60)
    print("✅ Live GPT-4 AI + Binance Testnet")
    print("✅ Detailed Risk Analysis")
    print("✅ Step-by-Step Process Debugging")
    print("━" * 60)
    
    try:
        # Setup logging with debug level
        setup_logger()
        
        # Load configuration
        config = Config()
        print(f"💰 Portfolio: ${config.min_trade_amount:.0f}-${config.max_trade_amount:.0f} per trade")
        print(f"🎯 Max Risk: {float(config.max_portfolio_risk)*100}% per trade")
        print(f"📊 Max Positions: {config.max_open_positions}")
        print("━" * 60)
        
        # Initialize trading bot
        bot = TradingBot(config)
        await bot.initialize()
        
        print("🔍 PORTFOLIO ANALYSIS:")
        portfolio_data = await bot.exchange.get_account_info()
        balances = portfolio_data.get("balances", {})
        
        total_value = 0
        usdt_balance = 0
        position_count = 0
        
        for asset, balance_info in balances.items():
            free = balance_info.get("free", 0)
            if free > 0:
                if asset == "USDT":
                    usdt_balance = free
                    total_value += free
                    print(f"   💵 {asset}: ${free:,.2f}")
                else:
                    position_count += 1
                    # Estimate value (simplified)
                    estimated_value = free * 100  # Rough estimate
                    total_value += estimated_value
                    print(f"   🪙 {asset}: {free:.4f} (~${estimated_value:,.0f})")
        
        print(f"\n📊 PORTFOLIO SUMMARY:")
        print(f"   💰 Total Value: ~${total_value:,.2f}")
        print(f"   💵 USDT Available: ${usdt_balance:,.2f}")
        print(f"   📈 Active Positions: {position_count}")
        
        print(f"\n🧠 QUERYING GPT-4 AI...")
        
        # Get market data
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT", "SOLUSDT", "MATICUSDT", "AVAXUSDT"]
        market_data = await bot.market_data_provider.get_current_prices(symbols)
        
        print(f"📈 MARKET DATA:")
        for symbol, data in market_data.items():
            price = data.get('price', 0)
            change_24h = data.get('price_change_24h', 0)
            print(f"   {symbol}: ${price:,.2f} ({change_24h:+.2f}%)")
        
        # Get AI decision
        ai_decision = await bot.ai_advisor.get_trading_recommendation(
            portfolio_data, market_data, {}
        )
        
        print(f"\n🤖 AI DECISION:")
        print(f"   Action: {ai_decision.get('action', 'N/A')}")
        print(f"   Symbol: {ai_decision.get('symbol', 'N/A')}")
        print(f"   Allocation: {ai_decision.get('allocation_percentage', 0)}%")
        print(f"   Confidence: {ai_decision.get('confidence', 0)}/10")
        print(f"   Reasoning: {ai_decision.get('reasoning', 'N/A')[:100]}...")
        
        # Test risk evaluation
        if ai_decision.get('action') in ['BUY', 'SELL']:
            print(f"\n🛡️ RISK ANALYSIS:")
            
            # Calculate trade amount
            allocation_pct = ai_decision.get('allocation_percentage', 0)
            trade_amount = (allocation_pct / 100) * usdt_balance
            
            print(f"   💰 Trade Amount: ${trade_amount:.2f} ({allocation_pct}% of ${usdt_balance:.2f})")
            print(f"   📊 Current Positions: {position_count}/{config.max_open_positions}")
            print(f"   🎯 Max Risk Per Trade: {float(config.max_portfolio_risk)*100}%")
            print(f"   💵 Min Trade Amount: ${config.min_trade_amount}")
            print(f"   💵 Max Trade Amount: ${config.max_trade_amount}")
            
            # Check specific risk factors
            risk_factors = []
            
            if trade_amount < float(config.min_trade_amount):
                risk_factors.append(f"Trade amount ${trade_amount:.2f} < min ${config.min_trade_amount}")
            
            if trade_amount > float(config.max_trade_amount):
                risk_factors.append(f"Trade amount ${trade_amount:.2f} > max ${config.max_trade_amount}")
            
            if allocation_pct > float(config.max_portfolio_risk) * 100:
                risk_factors.append(f"Allocation {allocation_pct}% > max {float(config.max_portfolio_risk)*100}%")
            
            if position_count >= config.max_open_positions and ai_decision.get('action') == 'BUY':
                risk_factors.append(f"Positions {position_count} >= max {config.max_open_positions}")
            
            if risk_factors:
                print(f"   ❌ RISK FACTORS:")
                for factor in risk_factors:
                    print(f"      • {factor}")
                print(f"   🚫 TRADE WOULD BE REJECTED")
            else:
                print(f"   ✅ ALL RISK CHECKS PASSED")
                print(f"   🚀 TRADE WOULD BE EXECUTED")
        
        await bot.shutdown()
        
        print("━" * 60)
        print("🎯 Debug analysis completed!")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_trading_cycle()) 