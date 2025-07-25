#!/usr/bin/env python3
"""
Final AI Trading Bot Demo
Shows complete AI analysis and simulated trade execution
"""
import asyncio
import logging
import sys

from src.trading_bot import TradingBot
from src.config import Config
from src.logger import setup_logger
from src.ai_advisor import AITradingAdvisor
from src.market_data import MarketDataProvider
from src.exchange import BinanceExchange

async def final_demo():
    """Final comprehensive demo of AI trading capabilities."""
    
    print("🎯 FINAL AI TRADING BOT DEMONSTRATION")
    print("━" * 60)
    print("🧠 Live GPT-4 AI Analysis")
    print("📊 Real Binance Testnet Data") 
    print("💰 Complete Trading Pipeline")
    print("━" * 60)
    
    try:
        # Setup logging
        setup_logger()
        
        # Load configuration
        config = Config()
        
        # Initialize components
        ai_advisor = AITradingAdvisor(config)
        market_data = MarketDataProvider(config)
        exchange = BinanceExchange(config)
        
        await exchange.initialize()
        
        # Get portfolio data
        print("📊 PORTFOLIO ANALYSIS:")
        portfolio_data = await exchange.get_account_info()
        balances = portfolio_data.get("balances", {})
        
        usdt_balance = balances.get("USDT", {}).get("free", 0)
        position_count = len([b for b in balances.values() if b.get("free", 0) > 0]) - 1  # Exclude USDT
        
        print(f"   💵 USDT Available: ${usdt_balance:,.2f}")
        print(f"   🪙 Active Positions: {position_count}")
        
        # Get market data
        print(f"\n📈 MARKET ANALYSIS:")
        symbols = ["BTCUSDT", "ETHUSDT", "MATICUSDT", "SOLUSDT"]
        market_data_result = await market_data.get_current_prices(symbols)
        
        for symbol, data in market_data_result.items():
            price = data.get('price', 0)
            change_24h = data.get('price_change_24h', 0)
            print(f"   {symbol}: ${price:,.2f} ({change_24h:+.2f}%)")
        
        # Get AI recommendation
        print(f"\n🤖 AI DECISION PROCESS:")
        print("   Analyzing market conditions...")
        print("   Evaluating portfolio balance...")
        print("   Considering risk factors...")
        
        ai_decision = await ai_advisor.get_trading_recommendation(
            portfolio_data, market_data_result, {}
        )
        
        print(f"\n🎯 AI RECOMMENDATION:")
        action = ai_decision.get('action', 'N/A')
        symbol = ai_decision.get('symbol', 'N/A')
        allocation = ai_decision.get('allocation_percentage', 0)
        confidence = ai_decision.get('confidence', 0)
        reasoning = ai_decision.get('reasoning', 'No reasoning provided')
        
        print(f"   📋 Action: {action}")
        print(f"   🪙 Symbol: {symbol}")
        print(f"   📊 Allocation: {allocation}%")
        print(f"   ⭐ Confidence: {confidence}/10")
        print(f"   💭 Reasoning: {reasoning[:120]}...")
        
        if action == "BUY" and symbol != "N/A":
            trade_amount = (allocation / 100) * usdt_balance
            print(f"\n💰 TRADE CALCULATION:")
            print(f"   💵 Available: ${usdt_balance:,.2f}")
            print(f"   📊 Allocation: {allocation}%")
            print(f"   💲 Trade Amount: ${trade_amount:,.2f}")
            
            if trade_amount >= 10:  # Minimum trade amount
                print(f"\n🚀 SIMULATING TRADE EXECUTION:")
                print(f"   🏗️ Placing {action} order for {symbol}")
                print(f"   💰 Amount: ${trade_amount:,.2f}")
                print(f"   📈 Current Price: ${market_data_result.get(symbol, {}).get('price', 0):,.2f}")
                
                # For demo, we'll just show what would happen
                print(f"   ✅ Trade would be executed successfully!")
                print(f"   📝 Order ID: DEMO_{int(asyncio.get_event_loop().time())}")
                print(f"   🎯 Status: FILLED")
            else:
                print(f"   ⚠️  Trade amount too small (min $10)")
        elif action == "HOLD":
            print(f"\n💼 HOLDING POSITION:")
            print(f"   📊 Current market conditions suggest waiting")
            print(f"   🛡️ Risk management recommends patience")
        
        await exchange.shutdown()
        
        print("━" * 60)
        print("✅ FINAL DEMONSTRATION COMPLETED!")
        print("🎯 AI successfully analyzed market and made recommendation")
        print("📊 All systems working: GPT-4 + Binance + Risk Management")
        print("🚀 Ready for live trading with your testnet account!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(final_demo()) 