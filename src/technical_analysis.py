"""Technical analysis indicators for cryptocurrency trading."""

import math
import statistics
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from .logger import TradingLogger


class TechnicalAnalyzer:
    """Provides technical analysis indicators and signals."""
    
    def __init__(self):
        self.logger = TradingLogger(__name__)
        
        # Price history cache
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.volume_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # Indicator parameters
        self.sma_periods = [20, 50, 200]  # Simple Moving Average periods
        self.ema_periods = [12, 26]       # Exponential Moving Average periods
        self.rsi_period = 14              # RSI period
        self.macd_fast = 12               # MACD fast period
        self.macd_slow = 26               # MACD slow period
        self.macd_signal = 9              # MACD signal period
        self.bb_period = 20               # Bollinger Bands period
        self.bb_std = 2                   # Bollinger Bands standard deviation
    
    def update_price_data(self, symbol: str, price: float, volume: float = 0.0, timestamp: datetime = None):
        """Update price and volume data for a symbol."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Initialize lists if not exist
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []
        
        # Add new data point
        self.price_history[symbol].append((timestamp, price))
        self.volume_history[symbol].append((timestamp, volume))
        
        # Keep only last 300 data points (approximately 1 day of 5-min intervals)
        if len(self.price_history[symbol]) > 300:
            self.price_history[symbol] = self.price_history[symbol][-300:]
            self.volume_history[symbol] = self.volume_history[symbol][-300:]
    
    def get_technical_indicators(self, symbol: str) -> Dict:
        """Calculate all technical indicators for a symbol."""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return self._get_empty_indicators()
        
        prices = [price for _, price in self.price_history[symbol]]
        volumes = [volume for _, volume in self.volume_history[symbol]]
        
        indicators = {}
        
        try:
            # Moving Averages
            indicators["sma"] = self._calculate_sma(prices)
            indicators["ema"] = self._calculate_ema(prices)
            
            # Momentum Indicators
            indicators["rsi"] = self._calculate_rsi(prices)
            indicators["macd"] = self._calculate_macd(prices)
            
            # Volatility Indicators
            indicators["bollinger_bands"] = self._calculate_bollinger_bands(prices)
            indicators["atr"] = self._calculate_atr(prices)
            
            # Volume Indicators
            indicators["volume_sma"] = self._calculate_volume_sma(volumes)
            indicators["volume_ratio"] = self._calculate_volume_ratio(volumes)
            
            # Trend Indicators
            indicators["trend_strength"] = self._calculate_trend_strength(prices)
            indicators["support_resistance"] = self._find_support_resistance(prices)
            
            # Price Action
            indicators["price_action"] = self._analyze_price_action(prices)
            
        except Exception as e:
            self.logger.log_error("get_technical_indicators", e)
            return self._get_empty_indicators()
        
        return indicators
    
    def _calculate_sma(self, prices: List[float]) -> Dict:
        """Calculate Simple Moving Averages."""
        sma = {}
        for period in self.sma_periods:
            if len(prices) >= period:
                sma[f"sma_{period}"] = sum(prices[-period:]) / period
        return sma
    
    def _calculate_ema(self, prices: List[float]) -> Dict:
        """Calculate Exponential Moving Averages."""
        ema = {}
        
        for period in self.ema_periods:
            if len(prices) >= period:
                ema_value = self._ema_calculation(prices, period)
                ema[f"ema_{period}"] = ema_value
        
        return ema
    
    def _ema_calculation(self, prices: List[float], period: int) -> float:
        """Calculate EMA using standard formula."""
        multiplier = 2 / (period + 1)
        ema = prices[0]  # Start with first price
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float]) -> Dict:
        """Calculate Relative Strength Index."""
        if len(prices) < self.rsi_period + 1:
            return {"rsi": 50.0, "signal": "NEUTRAL"}
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # Calculate average gains and losses
        avg_gain = sum(gains[-self.rsi_period:]) / self.rsi_period
        avg_loss = sum(losses[-self.rsi_period:]) / self.rsi_period
        
        # Calculate RSI
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Generate signal
        if rsi > 70:
            signal = "OVERBOUGHT"
        elif rsi < 30:
            signal = "OVERSOLD"
        else:
            signal = "NEUTRAL"
        
        return {"rsi": rsi, "signal": signal}
    
    def _calculate_macd(self, prices: List[float]) -> Dict:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < self.macd_slow:
            return {"macd": 0, "signal": 0, "histogram": 0, "trend": "NEUTRAL"}
        
        # Calculate EMAs
        ema_fast = self._ema_calculation(prices, self.macd_fast)
        ema_slow = self._ema_calculation(prices, self.macd_slow)
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # For signal line, we need MACD history (simplified calculation)
        macd_values = []
        if len(prices) >= self.macd_slow + self.macd_signal:
            for i in range(self.macd_slow, len(prices)):
                window_prices = prices[:i+1]
                fast_ema = self._ema_calculation(window_prices, self.macd_fast)
                slow_ema = self._ema_calculation(window_prices, self.macd_slow)
                macd_values.append(fast_ema - slow_ema)
        
        # Signal line (EMA of MACD)
        if len(macd_values) >= self.macd_signal:
            signal_line = self._ema_calculation(macd_values, self.macd_signal)
        else:
            signal_line = macd_line
        
        # Histogram
        histogram = macd_line - signal_line
        
        # Generate trend signal
        if macd_line > signal_line and histogram > 0:
            trend = "BULLISH"
        elif macd_line < signal_line and histogram < 0:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
            "trend": trend
        }
    
    def _calculate_bollinger_bands(self, prices: List[float]) -> Dict:
        """Calculate Bollinger Bands."""
        if len(prices) < self.bb_period:
            return {"upper": 0, "middle": 0, "lower": 0, "width": 0, "position": "NEUTRAL"}
        
        # Middle band (SMA)
        sma = sum(prices[-self.bb_period:]) / self.bb_period
        
        # Standard deviation
        variance = sum((price - sma) ** 2 for price in prices[-self.bb_period:]) / self.bb_period
        std_dev = math.sqrt(variance)
        
        # Upper and lower bands
        upper_band = sma + (self.bb_std * std_dev)
        lower_band = sma - (self.bb_std * std_dev)
        
        # Band width (volatility measure)
        width = (upper_band - lower_band) / sma * 100
        
        # Current price position
        current_price = prices[-1]
        if current_price > upper_band:
            position = "ABOVE_UPPER"
        elif current_price < lower_band:
            position = "BELOW_LOWER"
        elif current_price > sma:
            position = "UPPER_HALF"
        else:
            position = "LOWER_HALF"
        
        return {
            "upper": upper_band,
            "middle": sma,
            "lower": lower_band,
            "width": width,
            "position": position
        }
    
    def _calculate_atr(self, prices: List[float]) -> float:
        """Calculate Average True Range (volatility measure)."""
        if len(prices) < 15:
            return 0.0
        
        # Simplified ATR calculation using high-low ranges
        ranges = []
        for i in range(1, len(prices)):
            # Using price differences as proxy for true range
            daily_range = abs(prices[i] - prices[i-1])
            ranges.append(daily_range)
        
        # Average of last 14 periods
        if len(ranges) >= 14:
            return sum(ranges[-14:]) / 14
        else:
            return sum(ranges) / len(ranges) if ranges else 0.0
    
    def _calculate_volume_sma(self, volumes: List[float]) -> float:
        """Calculate volume simple moving average."""
        if len(volumes) < 20:
            return 0.0
        
        return sum(volumes[-20:]) / 20
    
    def _calculate_volume_ratio(self, volumes: List[float]) -> float:
        """Calculate current volume relative to average."""
        if len(volumes) < 20:
            return 1.0
        
        current_volume = volumes[-1]
        avg_volume = sum(volumes[-20:]) / 20
        
        return current_volume / avg_volume if avg_volume > 0 else 1.0
    
    def _calculate_trend_strength(self, prices: List[float]) -> Dict:
        """Calculate trend strength and direction."""
        if len(prices) < 20:
            return {"strength": 0, "direction": "SIDEWAYS"}
        
        # Calculate trend using linear regression slope
        n = len(prices[-20:])  # Use last 20 periods
        x_values = list(range(n))
        y_values = prices[-20:]
        
        # Linear regression slope
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Normalize slope to strength (0-100)
        price_range = max(prices[-20:]) - min(prices[-20:])
        if price_range > 0:
            strength = min(abs(slope) / price_range * 100 * 20, 100)  # Scale to 0-100
        else:
            strength = 0
        
        # Determine direction
        if slope > 0.001:
            direction = "UPTREND"
        elif slope < -0.001:
            direction = "DOWNTREND"
        else:
            direction = "SIDEWAYS"
        
        return {"strength": strength, "direction": direction}
    
    def _find_support_resistance(self, prices: List[float]) -> Dict:
        """Find support and resistance levels."""
        if len(prices) < 50:
            return {"support": 0, "resistance": 0, "strength": 0}
        
        # Use recent price data
        recent_prices = prices[-50:]
        current_price = prices[-1]
        
        # Find local highs and lows
        highs = []
        lows = []
        
        for i in range(2, len(recent_prices) - 2):
            # Local high
            if (recent_prices[i] > recent_prices[i-1] and 
                recent_prices[i] > recent_prices[i+1] and
                recent_prices[i] > recent_prices[i-2] and
                recent_prices[i] > recent_prices[i+2]):
                highs.append(recent_prices[i])
            
            # Local low
            if (recent_prices[i] < recent_prices[i-1] and 
                recent_prices[i] < recent_prices[i+1] and
                recent_prices[i] < recent_prices[i-2] and
                recent_prices[i] < recent_prices[i+2]):
                lows.append(recent_prices[i])
        
        # Find closest support and resistance
        support = max([low for low in lows if low < current_price], default=min(recent_prices))
        resistance = min([high for high in highs if high > current_price], default=max(recent_prices))
        
        # Calculate strength based on how many times levels were tested
        support_strength = sum(1 for price in recent_prices if abs(price - support) / support < 0.02)
        resistance_strength = sum(1 for price in recent_prices if abs(price - resistance) / resistance < 0.02)
        
        return {
            "support": support,
            "resistance": resistance,
            "strength": (support_strength + resistance_strength) / 2
        }
    
    def _analyze_price_action(self, prices: List[float]) -> Dict:
        """Analyze recent price action patterns."""
        if len(prices) < 10:
            return {"pattern": "INSUFFICIENT_DATA", "momentum": "NEUTRAL"}
        
        recent = prices[-10:]
        current = prices[-1]
        
        # Calculate momentum
        momentum_5 = (current - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
        momentum_10 = (current - prices[-10]) / prices[-10] * 100 if len(prices) >= 10 else 0
        
        # Determine momentum direction
        if momentum_5 > 2:
            momentum = "STRONG_UP"
        elif momentum_5 > 0.5:
            momentum = "UP"
        elif momentum_5 < -2:
            momentum = "STRONG_DOWN"
        elif momentum_5 < -0.5:
            momentum = "DOWN"
        else:
            momentum = "NEUTRAL"
        
        # Simple pattern recognition
        if len(recent) >= 5:
            if all(recent[i] > recent[i-1] for i in range(1, 5)):
                pattern = "STRONG_UPTREND"
            elif all(recent[i] < recent[i-1] for i in range(1, 5)):
                pattern = "STRONG_DOWNTREND"
            elif recent[-1] > recent[-3] and recent[-2] < recent[-3]:
                pattern = "POTENTIAL_REVERSAL_UP"
            elif recent[-1] < recent[-3] and recent[-2] > recent[-3]:
                pattern = "POTENTIAL_REVERSAL_DOWN"
            else:
                pattern = "CONSOLIDATION"
        else:
            pattern = "INSUFFICIENT_DATA"
        
        return {
            "pattern": pattern,
            "momentum": momentum,
            "momentum_5": momentum_5,
            "momentum_10": momentum_10
        }
    
    def _get_empty_indicators(self) -> Dict:
        """Return empty indicators when insufficient data."""
        return {
            "sma": {},
            "ema": {},
            "rsi": {"rsi": 50.0, "signal": "NEUTRAL"},
            "macd": {"macd": 0, "signal": 0, "histogram": 0, "trend": "NEUTRAL"},
            "bollinger_bands": {"upper": 0, "middle": 0, "lower": 0, "width": 0, "position": "NEUTRAL"},
            "atr": 0.0,
            "volume_sma": 0.0,
            "volume_ratio": 1.0,
            "trend_strength": {"strength": 0, "direction": "SIDEWAYS"},
            "support_resistance": {"support": 0, "resistance": 0, "strength": 0},
            "price_action": {"pattern": "INSUFFICIENT_DATA", "momentum": "NEUTRAL"}
        }
    
    def generate_trading_signals(self, symbol: str) -> Dict:
        """Generate comprehensive trading signals based on all indicators."""
        indicators = self.get_technical_indicators(symbol)
        
        signals = {
            "overall_signal": "NEUTRAL",
            "strength": 0,  # 0-100
            "bullish_factors": [],
            "bearish_factors": [],
            "neutral_factors": []
        }
        
        try:
            # RSI signals
            rsi_data = indicators.get("rsi", {})
            if rsi_data.get("signal") == "OVERSOLD":
                signals["bullish_factors"].append("RSI oversold (potential bounce)")
            elif rsi_data.get("signal") == "OVERBOUGHT":
                signals["bearish_factors"].append("RSI overbought (potential decline)")
            else:
                signals["neutral_factors"].append("RSI neutral")
            
            # MACD signals
            macd_data = indicators.get("macd", {})
            if macd_data.get("trend") == "BULLISH":
                signals["bullish_factors"].append("MACD bullish crossover")
            elif macd_data.get("trend") == "BEARISH":
                signals["bearish_factors"].append("MACD bearish crossover")
            else:
                signals["neutral_factors"].append("MACD neutral")
            
            # Moving average signals
            sma_data = indicators.get("sma", {})
            current_price = self.price_history[symbol][-1][1] if symbol in self.price_history else 0
            
            if "sma_20" in sma_data and current_price > sma_data["sma_20"]:
                signals["bullish_factors"].append("Price above SMA-20")
            elif "sma_20" in sma_data:
                signals["bearish_factors"].append("Price below SMA-20")
            
            # Bollinger Bands signals
            bb_data = indicators.get("bollinger_bands", {})
            if bb_data.get("position") == "BELOW_LOWER":
                signals["bullish_factors"].append("Price below lower Bollinger Band (oversold)")
            elif bb_data.get("position") == "ABOVE_UPPER":
                signals["bearish_factors"].append("Price above upper Bollinger Band (overbought)")
            
            # Trend strength signals
            trend_data = indicators.get("trend_strength", {})
            if trend_data.get("direction") == "UPTREND" and trend_data.get("strength", 0) > 50:
                signals["bullish_factors"].append("Strong uptrend detected")
            elif trend_data.get("direction") == "DOWNTREND" and trend_data.get("strength", 0) > 50:
                signals["bearish_factors"].append("Strong downtrend detected")
            
            # Price action signals
            price_action = indicators.get("price_action", {})
            if price_action.get("momentum") in ["STRONG_UP", "UP"]:
                signals["bullish_factors"].append("Positive price momentum")
            elif price_action.get("momentum") in ["STRONG_DOWN", "DOWN"]:
                signals["bearish_factors"].append("Negative price momentum")
            
            # Calculate overall signal and strength
            bullish_score = len(signals["bullish_factors"])
            bearish_score = len(signals["bearish_factors"])
            
            if bullish_score > bearish_score + 1:
                signals["overall_signal"] = "BULLISH"
                signals["strength"] = min((bullish_score - bearish_score) * 20, 100)
            elif bearish_score > bullish_score + 1:
                signals["overall_signal"] = "BEARISH"
                signals["strength"] = min((bearish_score - bullish_score) * 20, 100)
            else:
                signals["overall_signal"] = "NEUTRAL"
                signals["strength"] = 0
            
        except Exception as e:
            self.logger.log_error("generate_trading_signals", e)
        
        return signals 