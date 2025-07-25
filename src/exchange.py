"""Exchange integration for cryptocurrency trading."""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

try:
    from binance import AsyncClient
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    AsyncClient = None
    BinanceAPIException = Exception
    BINANCE_AVAILABLE = False

from .logger import TradingLogger


class BinanceExchange:
    """Binance exchange integration for cryptocurrency trading."""
    
    def __init__(self, config):
        self.config = config
        self.logger = TradingLogger(__name__)
        
        self.api_key = config.binance_api_key
        self.secret_key = config.binance_secret_key
        
        # Determine if we should use Binance testnet or demo mode
        has_valid_keys = (config.binance_api_key and config.binance_secret_key and 
                         len(config.binance_api_key) > 20 and len(config.binance_secret_key) > 20)
        self.use_binance_testnet = config.use_sandbox and BINANCE_AVAILABLE and has_valid_keys
        self.demo_mode = not self.use_binance_testnet
        
        # Trading state
        self.account_info = {}
        self.open_orders = {}
        self.positions = {}
        self.client = None
        
        # Demo portfolio for enhanced testing
        self.demo_balance = 10000.0  # $10,000 USDT for demo
        self.demo_positions = {}
    
    async def initialize(self):
        """Initialize exchange connection and account info."""
        try:
            if self.use_binance_testnet:
                self.logger.logger.info("🏗️ Connecting to Binance Testnet...")
                
                if not self.api_key or not self.secret_key:
                    raise ValueError("Binance API credentials required for testnet")
                
                # Initialize Binance testnet client
                try:
                    self.client = AsyncClient(
                        api_key=self.api_key,
                        api_secret=self.secret_key,
                        testnet=True,  # This enables testnet mode
                        requests_params={'timeout': 20}
                    )
                    
                    # Test the connection
                    await self.client.ping()
                    self.logger.logger.info("✅ Connected to Binance Testnet successfully!")
                    
                except Exception as e:
                    self.logger.logger.warning(f"Failed to connect to Binance Testnet: {e}")
                    self.logger.logger.info("💡 Note: Testnet requires separate API keys from https://testnet.binance.vision/")
                    self.logger.logger.info("Falling back to enhanced demo mode...")
                    self.demo_mode = True
                    self.use_binance_testnet = False
                    self.client = None
                    # Initialize demo balance for enhanced demo mode
                    self.demo_balance = 10000.0  # $10,000 demo balance
            
            if self.demo_mode:
                self.logger.logger.info("Running in DEMO mode - simulated trading")
                self.client = None
            
            # Get account information
            self.account_info = await self.get_account_info()
            
            # Get current positions
            self.positions = await self.get_positions()
            
            self.logger.logger.info("Exchange initialized successfully")
            
        except Exception as e:
            self.logger.log_error("initialize", e)
            raise
    
    async def get_account_info(self) -> Dict:
        """Get account information including balances."""
        try:
            if self.use_binance_testnet and self.client:
                try:
                    # Real Binance Testnet API call
                    account = await self.client.get_account()
                    
                    # Process balances
                    balances = {}
                    for balance in account.get("balances", []):
                        asset = balance["asset"]
                        free = float(balance["free"])
                        locked = float(balance["locked"])
                        
                        if free > 0 or locked > 0:
                            balances[asset] = {
                                "free": free,
                                "locked": locked,
                                "total": free + locked
                            }
                    
                    return {
                        "balances": balances,
                        "account_type": f"TESTNET_{account.get('accountType', 'SPOT')}",
                        "trading_enabled": account.get("canTrade", True),
                        "withdraw_enabled": False,  # Testnet doesn't allow real withdrawals
                        "deposit_enabled": False    # Testnet doesn't allow real deposits
                    }
                
                except Exception as e:
                    # If testnet API fails, fall back to demo mode
                    self.logger.logger.warning(f"Testnet API failed: {e}")
                    self.logger.logger.info("Switching to enhanced demo mode for this session...")
                    self.demo_mode = True
                    self.use_binance_testnet = False
                    self.client = None
                    if not hasattr(self, 'demo_balance'):
                        self.demo_balance = 10000.0
                    # Fall through to demo mode below
            
            else:
                # Demo mode - Return simulated account info
                balances = {
                    "USDT": {
                        "free": self.demo_balance,
                        "locked": 0.0,
                        "total": self.demo_balance
                    }
                }
                
                # Add demo positions
                for symbol, position in self.demo_positions.items():
                    asset = symbol.replace("USDT", "")
                    balances[asset] = {
                        "free": position["quantity"],
                        "locked": 0.0,
                        "total": position["quantity"]
                    }
                
                return {
                    "balances": balances,
                    "account_type": "DEMO",
                    "trading_enabled": True,
                    "withdraw_enabled": False,
                    "deposit_enabled": False
                }
            
        except Exception as e:
            self.logger.log_error("get_account_info", e)
            return {}
    
    async def get_positions(self) -> Dict:
        """Get current trading positions."""
        try:
            # For spot trading, positions are just balances
            account_info = await self.get_account_info()
            balances = account_info.get("balances", {})
            
            positions = {}
            
            # Calculate positions for each asset
            for asset, balance in balances.items():
                if asset != self.config.base_currency and balance["total"] > 0:
                    # Get current price
                    symbol = f"{asset}{self.config.base_currency}"
                    if symbol in self.config.supported_symbols:
                        ticker = await self.get_ticker_price(symbol)
                        current_price = float(ticker.get("price", 0))
                        
                        if current_price > 0:
                            value = balance["total"] * current_price
                            positions[symbol] = {
                                "symbol": symbol,
                                "quantity": balance["total"],
                                "entry_price": 0,  # We don't track entry price in this simple version
                                "current_price": current_price,
                                "value": value,
                                "unrealized_pnl": 0  # Would need entry price to calculate
                            }
            
            return positions
            
        except Exception as e:
            self.logger.log_error("get_positions", e)
            return {}
    
    async def get_ticker_price(self, symbol: str) -> Dict:
        """Get current ticker price for a symbol."""
        try:
            if self.use_binance_testnet and self.client:
                # Real Binance Testnet API call
                ticker = await self.client.get_symbol_ticker(symbol=symbol)
                return ticker
            
            else:
                # Demo prices (simulated)
                demo_prices = {
                    "BTCUSDT": 65000.0,
                    "ETHUSDT": 3200.0,
                    "ADAUSDT": 0.45,
                    "DOTUSDT": 6.5,
                    "LINKUSDT": 14.0,
                    "SOLUSDT": 180.0,
                    "MATICUSDT": 0.85,
                    "AVAXUSDT": 28.0
                }
                return {"symbol": symbol, "price": str(demo_prices.get(symbol, 1.0))}
            
        except Exception as e:
            self.logger.log_error("get_ticker_price", e)
            return {"symbol": symbol, "price": "0"}
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """Get order book depth for a symbol."""
        try:
            if self.use_binance_testnet and self.client:
                # Real Binance Testnet API call
                order_book = await self.client.get_order_book(symbol=symbol, limit=limit)
                return order_book
            
            else:
                # Demo order book (simulated)
                import random
                
                # Get current price for simulation
                ticker = await self.get_ticker_price(symbol)
                current_price = float(ticker.get("price", 1.0))
                
                # Generate realistic bid/ask spread (0.01-0.1%)
                spread_pct = random.uniform(0.0001, 0.001)
                spread = current_price * spread_pct
                
                # Generate bids (below current price)
                bids = []
                for i in range(limit):
                    price = current_price - spread * (i + 1) / 2
                    quantity = random.uniform(0.1, 10.0)
                    bids.append([str(round(price, 2)), str(round(quantity, 6))])
                
                # Generate asks (above current price)
                asks = []
                for i in range(limit):
                    price = current_price + spread * (i + 1) / 2
                    quantity = random.uniform(0.1, 10.0)
                    asks.append([str(round(price, 2)), str(round(quantity, 6))])
                
                return {
                    "lastUpdateId": int(time.time() * 1000),
                    "bids": bids,
                    "asks": asks
                }
            
        except Exception as e:
            self.logger.log_error("get_order_book", e)
            return {"bids": [], "asks": []}
    
    async def place_buy_order(self, symbol: str, amount: float, order_type: str = "MARKET") -> Dict:
        """Place a buy order."""
        try:
            # Validate minimum order amount
            if amount < 10.0:  # $10 minimum
                raise ValueError(f"Order amount {amount} is below minimum $10")
            
            if self.use_binance_testnet and self.client:
                # Real Binance Testnet order
                if order_type == "MARKET":
                    self.logger.logger.info(f"🏗️ Placing TESTNET buy order: {symbol} for ${amount:.2f}")
                    response = await self.client.order_market_buy(
                        symbol=symbol,
                        quoteOrderQty=amount
                    )
                    self.logger.logger.info(f"✅ Testnet buy order executed: {response.get('orderId')}")
                else:
                    raise NotImplementedError("Only market orders supported currently")
            else:
                # Simulate buy order (demo mode)
                response = self._simulate_buy_order(symbol, amount)
            
            # Log the trade
            self.logger.log_trade(
                action="BUY",
                symbol=symbol,
                amount=amount,
                price=0,  # Market order
                order_id=response.get("orderId"),
                status=response.get("status"),
                mode="TESTNET" if self.use_binance_testnet else "DEMO"
            )
            
            return response
            
        except Exception as e:
            self.logger.log_error("place_buy_order", e)
            return {"error": str(e)}
    
    async def place_sell_order(self, symbol: str, quantity: float, order_type: str = "MARKET") -> Dict:
        """Place a sell order."""
        try:
            # Validate minimum order quantity
            if quantity <= 0:
                raise ValueError(f"Invalid quantity: {quantity}")
            
            if self.use_binance_testnet and self.client:
                # Real Binance Testnet sell order
                if order_type == "MARKET":
                    self.logger.logger.info(f"🏗️ Placing TESTNET sell order: {symbol} quantity {quantity}")
                    response = await self.client.order_market_sell(
                        symbol=symbol,
                        quantity=quantity
                    )
                    self.logger.logger.info(f"✅ Testnet sell order executed: {response.get('orderId')}")
                else:
                    raise NotImplementedError("Only market orders supported currently")
            else:
                # Simulate sell order (demo mode)
                response = self._simulate_sell_order(symbol, quantity)
            
            # Log the trade
            self.logger.log_trade(
                action="SELL",
                symbol=symbol,
                amount=quantity,
                price=0,  # Market order
                order_id=response.get("orderId"),
                status=response.get("status"),
                mode="TESTNET" if self.use_binance_testnet else "DEMO"
            )
            
            return response
            
        except Exception as e:
            self.logger.log_error("place_sell_order", e)
            return {"error": str(e)}
    
    async def shutdown(self):
        """Cleanup exchange resources."""
        try:
            if hasattr(self, 'client') and self.client:
                await self.client.close_connection()
        except Exception as e:
            self.logger.logger.warning(f"Error during exchange shutdown: {e}")
    
    async def get_symbol_info(self, symbol: str) -> Dict:
        """Get trading rules and info for a symbol."""
        try:
            if self.demo_mode:
                # Return demo symbol info
                return {
                    "symbol": symbol,
                    "status": "TRADING",
                    "min_qty": 0.001,
                    "min_notional": 10.0,
                    "base_asset": symbol.replace("USDT", ""),
                    "quote_asset": "USDT"
                }
            else:
                # Real API call
                exchange_info = await self.client.get_exchange_info()
                
                for symbol_info in exchange_info.get("symbols", []):
                    if symbol_info["symbol"] == symbol:
                        # Extract key trading rules
                        filters = symbol_info.get("filters", [])
                        
                        min_qty = 0.001
                        min_notional = 10.0
                        
                        for filter_item in filters:
                            if filter_item["filterType"] == "LOT_SIZE":
                                min_qty = float(filter_item["minQty"])
                            elif filter_item["filterType"] == "MIN_NOTIONAL":
                                min_notional = float(filter_item["minNotional"])
                        
                        return {
                            "symbol": symbol,
                            "status": symbol_info.get("status"),
                            "min_qty": min_qty,
                            "min_notional": min_notional,
                            "base_asset": symbol_info.get("baseAsset"),
                            "quote_asset": symbol_info.get("quoteAsset")
                        }
                
                return {}
            
        except Exception as e:
            self.logger.log_error("get_symbol_info", e)
            return {}
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """Get status of a specific order."""
        try:
            if self.demo_mode:
                # Demo orders are always filled immediately
                return {
                    "symbol": symbol,
                    "orderId": order_id,
                    "status": "FILLED",
                    "executedQty": "1.0",
                    "type": "MARKET"
                }
            else:
                response = await self.client.get_order(symbol=symbol, orderId=order_id)
                return response
            
        except Exception as e:
            self.logger.log_error("get_order_status", e)
            return {}
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an open order."""
        try:
            if self.demo_mode:
                # Demo orders are filled immediately, so can't be cancelled
                return {"error": "Demo orders are filled immediately"}
            else:
                response = await self.client.cancel_order(symbol=symbol, orderId=order_id)
                self.logger.logger.info(f"Cancelled order {order_id} for {symbol}")
                return response
            
        except Exception as e:
            self.logger.log_error("cancel_order", e)
            return {}
    
    async def get_portfolio_value(self) -> Dict:
        """Calculate total portfolio value in base currency."""
        try:
            account_info = await self.get_account_info()
            balances = account_info.get("balances", {})
            
            total_value = 0.0
            base_balance = balances.get(self.config.base_currency, {}).get("total", 0)
            
            # Add base currency balance
            total_value += base_balance
            
            # Convert other assets to base currency
            for asset, balance in balances.items():
                if asset != self.config.base_currency and balance["total"] > 0:
                    symbol = f"{asset}{self.config.base_currency}"
                    if symbol in self.config.supported_symbols:
                        ticker = await self.get_ticker_price(symbol)
                        price = float(ticker.get("price", 0))
                        asset_value = balance["total"] * price
                        total_value += asset_value
            
            return {
                "total_value": total_value,
                "base_currency": self.config.base_currency,
                "available_balance": base_balance,
                "positions": await self.get_positions()
            }
            
        except Exception as e:
            self.logger.log_error("get_portfolio_value", e)
            return {"total_value": 0, "available_balance": 0, "positions": {}}
    

    
    def _simulate_buy_order(self, symbol: str, amount: float) -> Dict:
        """Simulate buy order execution for demo mode."""
        order_id = int(time.time() * 1000)
        
        # Get demo price
        demo_prices = {
            "BTCUSDT": 65000.0,
            "ETHUSDT": 3200.0,
            "ADAUSDT": 0.45,
            "DOTUSDT": 6.5,
            "LINKUSDT": 14.0,
            "SOLUSDT": 180.0,
            "MATICUSDT": 0.85,
            "AVAXUSDT": 28.0
        }
        
        price = demo_prices.get(symbol, 1.0)
        quantity = amount / price
        
        # Update demo balance and positions
        if amount <= self.demo_balance:
            self.demo_balance -= amount
            
            if symbol in self.demo_positions:
                self.demo_positions[symbol]["quantity"] += quantity
                self.demo_positions[symbol]["value"] += amount
            else:
                self.demo_positions[symbol] = {
                    "quantity": quantity,
                    "entry_price": price,
                    "current_price": price,
                    "value": amount,
                    "unrealized_pnl": 0
                }
        
        return {
            "symbol": symbol,
            "orderId": order_id,
            "orderListId": -1,
            "clientOrderId": f"demo_buy_{order_id}",
            "transactTime": int(time.time() * 1000),
            "price": str(price),
            "origQty": str(quantity),
            "executedQty": str(quantity),
            "cummulativeQuoteQty": str(amount),
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "MARKET",
            "side": "BUY"
        }
    
    def _simulate_sell_order(self, symbol: str, quantity: float) -> Dict:
        """Simulate sell order execution for demo mode."""
        order_id = int(time.time() * 1000)
        
        # Get demo price
        demo_prices = {
            "BTCUSDT": 65000.0,
            "ETHUSDT": 3200.0,
            "ADAUSDT": 0.45,
            "DOTUSDT": 6.5,
            "LINKUSDT": 14.0,
            "SOLUSDT": 180.0,
            "MATICUSDT": 0.85,
            "AVAXUSDT": 28.0
        }
        
        price = demo_prices.get(symbol, 1.0)
        amount = quantity * price
        
        # Update demo balance and positions
        if symbol in self.demo_positions and self.demo_positions[symbol]["quantity"] >= quantity:
            self.demo_balance += amount
            self.demo_positions[symbol]["quantity"] -= quantity
            self.demo_positions[symbol]["value"] -= amount
            
            if self.demo_positions[symbol]["quantity"] <= 0:
                del self.demo_positions[symbol]
        
        return {
            "symbol": symbol,
            "orderId": order_id,
            "orderListId": -1,
            "clientOrderId": f"demo_sell_{order_id}",
            "transactTime": int(time.time() * 1000),
            "price": str(price),
            "origQty": str(quantity),
            "executedQty": str(quantity),
            "cummulativeQuoteQty": str(amount),
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "MARKET",
            "side": "SELL"
        } 