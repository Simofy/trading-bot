#!/usr/bin/env python3
"""
Quick Balance Checker
Simple script to check real Binance API balance
"""
import asyncio
import sys
from src.config import Config
from src.exchange import BinanceExchange

async def check_balance():
    """Check and display current account balance from Binance API."""
    
    print("💰 BINANCE BALANCE CHECKER")
    print("=" * 40)
    
    try:
        # Load configuration
        config = Config()
        
        # Initialize exchange
        exchange = BinanceExchange(config)
        
        # Show connection mode
        print(f"🔧 Connection Mode:")
        if exchange.use_binance_live:
            print("   📡 LIVE API (Real Trading)")
        elif exchange.use_binance_testnet:
            print("   🧪 TESTNET API (Paper Trading)")
        else:
            print("   🎮 DEMO MODE (Simulated)")
        
        print("\n🔌 Connecting...")
        await exchange.initialize()
        
        # Get account info
        account_info = await exchange.get_account_info()
        account_type = account_info.get("account_type", "UNKNOWN")
        
        print(f"✅ Connected to {account_type}")
        print("\n💼 ACCOUNT BALANCES:")
        print("-" * 40)
        
        balances = account_info.get("balances", {})
        
        if not balances:
            print("   No balances found")
        else:
            total_usd_value = 0
            
            for asset, balance_info in balances.items():
                free = balance_info.get("free", 0)
                locked = balance_info.get("locked", 0)
                total = balance_info.get("total", 0)
                
                if total > 0:
                    if asset == "USDT":
                        total_usd_value += total
                        print(f"   💵 {asset:>8}: ${total:>12,.2f}")
                    else:
                        print(f"   🪙 {asset:>8}: {total:>12,.6f}")
                        # Try to get USD value
                        try:
                            ticker = await exchange.get_ticker_price(f"{asset}USDT")
                            price = float(ticker.get("price", 0))
                            usd_value = total * price
                            total_usd_value += usd_value
                            print(f"                 (~${usd_value:,.2f} USD)")
                        except:
                            pass
        
        print("-" * 40)
        print(f"📊 ESTIMATED TOTAL: ~${total_usd_value:,.2f} USD")
        
        # Show trading permissions
        if account_info.get("trading_enabled"):
            print("✅ Trading: Enabled")
        else:
            print("❌ Trading: Disabled")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
        
    finally:
        # Clean up connection
        if hasattr(exchange, 'client') and exchange.client:
            await exchange.client.close_connection()
            print("\n🔌 Connection closed")

if __name__ == "__main__":
    asyncio.run(check_balance()) 