#!/usr/bin/env python3
"""
Binance Testnet Connection Test
Tests your testnet API keys and shows account information
"""
import asyncio
import sys
from decimal import Decimal

from src.config import Config
from src.exchange import BinanceExchange
from src.logger import setup_logger

async def test_testnet_connection():
    """Test Binance testnet connection and display account info."""
    
    print("🔍 BINANCE TESTNET CONNECTION TEST")
    print("━" * 60)
    
    try:
        # Setup logging
        setup_logger()
        
        # Load configuration
        config = Config()
        
        print(f"🔑 API Key: {config.binance_api_key[:10]}...")
        print(f"🔐 Secret Key: {config.binance_secret_key[:10]}...")
        print(f"🏗️ Use Sandbox: {config.use_sandbox}")
        print("━" * 60)
        
        # Initialize exchange
        exchange = BinanceExchange(config)
        
        print("⏳ Connecting to Binance Testnet...")
        await exchange.initialize()
        
        if exchange.use_binance_testnet:
            print("✅ Successfully connected to Binance Testnet!")
            
            # Get account info
            print("\n📊 Testnet Account Information:")
            account_info = await exchange.get_account_info()
            
            if account_info:
                balances = account_info.get("balances", {})
                
                print(f"📝 Account Type: {account_info.get('account_type', 'Unknown')}")
                print(f"💹 Trading Enabled: {account_info.get('trading_enabled', False)}")
                
                print("\n💰 Available Balances:")
                for asset, balance_info in balances.items():
                    free = balance_info.get("free", 0)
                    if free > 0:
                        print(f"   {asset}: {free:.8f}")
                
                if not any(balance.get("free", 0) > 0 for balance in balances.values()):
                    print("   ⚠️  No funds found!")
                    print("   💡 Get free testnet funds at: https://testnet.binance.vision/en/faucet")
                
                # Test a simple API call
                print("\n🔄 Testing ticker price fetch...")
                ticker = await exchange.get_ticker_price("BTCUSDT")
                if ticker:
                    print(f"   BTC Price: ${float(ticker.get('price', 0)):,.2f}")
                
                print("\n🎯 Testnet connection test PASSED!")
                print("✅ Ready for live testnet trading!")
                
            else:
                print("❌ Failed to get account information")
                
        else:
            print("⚠️  Running in demo mode")
            if not config.use_sandbox:
                print("   💡 Set USE_SANDBOX=true in .env file")
            if not config.binance_api_key:
                print("   💡 Add BINANCE_API_KEY to .env file")
            if not config.binance_secret_key:
                print("   💡 Add BINANCE_SECRET_KEY to .env file")
        
        await exchange.shutdown()
        
    except Exception as e:
        print(f"❌ Testnet connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your API keys are correct")
        print("   2. Ensure keys have 'Enable Reading' and 'Enable Spot Trading' permissions")
        print("   3. Verify you're using TESTNET keys from https://testnet.binance.vision/")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_testnet_connection()) 