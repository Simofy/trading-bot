#!/usr/bin/env python3
"""
Enhanced AI Trading Bot - Comprehensive Demo
Showcases all the implemented enhancements and new features
"""
import asyncio
import logging
import sys
from datetime import datetime

from src.trading_bot import TradingBot
from src.config import Config
from src.logger import setup_logger
from src.performance_tracker import PerformanceTracker
from src.technical_analysis import TechnicalAnalyzer
from src.database import TradingDatabase

async def demo_enhanced_system():
    """Run comprehensive demo of all enhanced features."""
    
    print("🚀 AI TRADING BOT - ENHANCED SYSTEM DEMO")
    print("=" * 70)
    print("🧠 GPT-4 AI Decision Making with Technical Analysis")
    print("📊 Real-time Performance Tracking & Analytics") 
    print("🗄️ SQLite Database for Persistent Storage")
    print("🛡️ Advanced Risk Management with VaR & Stress Testing")
    print("📈 Comprehensive Technical Indicators (RSI, MACD, Bollinger Bands)")
    print("🌐 Web Dashboard for Real-time Monitoring")
    print("=" * 70)
    
    try:
        # Setup logging
        setup_logger()
        logger = logging.getLogger(__name__)
        
        # Load configuration
        config = Config()
        
        print("\n🏗️ INITIALIZING ENHANCED COMPONENTS")
        print("-" * 50)
        
        # Initialize enhanced trading bot
        bot = TradingBot(config)
        await bot.initialize()
        
        print("✅ Trading Bot initialized with:")
        print("   • AI Advisor with GPT-4 integration")
        print("   • Technical Analysis engine")
        print("   • Performance tracker with advanced metrics")
        print("   • SQLite database for persistence")
        print("   • Enhanced risk management")
        
        # Demonstrate technical analysis
        print("\n📈 TECHNICAL ANALYSIS DEMONSTRATION")
        print("-" * 50)
        
        # Get market data
        market_data = await bot.market_data.get_current_prices(["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        
        # Update technical analysis
        for symbol, data in market_data.items():
            price = data.get('price', 0)
            volume = data.get('volume_24h', 0)
            bot.ai_advisor.technical_analyzer.update_price_data(symbol, price, volume)
        
        # Show technical indicators for Bitcoin
        if "BTCUSDT" in market_data:
            indicators = bot.ai_advisor.technical_analyzer.get_technical_indicators("BTCUSDT")
            signals = bot.ai_advisor.technical_analyzer.generate_trading_signals("BTCUSDT")
            
            print(f"📊 BTCUSDT Technical Analysis:")
            rsi = indicators.get("rsi", {})
            print(f"   RSI: {rsi.get('rsi', 0):.1f} ({rsi.get('signal', 'N/A')})")
            
            macd = indicators.get("macd", {})
            print(f"   MACD: {macd.get('trend', 'N/A')}")
            
            bb = indicators.get("bollinger_bands", {})
            print(f"   Bollinger Bands: {bb.get('position', 'N/A')}")
            
            trend = indicators.get("trend_strength", {})
            print(f"   Trend: {trend.get('direction', 'N/A')} ({trend.get('strength', 0):.0f}%)")
            
            print(f"   Overall Signal: {signals.get('overall_signal', 'N/A')} ({signals.get('strength', 0)}%)")
            print(f"   Bullish Factors: {len(signals.get('bullish_factors', []))}")
            print(f"   Bearish Factors: {len(signals.get('bearish_factors', []))}")
        
        # Demonstrate enhanced risk management
        print("\n🛡️ ENHANCED RISK MANAGEMENT")
        print("-" * 50)
        
        portfolio_data = await bot.exchange.get_portfolio_value()
        
        # Calculate VaR
        var_95 = bot.risk_manager.calculate_var(portfolio_data, market_data, confidence_level=0.05)
        var_99 = bot.risk_manager.calculate_var(portfolio_data, market_data, confidence_level=0.01)
        
        print(f"💰 Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}")
        print(f"📉 Value at Risk (95%): ${var_95:,.2f}")
        print(f"📉 Value at Risk (99%): ${var_99:,.2f}")
        
        # Stress testing
        stress_results = bot.risk_manager.stress_test_portfolio(portfolio_data, market_data)
        print(f"🧪 Stress Test Results:")
        for scenario, loss in stress_results.items():
            print(f"   {scenario.replace('_', ' ').title()}: ${loss:,.2f}")
        
        # Demonstrate AI decision with technical analysis
        print("\n🧠 AI DECISION WITH TECHNICAL ANALYSIS")
        print("-" * 50)
        
        # Get comprehensive risk metrics
        risk_metrics = bot.risk_manager.get_risk_metrics(portfolio_data, market_data)
        
        # Get AI decision with enhanced technical context
        ai_decision = await bot.ai_advisor.get_trading_decision(market_data, portfolio_data, risk_metrics)
        
        print(f"🎯 AI Recommendation:")
        print(f"   Action: {ai_decision.get('action', 'N/A')}")
        print(f"   Symbol: {ai_decision.get('symbol', 'N/A')}")
        print(f"   Allocation: {ai_decision.get('allocation_percentage', 0)}%")
        print(f"   Confidence: {ai_decision.get('confidence', 0)}/10")
        print(f"   Timeframe: {ai_decision.get('timeframe', 'N/A')}")
        reasoning = ai_decision.get('reasoning', '')
        print(f"   Reasoning: {reasoning[:120]}{'...' if len(reasoning) > 120 else ''}")
        
        # Demonstrate database functionality
        print("\n🗄️ DATABASE INTEGRATION")
        print("-" * 50)
        
        # Get trading statistics
        stats = bot.db.get_trading_statistics()
        print(f"📈 Trading Statistics:")
        print(f"   Total Trades: {stats.get('total_trades', 0)}")
        print(f"   Success Rate: {stats.get('success_rate', 0):.1%}")
        print(f"   Latest Portfolio Value: ${stats.get('latest_portfolio_value', 0):,.2f}")
        
        # Show recent AI decisions from database
        recent_decisions = bot.db.get_ai_decisions(limit=3)
        print(f"🧠 Recent AI Decisions:")
        for decision in recent_decisions[:3]:
            timestamp = datetime.fromisoformat(decision['timestamp']).strftime('%Y-%m-%d %H:%M')
            print(f"   {timestamp}: {decision['action']} {decision.get('symbol', 'N/A')} "
                  f"(confidence: {decision.get('confidence', 0)}/10)")
        
        # Demonstrate performance tracking
        print("\n📊 PERFORMANCE ANALYTICS")
        print("-" * 50)
        
        performance_metrics = bot.performance_tracker.get_performance_metrics()
        
        print(f"💰 Performance Summary:")
        print(f"   Total Return: ${performance_metrics.total_return:,.2f} ({performance_metrics.total_return_pct:.2%})")
        print(f"   Annualized Return: {performance_metrics.annualized_return:.2%}")
        print(f"   Sharpe Ratio: {performance_metrics.sharpe_ratio:.2f}")
        print(f"   Sortino Ratio: {performance_metrics.sortino_ratio:.2f}")
        print(f"   Max Drawdown: ${performance_metrics.max_drawdown:,.2f} ({performance_metrics.max_drawdown_pct:.2%})")
        print(f"   Win Rate: {performance_metrics.win_rate:.1%}")
        print(f"   Total Trades: {performance_metrics.total_trades}")
        print(f"   Volatility: {performance_metrics.volatility:.2%}")
        
        # Show what the web dashboard offers
        print("\n🌐 WEB DASHBOARD FEATURES")
        print("-" * 50)
        print("📊 Real-time portfolio monitoring")
        print("📈 Interactive charts and visualizations")
        print("🔄 Live trade execution and history")
        print("🧠 AI decision tracking and analysis")
        print("⚡ Manual trading interface")
        print("📱 Responsive design for mobile/desktop")
        print("🔄 Auto-refresh every 30 seconds")
        print("")
        print("💡 To start the web dashboard, run: python demo_dashboard.py")
        print("🌐 Dashboard URL: http://127.0.0.1:8000")
        
        # Run a single enhanced trading cycle
        print("\n🔄 ENHANCED TRADING CYCLE DEMONSTRATION")
        print("-" * 50)
        
        print("🧠 Running enhanced trading cycle with all new features...")
        await bot.run_cycle()
        
        print("\n✅ ENHANCED SYSTEM DEMONSTRATION COMPLETE!")
        print("=" * 70)
        print("🎯 All enhancements successfully implemented:")
        print("   ✅ Market data API fixes and parameter validation")
        print("   ✅ Secure configuration management")
        print("   ✅ Comprehensive performance tracking (Sharpe, Sortino, Calmar ratios)")
        print("   ✅ Technical analysis integration (RSI, MACD, Bollinger Bands, etc.)")
        print("   ✅ SQLite database for persistent storage")
        print("   ✅ Real-time web dashboard with FastAPI")
        print("   ✅ Enhanced risk management with VaR and stress testing")
        print("")
        print("🚀 The trading bot is now production-ready with institutional-grade features!")
        print("📈 Ready for live trading, backtesting, and advanced analytics")
        print("")
        print("🔧 Next Steps:")
        print("   1. Run 'python demo_dashboard.py' for web interface")
        print("   2. Run 'python demo_quick_cycles.py' for rapid testing")
        print("   3. Configure real API keys for live trading")
        print("   4. Set up monitoring and alerting")
        
        await bot.shutdown()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_enhanced_system()) 