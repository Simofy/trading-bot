#!/usr/bin/env python3
"""
Check which symbols are actually available for trading on this Binance account.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def check_available_symbols():
    """Check which symbols are available for trading."""
    print("🔍 Checking Available Symbols for Your Account")
    print("=" * 50)
    
    try:
        from src.config import Config
        from src.exchange import BinanceExchange
        
        config = Config()
        exchange = BinanceExchange(config)
        await exchange.initialize()
        
        print(f"📊 Testing All Supported Symbols:")
        print("-" * 30)
        
        available_symbols = []
        restricted_symbols = []
        
        for symbol in config.supported_symbols:
            try:
                # Try to get current price (this checks if symbol is available)
                ticker = await exchange.get_ticker_price(symbol)
                price_str = ticker.get("price", "0")
                price = float(price_str) if price_str else 0
                
                if price > 0:
                    # Get minimum requirements
                    symbol_info = await exchange.get_symbol_info(symbol)
                    min_notional = symbol_info.get("min_notional", 0)
                    
                    # Check if we can afford this symbol
                    portfolio_value = 14.70
                    required_percent = (min_notional / portfolio_value) * 100
                    can_afford = required_percent <= 75  # Our max risk
                    
                    status = "✅ CAN TRADE" if can_afford else "⚠️  TOO EXPENSIVE"
                    available_symbols.append(symbol)
                    
                    print(f"   {symbol}: ${price:.4f} | Min: ${min_notional:.1f} | Need: {required_percent:.1f}% | {status}")
                else:
                    restricted_symbols.append(symbol)
                    print(f"   {symbol}: ❌ No price data (restricted?)")
                    
            except Exception as e:
                restricted_symbols.append(symbol)
                print(f"   {symbol}: ❌ Error - {str(e)[:50]}...")
        
        print(f"\n📋 Summary:")
        print(f"   ✅ Available symbols: {len(available_symbols)}")
        print(f"   ❌ Restricted symbols: {len(restricted_symbols)}")
        
        if available_symbols:
            print(f"\n🎯 Recommended symbols for your account:")
            for symbol in available_symbols:
                try:
                    symbol_info = await exchange.get_symbol_info(symbol)
                    min_notional = symbol_info.get("min_notional", 0)
                    required_percent = (min_notional / 14.70) * 100
                    if required_percent <= 75:
                        print(f"   🟢 {symbol} (need {required_percent:.1f}% of portfolio)")
                except:
                    continue
        
        await exchange.shutdown()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await check_available_symbols()

if __name__ == "__main__":
    asyncio.run(main()) 