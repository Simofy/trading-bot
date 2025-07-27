#!/usr/bin/env python3
"""
Complete API Validation Script
Tests both Binance and CoinGecko APIs with comprehensive diagnostics
"""
import asyncio
import sys
import aiohttp
from datetime import datetime
from decimal import Decimal

from src.config import Config
from src.exchange import BinanceExchange
from src.market_data import MarketDataProvider
from src.logger import setup_logger


class APIValidator:
    """Comprehensive API validation for the trading bot."""
    
    def __init__(self):
        self.config = Config()
        self.results = {
            'binance': {'status': 'pending', 'details': []},
            'coingecko': {'status': 'pending', 'details': []},
            'overall': {'status': 'pending', 'critical_issues': []}
        }
    
    async def validate_all_apis(self):
        """Run complete API validation suite."""
        print("🔍 COMPREHENSIVE API VALIDATION")
        print("=" * 80)
        print(f"⏰ Validation started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Validate Binance API
        await self.validate_binance_api()
        print()
        
        # Validate CoinGecko API
        await self.validate_coingecko_api()
        print()
        
        # Display summary
        self.display_summary()
        
        return self.results
    
    async def validate_binance_api(self):
        """Comprehensive Binance API validation."""
        print("📊 BINANCE API VALIDATION")
        print("-" * 40)
        
        try:
            # Check API key configuration
            print("🔑 Checking API Configuration...")
            print(f"   Sandbox Mode: {self.config.use_sandbox}")
            
            if self.config.use_sandbox:
                print("   🧪 Using TESTNET mode")
                has_api_key = bool(self.config.binance_testnet_api_key and len(self.config.binance_testnet_api_key) > 20)
                has_secret = bool(self.config.binance_testnet_secret_key and len(self.config.binance_testnet_secret_key) > 20)
                
                if not has_api_key:
                    self.results['binance']['details'].append("❌ Binance testnet API key missing or too short")
                    if not self.config.binance_testnet_api_key:
                        print("   ❌ BINANCE_TESTNET_API_KEY not configured")
                else:
                    self.results['binance']['details'].append("✅ Binance testnet API key configured")
                    print(f"   Testnet API Key: {self.config.binance_testnet_api_key[:10]}...{self.config.binance_testnet_api_key[-4:]}")
                
                if not has_secret:
                    self.results['binance']['details'].append("❌ Binance testnet secret key missing or too short")
                    if not self.config.binance_testnet_secret_key:
                        print("   ❌ BINANCE_TESTNET_SECRET_KEY not configured")
                else:
                    self.results['binance']['details'].append("✅ Binance testnet secret key configured")
                    print(f"   Testnet Secret Key: {self.config.binance_testnet_secret_key[:10]}...{self.config.binance_testnet_secret_key[-4:]}")
                    
            else:
                print("   🚀 Using LIVE mode")
                has_api_key = bool(self.config.binance_live_api_key and len(self.config.binance_live_api_key) > 20)
                has_secret = bool(self.config.binance_live_secret_key and len(self.config.binance_live_secret_key) > 20)
                
                if not has_api_key:
                    self.results['binance']['details'].append("❌ Binance live API key missing or too short")
                    self.results['overall']['critical_issues'].append("Binance live API key not configured")
                    print("   ❌ BINANCE_LIVE_API_KEY not configured")
                else:
                    self.results['binance']['details'].append("✅ Binance live API key configured")
                    print(f"   Live API Key: {self.config.binance_live_api_key[:10]}...{self.config.binance_live_api_key[-4:]}")
                
                if not has_secret:
                    self.results['binance']['details'].append("❌ Binance live secret key missing or too short")
                    self.results['overall']['critical_issues'].append("Binance live secret key not configured")
                    print("   ❌ BINANCE_LIVE_SECRET_KEY not configured")
                else:
                    self.results['binance']['details'].append("✅ Binance live secret key configured")
                    print(f"   Live Secret Key: {self.config.binance_live_secret_key[:10]}...{self.config.binance_live_secret_key[-4:]}")
            
            # For backward compatibility, show warning if old env vars are still being used
            if not has_api_key and not has_secret:
                if self.config.use_sandbox and (not self.config.binance_testnet_api_key and not self.config.binance_testnet_secret_key):
                    self.results['overall']['critical_issues'].append("Binance testnet API keys not configured")
            
            # Test exchange initialization
            print("\n🏗️ Testing Exchange Connection...")
            exchange = BinanceExchange(self.config)
            
            await exchange.initialize()
            
            if exchange.use_binance_testnet:
                print("✅ Connected to Binance Testnet successfully!")
                self.results['binance']['details'].append("✅ Testnet connection successful")
                
                # Test account info
                print("\n📊 Testing Account Information...")
                account_info = await exchange.get_account_info()
                
                if account_info:
                    print("✅ Account info retrieved successfully")
                    self.results['binance']['details'].append("✅ Account info accessible")
                    
                    balances = account_info.get("balances", {})
                    trading_enabled = account_info.get("trading_enabled", False)
                    
                    print(f"   Trading Enabled: {trading_enabled}")
                    print(f"   Available Assets: {len(balances)}")
                    
                    # Show non-zero balances
                    non_zero_balances = {asset: bal for asset, bal in balances.items() 
                                       if bal.get("free", 0) > 0}
                    
                    if non_zero_balances:
                        print("   💰 Balances:")
                        for asset, balance in non_zero_balances.items():
                            print(f"      {asset}: {balance.get('free', 0):.8f}")
                        self.results['binance']['details'].append(f"✅ Found {len(non_zero_balances)} funded assets")
                    else:
                        print("   ⚠️  No testnet funds found")
                        print("   💡 Get free testnet funds at: https://testnet.binance.vision/en/faucet")
                        self.results['binance']['details'].append("⚠️ No testnet funds available")
                
                # Test market data
                print("\n📈 Testing Market Data...")
                try:
                    ticker = await exchange.get_ticker_price("BTCUSDT")
                    if ticker and 'price' in ticker:
                        price = float(ticker['price'])
                        print(f"   BTC/USDT Price: ${price:,.2f}")
                        self.results['binance']['details'].append("✅ Market data retrieval working")
                    else:
                        print("   ❌ Failed to get ticker price")
                        self.results['binance']['details'].append("❌ Market data retrieval failed")
                except Exception as e:
                    print(f"   ❌ Market data error: {e}")
                    self.results['binance']['details'].append(f"❌ Market data error: {e}")
                
                # Test order book
                print("\n📖 Testing Order Book...")
                try:
                    order_book = await exchange.get_order_book("BTCUSDT", limit=5)
                    if order_book and 'bids' in order_book and 'asks' in order_book:
                        print(f"   Order book depth: {len(order_book['bids'])} bids, {len(order_book['asks'])} asks")
                        self.results['binance']['details'].append("✅ Order book data accessible")
                    else:
                        print("   ❌ Failed to get order book")
                        self.results['binance']['details'].append("❌ Order book retrieval failed")
                except Exception as e:
                    print(f"   ❌ Order book error: {e}")
                    self.results['binance']['details'].append(f"❌ Order book error: {e}")
                
                self.results['binance']['status'] = 'success'
                
            elif exchange.use_binance_live:
                print("🚀 Connected to Binance Live API successfully!")
                self.results['binance']['details'].append("✅ Live API connection successful")
                
                # Test account info
                print("\n📊 Testing Live Account Information...")
                account_info = await exchange.get_account_info()
                
                if account_info:
                    print("✅ Live account info retrieved successfully")
                    self.results['binance']['details'].append("✅ Live account info accessible")
                    
                    balances = account_info.get("balances", {})
                    account_type = account_info.get("accountType", "UNKNOWN")
                    
                    print(f"   Account Type: {account_type}")
                    print(f"   Available Assets: {len(balances)}")
                    self.results['binance']['details'].append(f"✅ Live account type: {account_type}")
                    
                    # Show non-zero balances (but limit for privacy)
                    non_zero_balances = {asset: bal for asset, bal in balances.items() 
                                       if bal.get("free", 0) > 0}
                    
                    if non_zero_balances:
                        print(f"   💰 Non-zero balances: {len(non_zero_balances)} assets")
                        self.results['binance']['details'].append(f"✅ Found {len(non_zero_balances)} funded assets")
                    else:
                        print("   ⚠️  No available balances found")
                        self.results['binance']['details'].append("⚠️ No available balances")
                
                # Test market data
                print("\n📈 Testing Live Market Data...")
                try:
                    ticker = await exchange.get_ticker_price("BTCUSDT")
                    if ticker and 'price' in ticker:
                        price = float(ticker['price'])
                        print(f"   BTC/USDT Live Price: ${price:,.2f}")
                        self.results['binance']['details'].append("✅ Live market data retrieval working")
                    else:
                        print("   ❌ Failed to get live ticker price")
                        self.results['binance']['details'].append("❌ Live market data retrieval failed")
                except Exception as e:
                    print(f"   ❌ Live market data error: {e}")
                    self.results['binance']['details'].append(f"❌ Live market data error: {e}")
                
                self.results['binance']['status'] = 'success'
                
            elif exchange.demo_mode:
                print("⚠️  Running in demo mode (no real API connection)")
                self.results['binance']['details'].append("⚠️ Demo mode - no real API connection")
                self.results['binance']['status'] = 'demo'
                
                # Test demo functionality
                account_info = await exchange.get_account_info()
                if account_info:
                    print(f"   Demo balance: ${account_info.get('demo_balance', 0):,.2f}")
                    self.results['binance']['details'].append("✅ Demo mode functioning")
            
            await exchange.shutdown()
            
        except Exception as e:
            print(f"❌ Binance API validation failed: {e}")
            self.results['binance']['status'] = 'failed'
            self.results['binance']['details'].append(f"❌ Validation failed: {e}")
            self.results['overall']['critical_issues'].append(f"Binance API error: {e}")
            
            # Troubleshooting suggestions
            print("\n🔧 Binance Troubleshooting:")
            if not has_api_key or not has_secret:
                if self.config.use_sandbox:
                    print("   1. Get TESTNET API keys from: https://testnet.binance.vision/")
                    print("   2. Add them to .env as BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_SECRET_KEY")
                    print("   3. Testnet keys are FREE and safe for testing")
                else:
                    print("   1. Get LIVE API keys from: https://www.binance.com/en/my/settings/api-management")
                    print("   2. Add them to .env as BINANCE_LIVE_API_KEY and BINANCE_LIVE_SECRET_KEY")
                    print("   3. ⚠️  WARNING: Live keys can access real funds!")
            print("   4. Ensure keys have 'Enable Reading' and 'Enable Spot Trading' permissions")
            print("   5. Check network connectivity")
            
            if self.config.use_sandbox:
                print("   💡 Note: You're in TESTNET mode - use testnet.binance.vision for API keys")
            else:
                print("   💡 Note: You're in LIVE mode - use www.binance.com for API keys")
    
    async def validate_coingecko_api(self):
        """Comprehensive CoinGecko API validation."""
        print("🦎 COINGECKO API VALIDATION")
        print("-" * 40)
        
        try:
            # Check API key configuration
            print("🔑 Checking CoinGecko Configuration...")
            
            has_api_key = bool(self.config.coingecko_api_key)
            
            if has_api_key:
                print(f"   Pro API Key: {self.config.coingecko_api_key[:10]}...{self.config.coingecko_api_key[-4:]}")
                self.results['coingecko']['details'].append("✅ CoinGecko Pro API key configured")
            else:
                print("   Free API (no key configured)")
                self.results['coingecko']['details'].append("ℹ️ Using free CoinGecko API tier")
            
            # Initialize market data provider
            print("\n🏗️ Testing CoinGecko Connection...")
            market_data_provider = MarketDataProvider(self.config)
            
            # Test basic API connectivity
            print("\n🌐 Testing API Connectivity...")
            base_url = "https://api.coingecko.com/api/v3/ping"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('gecko_says') == '(V3) To the Moon!':
                            print("✅ CoinGecko API is reachable")
                            self.results['coingecko']['details'].append("✅ API connectivity confirmed")
                        else:
                            print("⚠️ Unexpected response from CoinGecko")
                            self.results['coingecko']['details'].append("⚠️ Unexpected API response")
                    else:
                        print(f"❌ CoinGecko API returned status {response.status}")
                        self.results['coingecko']['details'].append(f"❌ API returned status {response.status}")
            
            # Test market data retrieval
            print("\n📊 Testing Market Data Retrieval...")
            test_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
            
            try:
                market_data = await market_data_provider.get_current_prices(test_symbols)
                
                if market_data:
                    print(f"✅ Retrieved data for {len(market_data)} symbols")
                    self.results['coingecko']['details'].append(f"✅ Market data for {len(market_data)} symbols")
                    
                    # Display sample data
                    for symbol in test_symbols[:2]:  # Show first 2
                        if symbol in market_data:
                            data = market_data[symbol]
                            print(f"   {symbol}: ${data.get('price', 0):,.2f} "
                                f"({data.get('price_change_24h', 0):+.2f}%)")
                    
                    # Check data quality
                    sample_data = next(iter(market_data.values()))
                    required_fields = ['price', 'volume_24h', 'market_cap']
                    missing_fields = [field for field in required_fields if field not in sample_data]
                    
                    if missing_fields:
                        print(f"   ⚠️ Missing fields: {missing_fields}")
                        self.results['coingecko']['details'].append(f"⚠️ Missing data fields: {missing_fields}")
                    else:
                        print("   ✅ All required data fields present")
                        self.results['coingecko']['details'].append("✅ Complete data structure")
                    
                else:
                    print("❌ No market data retrieved")
                    self.results['coingecko']['details'].append("❌ No market data retrieved")
                
            except Exception as e:
                print(f"❌ Market data error: {e}")
                self.results['coingecko']['details'].append(f"❌ Market data error: {e}")
            
            # Test rate limiting
            print("\n⏱️ Testing Rate Limiting...")
            try:
                # Make multiple requests to test rate limiting
                start_time = datetime.now()
                
                for i in range(3):
                    await market_data_provider.get_current_prices(["BTCUSDT"])
                    if i < 2:  # Don't sleep after last request
                        await asyncio.sleep(0.1)  # Small delay between requests
                
                end_time = datetime.now()
                total_time = (end_time - start_time).total_seconds()
                
                print(f"   ✅ Made 3 requests in {total_time:.2f} seconds")
                if total_time > 3:  # If it took more than 3 seconds for 3 requests
                    print("   ✅ Rate limiting appears to be working")
                    self.results['coingecko']['details'].append("✅ Rate limiting functional")
                else:
                    print("   ℹ️ Rate limiting not triggered (normal for low volume)")
                    self.results['coingecko']['details'].append("ℹ️ Rate limiting not triggered")
                
            except Exception as e:
                print(f"   ⚠️ Rate limiting test error: {e}")
                self.results['coingecko']['details'].append(f"⚠️ Rate limiting test error: {e}")
            
            # Test global market data
            print("\n🌍 Testing Global Market Data...")
            try:
                global_data = await market_data_provider.get_market_overview()
                
                if global_data:
                    print("✅ Global market data retrieved")
                    if 'total_market_cap' in global_data:
                        market_cap = global_data['total_market_cap']
                        print(f"   Total Market Cap: ${market_cap:,.0f}")
                    self.results['coingecko']['details'].append("✅ Global market data accessible")
                else:
                    print("❌ Failed to get global market data")
                    self.results['coingecko']['details'].append("❌ Global market data failed")
                    
            except Exception as e:
                print(f"❌ Global data error: {e}")
                self.results['coingecko']['details'].append(f"❌ Global data error: {e}")
            
            # Determine overall status
            failed_tests = [detail for detail in self.results['coingecko']['details'] if detail.startswith('❌')]
            if failed_tests:
                self.results['coingecko']['status'] = 'partial'
                print(f"\n⚠️ CoinGecko validation completed with {len(failed_tests)} issues")
            else:
                self.results['coingecko']['status'] = 'success'
                print("\n✅ CoinGecko validation completed successfully")
            
        except Exception as e:
            print(f"❌ CoinGecko API validation failed: {e}")
            self.results['coingecko']['status'] = 'failed'
            self.results['coingecko']['details'].append(f"❌ Validation failed: {e}")
            self.results['overall']['critical_issues'].append(f"CoinGecko API error: {e}")
            
            # Troubleshooting suggestions
            print("\n🔧 CoinGecko Troubleshooting:")
            print("   1. Check internet connectivity")
            print("   2. Consider getting a Pro API key for higher rate limits")
            print("   3. Verify CoinGecko service status at: https://status.coingecko.com/")
    
    def display_summary(self):
        """Display comprehensive validation summary."""
        print("📋 VALIDATION SUMMARY")
        print("=" * 80)
        
        # Binance Summary
        binance_status = self.results['binance']['status']
        if binance_status == 'success':
            print("🟢 Binance API: FULLY OPERATIONAL")
        elif binance_status == 'demo':
            print("🟡 Binance API: DEMO MODE (no real connection)")
        else:
            print("🔴 Binance API: FAILED")
        
        for detail in self.results['binance']['details']:
            print(f"   {detail}")
        
        print()
        
        # CoinGecko Summary
        coingecko_status = self.results['coingecko']['status']
        if coingecko_status == 'success':
            print("🟢 CoinGecko API: FULLY OPERATIONAL")
        elif coingecko_status == 'partial':
            print("🟡 CoinGecko API: PARTIAL (some issues)")
        else:
            print("🔴 CoinGecko API: FAILED")
        
        for detail in self.results['coingecko']['details']:
            print(f"   {detail}")
        
        print()
        
        # Overall Assessment
        critical_issues = self.results['overall']['critical_issues']
        
        if not critical_issues:
            if binance_status in ['success', 'demo'] and coingecko_status in ['success', 'partial']:
                print("🎉 OVERALL STATUS: READY FOR TRADING")
                print("✅ Both APIs are functional - trading bot can operate")
                if binance_status == 'demo':
                    print("ℹ️ Binance is in demo mode - trades will be simulated")
            else:
                print("⚠️ OVERALL STATUS: PARTIAL FUNCTIONALITY")
        else:
            print("🚨 OVERALL STATUS: CRITICAL ISSUES DETECTED")
            print("❌ Trading bot may not function properly")
            
            print("\n🔧 CRITICAL ISSUES TO RESOLVE:")
            for issue in critical_issues:
                print(f"   • {issue}")
        
        print()
        print("💡 RECOMMENDATIONS:")
        
        if binance_status == 'demo':
            print("   • Add valid Binance testnet API keys for real market testing")
            print("   • Get testnet keys from: https://testnet.binance.vision/")
        
        if coingecko_status != 'success':
            print("   • Consider getting a CoinGecko Pro API key for better reliability")
            print("   • Check internet connectivity if API calls are failing")
        
        if not critical_issues and binance_status in ['success', 'demo']:
            print("   • System is ready - you can start running the trading bot")
            print("   • Use demo mode first to test strategies safely")
        
        print("\n" + "=" * 80)
        print(f"⏰ Validation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


async def main():
    """Main validation function."""
    try:
        # Setup logging
        setup_logger()
        
        # Run validation
        validator = APIValidator()
        results = await validator.validate_all_apis()
        
        # Exit with appropriate code
        if results['overall']['critical_issues']:
            sys.exit(1)  # Exit with error if critical issues
        else:
            sys.exit(0)  # Exit successfully
            
    except KeyboardInterrupt:
        print("\n⏹️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 