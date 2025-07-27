#!/usr/bin/env python3
"""
Check the minimum order requirements for ETHUSDT on Binance.
Test the NOTIONAL filter fix.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def check_ethusdt_minimum():
    """Check the minimum order requirements for ETHUSDT and test our NOTIONAL filter fix."""
    print("🔍 Testing NOTIONAL Filter Fix for ETHUSDT")
    print("=" * 50)
    
    try:
        from src.config import Config
        from src.exchange import BinanceExchange
        
        config = Config()
        exchange = BinanceExchange(config)
        await exchange.initialize()
        
        # Get symbol info for ETHUSDT (the failing symbol)
        symbol_info = await exchange.get_symbol_info("ETHUSDT")
        
        print(f"📊 ETHUSDT Trading Requirements:")
        print(f"   Symbol: {symbol_info.get('symbol', 'N/A')}")
        print(f"   Status: {symbol_info.get('status', 'N/A')}")
        print(f"   Minimum Quantity: {symbol_info.get('min_qty', 'N/A')}")
        print(f"   Minimum Notional: ${symbol_info.get('min_notional', 'N/A')}")
        print(f"   Base Asset: {symbol_info.get('base_asset', 'N/A')}")
        print(f"   Quote Asset: {symbol_info.get('quote_asset', 'N/A')}")
        
        min_notional = symbol_info.get('min_notional', 0)
        portfolio_value = 14.70  # From the error logs
        
        if min_notional:
            print(f"\n💡 Analysis of the Failed Trade:")
            print(f"   Your Portfolio: ${portfolio_value}")
            print(f"   ETHUSDT Minimum: ${min_notional}")
            print(f"   Required %: {(min_notional / portfolio_value) * 100:.1f}% of portfolio")
            
            if min_notional <= portfolio_value:
                print(f"✅ Portfolio meets minimum (need ${min_notional:.2f})")
                print(f"   🔧 If this shows passing but trading failed, there may be another issue")
            else:
                print(f"❌ Portfolio below minimum (need ${min_notional:.2f}, have ${portfolio_value})")
                print(f"   🎯 This explains the NOTIONAL filter failure!")
        
        # Check other supported symbols for comparison
        print(f"\n📋 Comparing Other Supported Symbols:")
        print("-" * 40)
        
        symbols_to_check = ["BTCUSDT", "ADAUSDT", "DOTUSDT", "SOLUSDT", "LINKUSDT"]
        
        for symbol in symbols_to_check:
            try:
                info = await exchange.get_symbol_info(symbol)
                min_not = info.get('min_notional', 0)
                status = info.get('status', 'N/A')
                
                if min_not <= portfolio_value:
                    status_icon = "✅"
                else:
                    status_icon = "❌"
                    
                print(f"   {status_icon} {symbol}: ${min_not:.2f} (Status: {status})")
            except Exception as e:
                print(f"   ❓ {symbol}: Error getting info - {e}")
                
        print(f"\n🎯 Recommendation:")
        tradeable_symbols = []
        for symbol in symbols_to_check:
            try:
                info = await exchange.get_symbol_info(symbol)
                min_not = info.get('min_notional', 0)
                if min_not <= portfolio_value and info.get('status') == 'TRADING':
                    tradeable_symbols.append((symbol, min_not))
            except:
                pass
                
        if tradeable_symbols:
            print(f"   With ${portfolio_value}, you can trade:")
            for symbol, min_not in sorted(tradeable_symbols, key=lambda x: x[1]):
                print(f"     • {symbol} (min: ${min_not:.2f})")
        else:
            print(f"   With ${portfolio_value}, no symbols meet minimum requirements")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_ethusdt_minimum()) 