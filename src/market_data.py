"""Market data provider for cryptocurrency prices and market information."""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .logger import TradingLogger


class MarketDataProvider:
    """Provides real-time and historical cryptocurrency market data."""
    
    def __init__(self, config):
        self.config = config
        self.logger = TradingLogger(__name__)
        
        # CoinGecko API configuration
        self.base_url = "https://api.coingecko.com/api/v3"
        self.pro_url = "https://pro-api.coingecko.com/api/v3"
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # 1 second between requests for free tier
        
        # Data cache
        self.price_cache = {}
        self.cache_ttl = 60  # 1 minute cache
        self.last_cache_update = {}
        
        # Symbol mapping (CoinGecko ID to trading symbol)
        self.symbol_mapping = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum", 
            "ADAUSDT": "cardano",
            "DOTUSDT": "polkadot",
            "LINKUSDT": "chainlink",
            "SOLUSDT": "solana",
            "MATICUSDT": "matic-network",
            "AVAXUSDT": "avalanche-2"
        }
    
    async def get_current_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get current prices for specified cryptocurrency symbols."""
        try:
            # Try to get real prices from CoinGecko if configured to do so
            if hasattr(self.config, 'should_use_real_market_data') and self.config.should_use_real_market_data:
                try:
                    return await self._get_real_prices(symbols)
                except Exception as e:
                    self.logger.logger.warning(f"Failed to get real prices: {e}, using demo data")
                    return self._get_demo_prices(symbols)
            else:
                # Use simulated demo data
                return self._get_demo_prices(symbols)
            
        except Exception as e:
            self.logger.log_error("get_current_prices", e)
            return self._get_fallback_prices(symbols)
    
    async def _get_real_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get real prices from CoinGecko for testnet mode."""
        # Check cache first
        cached_data = self._get_cached_prices(symbols)
        if cached_data:
            return cached_data
        
        # Map symbols to CoinGecko IDs
        coin_ids = []
        for symbol in symbols:
            if symbol in self.symbol_mapping:
                coin_ids.append(self.symbol_mapping[symbol])
        
        if not coin_ids:
            return {}
        
        # Fetch data from CoinGecko
        url = f"{self.base_url}/coins/markets"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": str(len(coin_ids)),
            "page": "1",
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d"
        }
        
        data = await self._make_request(url, params)
        
        # Process and format data
        processed_data = self._process_market_data(data, symbols)
        
        # Update cache
        self._update_cache(processed_data)
        
        self.logger.logger.info(f"Fetched real market data for {len(processed_data)} symbols")
        return processed_data
    
    def _get_demo_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get demo prices with realistic market data simulation."""
        import random
        import time
        
        # Base demo prices with some volatility
        base_prices = {
            "BTCUSDT": 65000.0,
            "ETHUSDT": 3200.0,
            "ADAUSDT": 0.45,
            "DOTUSDT": 6.5,
            "LINKUSDT": 14.0,
            "SOLUSDT": 180.0,
            "MATICUSDT": 0.85,
            "AVAXUSDT": 28.0
        }
        
        demo_data = {}
        
        for symbol in symbols:
            if symbol in base_prices:
                base_price = base_prices[symbol]
                
                # Add some randomness to simulate real market movements
                price_change_24h = random.uniform(-15.0, 15.0)  # -15% to +15%
                current_price = base_price * (1 + price_change_24h / 100)
                
                # Generate realistic volume
                market_cap = current_price * random.uniform(10000000, 1000000000)
                volume_24h = market_cap * random.uniform(0.05, 0.3)  # 5-30% of market cap
                
                demo_data[symbol] = {
                    "price": current_price,
                    "market_cap": market_cap,
                    "volume_24h": volume_24h,
                    "price_change_1h": random.uniform(-3.0, 3.0),
                    "price_change_24h": price_change_24h,
                    "price_change_7d": random.uniform(-25.0, 25.0),
                    "circulating_supply": market_cap / current_price,
                    "total_supply": market_cap / current_price * 1.1,
                    "ath": current_price * random.uniform(1.5, 3.0),
                    "atl": current_price * random.uniform(0.1, 0.8),
                    "last_updated": time.time()
                }
        
        self.logger.logger.info(f"Generated demo market data for {len(demo_data)} symbols")
        return demo_data
    
    async def get_historical_data(self, symbol: str, days: int = 7) -> Dict:
        """Get historical price data for a cryptocurrency."""
        try:
            if symbol not in self.symbol_mapping:
                return {}
            
            coin_id = self.symbol_mapping[symbol]
            
            url = f"{self.base_url}/coins/{coin_id}/market_chart"
            params = {
                "vs_currency": "usd",
                "days": str(days),
                "interval": "hourly" if days <= 7 else "daily"
            }
            
            if self.config.coingecko_api_key:
                url = f"{self.pro_url}/coins/{coin_id}/market_chart"
                params["x_cg_pro_api_key"] = self.config.coingecko_api_key
            
            data = await self._make_request(url, params)
            
            return self._process_historical_data(data)
            
        except Exception as e:
            self.logger.log_error("get_historical_data", e)
            return {}
    
    async def get_market_overview(self) -> Dict:
        """Get overall cryptocurrency market overview."""
        try:
            url = f"{self.base_url}/global"
            
            if self.config.coingecko_api_key:
                url = f"{self.pro_url}/global"
                params = {"x_cg_pro_api_key": self.config.coingecko_api_key}
            else:
                params = {}
            
            data = await self._make_request(url, params)
            
            return self._process_global_data(data)
            
        except Exception as e:
            self.logger.log_error("get_market_overview", e)
            return {}
    
    async def get_trending_coins(self) -> List[Dict]:
        """Get currently trending cryptocurrencies."""
        try:
            url = f"{self.base_url}/search/trending"
            
            data = await self._make_request(url, {})
            
            return self._process_trending_data(data)
            
        except Exception as e:
            self.logger.log_error("get_trending_coins", e)
            return []
    
    async def _make_request(self, url: str, params: Dict) -> Dict:
        """Make HTTP request with rate limiting and error handling."""
        # Rate limiting
        await self._apply_rate_limit()
        
        # Validate and sanitize parameters
        sanitized_params = self._sanitize_params(params)
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=sanitized_params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limited
                    await asyncio.sleep(5)
                    raise Exception("Rate limited by CoinGecko API")
                else:
                    raise Exception(f"API request failed with status {response.status}")
    
    def _sanitize_params(self, params: Dict) -> Dict:
        """Sanitize parameters to ensure they're valid for HTTP requests."""
        sanitized = {}
        for key, value in params.items():
            if isinstance(value, bool):
                sanitized[key] = "true" if value else "false"
            elif isinstance(value, (int, float)):
                sanitized[key] = str(value)
            else:
                sanitized[key] = value
        return sanitized
    
    async def _apply_rate_limit(self):
        """Apply rate limiting for API requests."""
        current_time = datetime.now()
        
        if hasattr(self, '_last_request_time'):
            time_since_last = (current_time - self._last_request_time).total_seconds()
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self._last_request_time = current_time
    
    def _process_market_data(self, data: List[Dict], symbols: List[str]) -> Dict[str, Dict]:
        """Process raw market data from CoinGecko."""
        processed = {}
        
        # Create reverse mapping
        id_to_symbol = {v: k for k, v in self.symbol_mapping.items()}
        
        for coin_data in data:
            coin_id = coin_data.get("id")
            symbol = id_to_symbol.get(coin_id)
            
            if symbol and symbol in symbols:
                processed[symbol] = {
                    "price": float(coin_data.get("current_price", 0)),
                    "market_cap": float(coin_data.get("market_cap", 0)),
                    "volume_24h": float(coin_data.get("total_volume", 0)),
                    "price_change_1h": float(coin_data.get("price_change_percentage_1h_in_currency", 0)),
                    "price_change_24h": float(coin_data.get("price_change_percentage_24h", 0)),
                    "price_change_7d": float(coin_data.get("price_change_percentage_7d_in_currency", 0)),
                    "circulating_supply": float(coin_data.get("circulating_supply", 0)),
                    "total_supply": float(coin_data.get("total_supply", 0)),
                    "ath": float(coin_data.get("ath", 0)),
                    "atl": float(coin_data.get("atl", 0)),
                    "last_updated": coin_data.get("last_updated")
                }
        
        return processed
    
    def _process_historical_data(self, data: Dict) -> Dict:
        """Process historical price data."""
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        
        if not prices:
            return {}
        
        # Calculate basic statistics
        price_values = [price[1] for price in prices]
        
        return {
            "prices": prices,
            "volumes": volumes,
            "min_price": min(price_values),
            "max_price": max(price_values),
            "avg_price": sum(price_values) / len(price_values),
            "volatility": self._calculate_volatility(price_values)
        }
    
    def _process_global_data(self, data: Dict) -> Dict:
        """Process global market data."""
        global_data = data.get("data", {})
        
        return {
            "total_market_cap": global_data.get("total_market_cap", {}).get("usd", 0),
            "total_volume": global_data.get("total_volume", {}).get("usd", 0),
            "bitcoin_dominance": global_data.get("market_cap_percentage", {}).get("btc", 0),
            "active_cryptocurrencies": global_data.get("active_cryptocurrencies", 0),
            "market_cap_change_24h": global_data.get("market_cap_change_percentage_24h_usd", 0)
        }
    
    def _process_trending_data(self, data: Dict) -> List[Dict]:
        """Process trending coins data."""
        trending = []
        
        for coin in data.get("coins", []):
            coin_data = coin.get("item", {})
            trending.append({
                "id": coin_data.get("id"),
                "name": coin_data.get("name"),
                "symbol": coin_data.get("symbol"),
                "market_cap_rank": coin_data.get("market_cap_rank"),
                "price_btc": coin_data.get("price_btc")
            })
        
        return trending
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility."""
        if len(prices) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            return_pct = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(return_pct)
        
        # Calculate standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        
        return (variance ** 0.5) * 100  # Convert to percentage
    
    def _get_cached_prices(self, symbols: List[str]) -> Optional[Dict]:
        """Get prices from cache if still valid."""
        current_time = datetime.now()
        
        cached_data = {}
        all_cached = True
        
        for symbol in symbols:
            if symbol in self.price_cache and symbol in self.last_cache_update:
                cache_age = (current_time - self.last_cache_update[symbol]).total_seconds()
                if cache_age < self.cache_ttl:
                    cached_data[symbol] = self.price_cache[symbol]
                else:
                    all_cached = False
                    break
            else:
                all_cached = False
                break
        
        return cached_data if all_cached else None
    
    def _update_cache(self, data: Dict):
        """Update price cache with new data."""
        current_time = datetime.now()
        
        for symbol, price_data in data.items():
            self.price_cache[symbol] = price_data
            self.last_cache_update[symbol] = current_time
    
    def _get_fallback_prices(self, symbols: List[str]) -> Dict:
        """Get fallback prices when API fails."""
        fallback_data = {}
        
        for symbol in symbols:
            # Use cached data if available, otherwise return dummy data
            if symbol in self.price_cache:
                fallback_data[symbol] = self.price_cache[symbol]
            else:
                fallback_data[symbol] = {
                    "price": 0.0,
                    "market_cap": 0.0,
                    "volume_24h": 0.0,
                    "price_change_1h": 0.0,
                    "price_change_24h": 0.0,
                    "price_change_7d": 0.0,
                    "last_updated": datetime.now().isoformat()
                }
        
        return fallback_data 