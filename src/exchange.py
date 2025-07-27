"""Exchange integration for cryptocurrency trading."""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from binance import AsyncClient
from binance.exceptions import BinanceAPIException
BINANCE_AVAILABLE = True

from .logger import TradingLogger


class BinanceExchange:
    """Binance exchange integration for cryptocurrency trading."""
    
    def __init__(self, config):
        self.config = config
        self.logger = TradingLogger(__name__)
        
        self.api_key = config.binance_api_key
        self.secret_key = config.binance_secret_key
        
        # Determine exchange mode: testnet, live, or demo
        has_valid_keys = (config.binance_api_key and config.binance_secret_key and 
                         len(config.binance_api_key) > 20 and len(config.binance_secret_key) > 20)
        
        # Properly determine which mode to use
        if config.use_sandbox and BINANCE_AVAILABLE and has_valid_keys:
            # Testnet mode: sandbox enabled with valid keys
            self.use_binance_testnet = True
            self.use_binance_live = False
            self.demo_mode = False
        elif not config.use_sandbox and BINANCE_AVAILABLE and has_valid_keys:
            # Live API mode: sandbox disabled with valid keys
            self.use_binance_testnet = False
            self.use_binance_live = True
            self.demo_mode = False
        else:
            # Demo mode: fallback when no valid keys or binance unavailable
            self.use_binance_testnet = False
            self.use_binance_live = False
            self.demo_mode = True
        
        # Trading state
        self.account_info = {}
        self.open_orders = {}
        self.positions = {}
        self.client = None
        
        # Demo portfolio for enhanced testing
        self.demo_balance = float(self.config.demo_initial_balance)  # Use configurable demo balance
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
                    self.use_binance_live = False
                    self.client = None
                    # Initialize demo balance for enhanced demo mode
                    self.demo_balance = float(self.config.demo_initial_balance)  # $10,000 demo balance
            
            elif self.use_binance_live:
                self.logger.logger.info("🚀 Connecting to Binance LIVE API...")
                
                if not self.api_key or not self.secret_key:
                    raise ValueError("Binance API credentials required for live trading")
                
                # Initialize Binance live client
                try:
                    self.client = AsyncClient(
                        api_key=self.api_key,
                        api_secret=self.secret_key,
                        testnet=False,  # This enables live mode
                        requests_params={'timeout': 20}
                    )
                    
                    # Test the connection
                    await self.client.ping()
                    self.logger.logger.info("✅ Connected to Binance LIVE API successfully!")
                    
                    # Verify account access
                    account = await self.client.get_account()
                    self.logger.logger.info(f"📊 Live account type: {account.get('accountType', 'UNKNOWN')}")
                    
                except Exception as e:
                    self.logger.logger.error(f"Failed to connect to Binance Live API: {e}")
                    self.logger.logger.warning("🚨 Live API connection failed - falling back to demo mode for safety")
                    self.demo_mode = True
                    self.use_binance_live = False
                    self.client = None
                    # Initialize demo balance for enhanced demo mode
                    self.demo_balance = float(self.config.demo_initial_balance)  # $10,000 demo balance
            
            elif self.demo_mode:
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
                    # Log the error but don't destroy the client for minor failures
                    self.logger.logger.warning(f"Testnet API call failed: {e}")
                    self.logger.logger.info("Using fallback account info, but keeping testnet client for trading")
                    
                    # Return basic account info without destroying the client
                    return {
                        "balances": {"USDT": {"free": 1000.0, "locked": 0.0, "total": 1000.0}},  # Fallback
                        "account_type": "TESTNET_SPOT",
                        "trading_enabled": True,
                        "withdraw_enabled": False,
                        "deposit_enabled": False
                    }
            
            elif self.use_binance_live and self.client:
                try:
                    # Real Binance Live API call
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
                        "account_type": f"LIVE_{account.get('accountType', 'SPOT')}",
                        "trading_enabled": account.get("canTrade", True),
                        "withdraw_enabled": account.get("canWithdraw", True),
                        "deposit_enabled": account.get("canDeposit", True)
                    }
                
                except Exception as e:
                    # Log the error but don't destroy the client for minor failures
                    self.logger.logger.warning(f"Live API call failed: {e}")
                    self.logger.logger.info("Using fallback account info, but keeping live client for trading")
                    
                    # Return basic account info without destroying the client
                    # (Trading client remains active for order placement)
                    return {
                        "balances": {"EUR": {"free": 14.7, "locked": 0.0, "total": 14.7}},  # Fallback
                        "account_type": "LIVE_SPOT",
                        "trading_enabled": True,
                        "withdraw_enabled": True,
                        "deposit_enabled": True
                    }
            
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
            # Get real minimum notional value from Binance for this symbol
            symbol_info = await self.get_symbol_info(symbol)
            min_notional = symbol_info.get("min_notional", 10.0)  # Default to $10 if not found
            
            # Validate against the real Binance minimum
            if amount < min_notional:
                raise ValueError(f"Order amount ${amount:.2f} below Binance minimum ${min_notional:.2f} for {symbol}")
            
            self.logger.logger.info(f"✅ Order amount ${amount:.2f} meets {symbol} minimum ${min_notional:.2f}")
            
            if (self.use_binance_testnet or self.use_binance_live) and self.client:
                # Real Binance order (testnet or live)
                if order_type == "MARKET":
                    mode_str = "TESTNET" if self.use_binance_testnet else "LIVE"
                    self.logger.logger.info(f"🏗️ Placing {mode_str} buy order: {symbol} for ${amount:.2f}")
                    response = await self.client.order_market_buy(
                        symbol=symbol,
                        quoteOrderQty=amount
                    )
                    self.logger.logger.info(f"✅ {mode_str} buy order executed: {response.get('orderId')}")
                else:
                    raise NotImplementedError("Only market orders supported currently")
            else:
                # Simulate buy order (demo mode)
                response = self._simulate_buy_order(symbol, amount)
            
            # Log the trade
            if self.use_binance_testnet:
                mode = "TESTNET"
            elif self.use_binance_live:
                mode = "LIVE"
            else:
                mode = "DEMO"
                
            self.logger.log_trade(
                action="BUY",
                symbol=symbol,
                amount=amount,
                price=0,  # Market order
                order_id=response.get("orderId"),
                status=response.get("status"),
                mode=mode
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
            
            if (self.use_binance_testnet or self.use_binance_live) and self.client:
                # Real Binance sell order (testnet or live)
                if order_type == "MARKET":
                    mode_str = "TESTNET" if self.use_binance_testnet else "LIVE"
                    self.logger.logger.info(f"🏗️ Placing {mode_str} sell order: {symbol} quantity {quantity}")
                    response = await self.client.order_market_sell(
                        symbol=symbol,
                        quantity=quantity
                    )
                    self.logger.logger.info(f"✅ {mode_str} sell order executed: {response.get('orderId')}")
                else:
                    raise NotImplementedError("Only market orders supported currently")
            else:
                # Simulate sell order (demo mode)
                response = self._simulate_sell_order(symbol, quantity)
            
            # Log the trade
            if self.use_binance_testnet:
                mode = "TESTNET"
            elif self.use_binance_live:
                mode = "LIVE"
            else:
                mode = "DEMO"
                
            self.logger.log_trade(
                action="SELL",
                symbol=symbol,
                amount=quantity,
                price=0,  # Market order
                order_id=response.get("orderId"),
                status=response.get("status"),
                mode=mode
            )
            
            return response
            
        except Exception as e:
            self.logger.log_error("place_sell_order", e)
            return {"error": str(e)}
    
    async def shutdown(self):
        """Cleanup exchange resources."""
        try:
            if hasattr(self, 'client') and self.client:
                self.logger.logger.info("Closing Binance client connection...")
                # Close connection with timeout to prevent hanging
                await asyncio.wait_for(self.client.close_connection(), timeout=3.0)
                self.logger.logger.info("Binance client connection closed")
        except asyncio.TimeoutError:
            self.logger.logger.warning("Binance client close timed out after 3 seconds")
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
                                # Legacy filter type
                                min_notional = float(filter_item["minNotional"])
                            elif filter_item["filterType"] == "NOTIONAL":
                                # New filter type - this is the one causing the issue
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
            available_balance = base_balance
            primary_asset_used = None  # Track which asset we used as primary to avoid double counting
            
            # If no base currency balance, find the primary balance and use it
            if base_balance == 0 and balances:
                # Find the largest balance to use as primary
                largest_asset = None
                largest_amount = 0
                
                for asset, balance_info in balances.items():
                    amount = balance_info.get("total", 0)
                    if amount > largest_amount:
                        largest_amount = amount
                        largest_asset = asset
                
                if largest_asset:
                    primary_asset_used = largest_asset  # Remember which asset we used as primary
                    self.logger.logger.info(f"No {self.config.base_currency} found, using {largest_asset} as primary currency")
                    
                    # Convert primary asset to USDT equivalent
                    if largest_asset == "USDT":
                        available_balance = largest_amount
                        total_value = largest_amount
                    else:
                        # Try to get USDT price for the asset
                        try:
                            symbol = f"{largest_asset}USDT"
                            ticker = await self.get_ticker_price(symbol)
                            price = float(ticker.get("price", 0))
                            if price > 0:
                                available_balance = largest_amount * price
                                total_value = available_balance
                                self.logger.logger.info(f"Converted {largest_amount} {largest_asset} to ~${available_balance:.2f} USDT")
                            else:
                                # Fallback: use amount as-is if no price available
                                available_balance = largest_amount
                                total_value = largest_amount
                        except Exception as e:
                            # Fallback: use amount as-is if conversion fails
                            available_balance = largest_amount
                            total_value = largest_amount
                            self.logger.logger.warning(f"Could not convert {largest_asset} to USDT: {e}")
            else:
                # Add base currency balance
                total_value += base_balance
            
            # Convert other assets to base currency (skip the one we already counted as primary)
            for asset, balance in balances.items():
                if asset != self.config.base_currency and asset != primary_asset_used and balance["total"] > 0:
                    try:
                        symbol = f"{asset}{self.config.base_currency}"
                        if symbol in self.config.supported_symbols:
                            ticker = await self.get_ticker_price(symbol)
                            price = float(ticker.get("price", 0))
                            asset_value = balance["total"] * price
                            total_value += asset_value
                        else:
                            # Try USDT conversion if base currency symbol not supported
                            symbol = f"{asset}USDT"
                            ticker = await self.get_ticker_price(symbol)
                            price = float(ticker.get("price", 0))
                            if price > 0:
                                asset_value = balance["total"] * price
                                total_value += asset_value
                    except Exception:
                        # Skip assets that can't be converted
                        continue
            
            return {
                "total_value": total_value,
                "base_currency": self.config.base_currency,
                "available_balance": available_balance,
                "positions": await self.get_positions()
            }
            
        except Exception as e:
            self.logger.log_error("get_portfolio_value", e)
            return {"total_value": 0, "available_balance": 0, "positions": {}}

    async def get_historical_trades(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Get historical trades from Binance API."""
        try:
            if self.demo_mode:
                # Return simulated trades for demo mode
                return self._get_demo_trades(symbol, limit)
            
            if not self.client:
                return []
            
            if symbol:
                # Get trades for specific symbol
                trades = await self.client.get_my_trades(symbol=symbol, limit=limit)
            else:
                # Get all trades across supported symbols
                all_trades = []
                for sym in self.config.supported_symbols:
                    try:
                        symbol_trades = await self.client.get_my_trades(symbol=sym, limit=min(50, limit))
                        all_trades.extend(symbol_trades)
                    except Exception as e:
                        self.logger.logger.warning(f"Could not fetch trades for {sym}: {e}")
                        continue
                
                # Sort by time and limit
                all_trades.sort(key=lambda x: x.get('time', 0), reverse=True)
                trades = all_trades[:limit]
            
            # Format trades for consistency
            formatted_trades = []
            for trade in trades:
                formatted_trades.append({
                    'id': trade.get('id'),
                    'symbol': trade.get('symbol'),
                    'orderId': trade.get('orderId'),
                    'price': float(trade.get('price', 0)),
                    'qty': float(trade.get('qty', 0)),
                    'quoteQty': float(trade.get('quoteQty', 0)),
                    'commission': float(trade.get('commission', 0)),
                    'commissionAsset': trade.get('commissionAsset'),
                    'time': trade.get('time'),
                    'isBuyer': trade.get('isBuyer'),
                    'isMaker': trade.get('isMaker'),
                    'timestamp': datetime.fromtimestamp(trade.get('time', 0) / 1000).isoformat() if trade.get('time') else None
                })
            
            return formatted_trades
            
        except Exception as e:
            self.logger.log_error("get_historical_trades", e)
            return []
    
    async def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
        """Get historical kline/candlestick data from Binance API."""
        try:
            if self.demo_mode:
                return self._get_demo_klines(symbol, interval, limit)
            
            if not self.client:
                return []
            
            klines = await self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            
            # Format klines data
            formatted_klines = []
            for kline in klines:
                formatted_klines.append({
                    'open_time': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'close_time': kline[6],
                    'quote_asset_volume': float(kline[7]),
                    'number_of_trades': int(kline[8]),
                    'taker_buy_base_asset_volume': float(kline[9]),
                    'taker_buy_quote_asset_volume': float(kline[10]),
                    'timestamp': datetime.fromtimestamp(kline[0] / 1000).isoformat()
                })
            
            return formatted_klines
            
        except Exception as e:
            self.logger.log_error("get_klines", e)
            return []
    
    async def get_24hr_ticker_stats(self, symbol: str = None) -> Dict:
        """Get 24hr ticker statistics from Binance API."""
        try:
            if self.demo_mode:
                return self._get_demo_ticker_stats(symbol)
            
            if not self.client:
                return {}
            
            if symbol:
                stats = await self.client.get_ticker(symbol=symbol)
                return {
                    'symbol': stats.get('symbol'),
                    'priceChange': float(stats.get('priceChange', 0)),
                    'priceChangePercent': float(stats.get('priceChangePercent', 0)),
                    'weightedAvgPrice': float(stats.get('weightedAvgPrice', 0)),
                    'prevClosePrice': float(stats.get('prevClosePrice', 0)),
                    'lastPrice': float(stats.get('lastPrice', 0)),
                    'bidPrice': float(stats.get('bidPrice', 0)),
                    'askPrice': float(stats.get('askPrice', 0)),
                    'openPrice': float(stats.get('openPrice', 0)),
                    'highPrice': float(stats.get('highPrice', 0)),
                    'lowPrice': float(stats.get('lowPrice', 0)),
                    'volume': float(stats.get('volume', 0)),
                    'quoteVolume': float(stats.get('quoteVolume', 0)),
                    'count': int(stats.get('count', 0))
                }
            else:
                # Get stats for all supported symbols
                all_stats = {}
                for sym in self.config.supported_symbols:
                    try:
                        stats = await self.client.get_ticker(symbol=sym)
                        all_stats[sym] = {
                            'priceChange': float(stats.get('priceChange', 0)),
                            'priceChangePercent': float(stats.get('priceChangePercent', 0)),
                            'lastPrice': float(stats.get('lastPrice', 0)),
                            'volume': float(stats.get('volume', 0)),
                            'quoteVolume': float(stats.get('quoteVolume', 0)),
                        }
                    except Exception as e:
                        self.logger.logger.warning(f"Could not get stats for {sym}: {e}")
                        continue
                
                return all_stats
            
        except Exception as e:
            self.logger.log_error("get_24hr_ticker_stats", e)
            return {}
    
    def _get_demo_trades(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Generate demo trade history."""
        import random
        from datetime import timedelta
        
        demo_trades = []
        symbols = [symbol] if symbol else self.config.supported_symbols[:3]  # Limit for demo
        
        for i in range(min(limit, 20)):  # Limit demo trades
            sym = random.choice(symbols)
            is_buy = random.choice([True, False])
            price = random.uniform(100, 70000) if 'BTC' in sym else random.uniform(0.1, 5000)
            qty = random.uniform(0.001, 1.0)
            
            demo_trades.append({
                'id': i + 1,
                'symbol': sym,
                'orderId': 1000 + i,
                'price': price,
                'qty': qty,
                'quoteQty': price * qty,
                'commission': price * qty * 0.001,  # 0.1% fee
                'commissionAsset': 'USDT',
                'time': int((datetime.now() - timedelta(hours=i)).timestamp() * 1000),
                'isBuyer': is_buy,
                'isMaker': random.choice([True, False]),
                'timestamp': (datetime.now() - timedelta(hours=i)).isoformat()
            })
        
        return demo_trades
    
    def _get_demo_klines(self, symbol: str, interval: str, limit: int) -> List[Dict]:
        """Generate demo kline data."""
        import random
        from datetime import timedelta
        
        klines = []
        base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 100
        
        for i in range(min(limit, 50)):  # Limit demo klines
            timestamp = int((datetime.now() - timedelta(hours=i)).timestamp() * 1000)
            
            # Generate realistic OHLC data
            open_price = base_price + random.uniform(-base_price*0.02, base_price*0.02)
            high_price = open_price + random.uniform(0, base_price*0.01)
            low_price = open_price - random.uniform(0, base_price*0.01)
            close_price = random.uniform(low_price, high_price)
            volume = random.uniform(100, 10000)
            
            klines.append({
                'open_time': timestamp,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'close_time': timestamp + 3600000,  # 1 hour later
                'quote_asset_volume': volume * close_price,
                'number_of_trades': random.randint(100, 1000),
                'taker_buy_base_asset_volume': volume * 0.6,
                'taker_buy_quote_asset_volume': volume * close_price * 0.6,
                'timestamp': datetime.fromtimestamp(timestamp / 1000).isoformat()
            })
        
        return klines
    
    def _get_demo_ticker_stats(self, symbol: str = None) -> Dict:
        """Generate demo 24hr ticker statistics."""
        if symbol:
            return {
                'symbol': symbol,
                'priceChange': random.uniform(-1000, 1000),
                'priceChangePercent': random.uniform(-5, 5),
                'weightedAvgPrice': 50000 if 'BTC' in symbol else 3000,
                'prevClosePrice': 49500 if 'BTC' in symbol else 2950,
                'lastPrice': 50000 if 'BTC' in symbol else 3000,
                'bidPrice': 49900 if 'BTC' in symbol else 2990,
                'askPrice': 50100 if 'BTC' in symbol else 3010,
                'openPrice': 49000 if 'BTC' in symbol else 2900,
                'highPrice': 51000 if 'BTC' in symbol else 3100,
                'lowPrice': 48000 if 'BTC' in symbol else 2800,
                'volume': random.uniform(1000, 50000),
                'quoteVolume': random.uniform(50000000, 2000000000),
                'count': random.randint(10000, 100000)
            }
        else:
            # Return stats for all supported symbols
            stats = {}
            for sym in self.config.supported_symbols:
                base_price = 50000 if 'BTC' in sym else 3000 if 'ETH' in sym else random.uniform(1, 500)
                stats[sym] = {
                    'priceChange': random.uniform(-base_price*0.05, base_price*0.05),
                    'priceChangePercent': random.uniform(-5, 5),
                    'lastPrice': base_price,
                    'volume': random.uniform(1000, 50000),
                    'quoteVolume': random.uniform(1000000, 100000000)
                }
            return stats

    
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