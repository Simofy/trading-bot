#!/usr/bin/env python3
"""
Test the new minimum order logic with real Binance requirements.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_new_logic():
    """Test the new logic with real minimum requirements."""
    print("🧪 Testing New Minimum Order Logic")
    print("=" * 40)
    
    try:
        from src.config import Config
        from src.exchange import BinanceExchange
        from src.risk_manager import RiskManager
        
        config = Config()
        exchange = BinanceExchange(config)
        await exchange.initialize()
        
        risk_manager = RiskManager(config, exchange)
        
        # Simulate the exact scenario from your logs
        portfolio_data = {
            "total_value": 14.70,
            "available_balance": 14.70,
            "positions": {}
        }
        
        market_data = {
            "DOTUSDT": {"price": 3.85, "change_24h": 0.89}
        }
        
        print(f"📊 Test Scenario:")
        print(f"   Portfolio: ${portfolio_data['total_value']}")
        print(f"   AI Wants: 10% allocation = ${portfolio_data['total_value'] * 0.10:.2f}")
        
        # Test the risk assessment
        risk_assessment = await risk_manager.evaluate_trade_risk(
            action="BUY",
            symbol="DOTUSDT",
            allocation_percentage=10.0,
            portfolio_data=portfolio_data,
            market_data=market_data
        )
        
        print(f"\n📋 Risk Assessment Results:")
        print(f"   Approved: {risk_assessment.get('approved', False)}")
        print(f"   Risk Score: {risk_assessment.get('risk_score', 0)}")
        
        adjustments = risk_assessment.get('adjustments', {})
        if adjustments:
            final_allocation = adjustments.get('allocation_percentage', 10.0)
            final_amount = (final_allocation / 100) * portfolio_data['total_value']
            print(f"   ✅ Adjusted Allocation: {final_allocation}% = ${final_amount:.2f}")
            
            # Check if this meets Binance minimum
            if final_amount >= 10.0:
                print(f"   ✅ Meets DOTUSDT minimum ($10.00)")
                
                # Test if exchange will accept this order
                try:
                    result = await exchange.place_buy_order("DOTUSDT", final_amount)
                    if "error" not in result:
                        print(f"   🎉 ORDER WOULD SUCCEED!")
                        print(f"   📝 Order ID: {result.get('orderId', 'N/A')}")
                    else:
                        print(f"   ❌ Order failed: {result['error']}")
                except Exception as e:
                    print(f"   ❌ Order error: {e}")
            else:
                print(f"   ❌ Still below minimum ($10.00)")
        else:
            final_amount = (10.0 / 100) * portfolio_data['total_value']
            print(f"   ❌ No adjustments made: ${final_amount:.2f}")
        
        await exchange.shutdown()
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_new_logic()

if __name__ == "__main__":
    asyncio.run(main()) 