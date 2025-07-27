"""Risk management system for cryptocurrency trading."""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from .logger import TradingLogger


class RiskManager:
    """Comprehensive risk management for cryptocurrency trading."""
    
    def __init__(self, config, exchange=None):
        self.config = config
        self.logger = TradingLogger(__name__)
        self._exchange_ref = exchange  # Reference to exchange for getting symbol info
        
        # Risk tracking
        self.daily_trades = []
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_portfolio_value = 0.0
        
        # Emergency stops
        self.emergency_stop_triggered = False
        self.last_emergency_check = datetime.now()
    
    async def evaluate_trade_risk(self, 
                                  action: str, 
                                  symbol: str, 
                                  allocation_percentage: float,
                                  portfolio_data: Dict,
                                  market_data: Dict) -> Dict:
        """Evaluate risk for a proposed trade."""
        
        risk_assessment = {
            "approved": False,
            "risk_score": 0.0,
            "warnings": [],
            "adjustments": {},
            "reason": ""
        }
        
        try:
            # Get current portfolio metrics
            portfolio_value = portfolio_data.get("total_value", 0)
            available_balance = portfolio_data.get("available_balance", 0)
            current_positions = portfolio_data.get("positions", {})
            
            # Basic validation checks
            if not self._basic_validation_checks(action, symbol, allocation_percentage, portfolio_value, risk_assessment):
                return risk_assessment
            
            # Check daily trade limits
            if not self._check_daily_limits(risk_assessment):
                return risk_assessment
            
            # Check position limits
            if not self._check_position_limits(current_positions, symbol, action, risk_assessment):
                return risk_assessment
            
            # Check portfolio concentration
            concentration_risk = self._check_concentration_risk(
                current_positions, symbol, allocation_percentage, portfolio_value, action
            )
            risk_assessment["risk_score"] += concentration_risk
            
            # Check volatility risk
            volatility_risk = self._check_volatility_risk(symbol, market_data, allocation_percentage)
            risk_assessment["risk_score"] += volatility_risk
            
            # Check correlation risk
            correlation_risk = self._check_correlation_risk(current_positions, symbol, action)
            risk_assessment["risk_score"] += correlation_risk
            
            # Calculate position size adjustments
            adjusted_allocation = await self._calculate_safe_position_size(
                allocation_percentage, risk_assessment["risk_score"], available_balance, portfolio_value, symbol
            )
            
            if adjusted_allocation != allocation_percentage:
                risk_assessment["adjustments"]["allocation_percentage"] = adjusted_allocation
                risk_assessment["warnings"].append(f"Position size adjusted from {allocation_percentage}% to {adjusted_allocation}%")
            
            # Final risk score assessment
            if risk_assessment["risk_score"] <= 3.0:
                risk_assessment["approved"] = True
                risk_assessment["reason"] = "Trade approved - Low risk"
            elif risk_assessment["risk_score"] <= 6.0:
                risk_assessment["approved"] = True
                risk_assessment["reason"] = "Trade approved with adjustments - Medium risk"
            else:
                risk_assessment["approved"] = False
                risk_assessment["reason"] = "Trade rejected - High risk"
            
            return risk_assessment
            
        except Exception as e:
            self.logger.log_error("evaluate_trade_risk", e)
            risk_assessment["reason"] = f"Risk evaluation failed: {e}"
            return risk_assessment
    
    def _basic_validation_checks(self, action: str, symbol: str, allocation_percentage: float, 
                                portfolio_value: float, risk_assessment: Dict) -> bool:
        """Perform basic validation checks."""
        
        # Check if emergency stop is triggered
        if self.emergency_stop_triggered:
            risk_assessment["reason"] = "Emergency stop is active"
            return False
        
        # Validate action
        if action not in ["BUY", "SELL", "CLOSE"]:
            risk_assessment["reason"] = f"Invalid action: {action}"
            return False
        
        # Validate symbol
        if symbol not in self.config.supported_symbols:
            risk_assessment["reason"] = f"Unsupported symbol: {symbol}"
            return False
        
        # Validate allocation percentage for BUY orders
        if action == "BUY":
            if allocation_percentage <= 0 or allocation_percentage > 100:
                risk_assessment["reason"] = f"Invalid allocation percentage: {allocation_percentage}%"
                return False
            
            max_single_trade_risk = float(self.config.max_portfolio_risk) * 100
            if allocation_percentage > max_single_trade_risk:
                risk_assessment["reason"] = f"Trade size {allocation_percentage}% exceeds max risk {max_single_trade_risk}%"
                return False
        
        # Check minimum portfolio value
        if portfolio_value < float(self.config.min_trade_amount):
            risk_assessment["reason"] = f"Portfolio value too low for trading: ${portfolio_value}"
            return False
        
        return True
    
    def _check_daily_limits(self, risk_assessment: Dict) -> bool:
        """Check daily trading limits."""
        
        # Clean up old trades (older than 24 hours)
        current_time = datetime.now()
        self.daily_trades = [
            trade for trade in self.daily_trades 
            if (current_time - trade["timestamp"]).total_seconds() < 86400  # 24 hours
        ]
        
        # Check daily trade count
        if len(self.daily_trades) >= self.config.max_trades_per_day:
            risk_assessment["reason"] = f"Daily trade limit reached: {len(self.daily_trades)}/{self.config.max_trades_per_day}"
            return False
        
        # Check daily loss limit (if we're tracking PnL)
        daily_loss_limit = float(self.config.emergency_stop_loss) * 0.5  # 50% of emergency stop
        if self.daily_pnl < -daily_loss_limit:
            risk_assessment["reason"] = f"Daily loss limit exceeded: {self.daily_pnl:.2%}"
            return False
        
        return True
    
    def _check_position_limits(self, current_positions: Dict, symbol: str, action: str, risk_assessment: Dict) -> bool:
        """Check position count limits."""
        
        if action == "BUY":
            # Check if we already have this position
            if symbol in current_positions:
                risk_assessment["warnings"].append(f"Already have position in {symbol}")
                risk_assessment["risk_score"] += 1.0
            
            # Check maximum open positions
            if len(current_positions) >= self.config.max_open_positions:
                risk_assessment["reason"] = f"Maximum positions reached: {len(current_positions)}/{self.config.max_open_positions}"
                return False
        
        elif action in ["SELL", "CLOSE"]:
            # Check if we have the position to sell
            if symbol not in current_positions:
                risk_assessment["reason"] = f"No position found for {symbol} to sell/close"
                return False
        
        return True
    
    def _check_concentration_risk(self, current_positions: Dict, symbol: str, 
                                 allocation_percentage: float, portfolio_value: float, action: str) -> float:
        """Check portfolio concentration risk."""
        
        risk_score = 0.0
        
        if action == "BUY":
            # Calculate what the concentration would be after this trade
            trade_value = (allocation_percentage / 100) * portfolio_value
            
            # Check single position concentration
            max_position_size = float(self.config.max_portfolio_risk) * 5  # 5x the max risk per trade
            position_concentration = (trade_value / portfolio_value) * 100
            
            if position_concentration > max_position_size:
                risk_score += 3.0
            elif position_concentration > max_position_size * 0.7:
                risk_score += 1.5
            
            # Check sector concentration (all crypto positions)
            total_crypto_value = sum(pos.get("value", 0) for pos in current_positions.values())
            new_crypto_concentration = ((total_crypto_value + trade_value) / portfolio_value) * 100
            
            if new_crypto_concentration > 80:  # 80% in crypto is very high risk
                risk_score += 2.0
            elif new_crypto_concentration > 60:
                risk_score += 1.0
        
        return risk_score
    
    def _check_volatility_risk(self, symbol: str, market_data: Dict, allocation_percentage: float) -> float:
        """Check volatility-based risk."""
        
        risk_score = 0.0
        
        symbol_data = market_data.get(symbol, {})
        
        # Check 24h price change
        price_change_24h = abs(symbol_data.get("price_change_24h", 0))
        
        if price_change_24h > 20:  # More than 20% change in 24h
            risk_score += 2.0
        elif price_change_24h > 10:
            risk_score += 1.0
        
        # Check volume
        volume_24h = symbol_data.get("volume_24h", 0)
        market_cap = symbol_data.get("market_cap", 0)
        
        if market_cap > 0:
            volume_ratio = volume_24h / market_cap
            if volume_ratio < 0.01:  # Very low liquidity
                risk_score += 1.5
        
        # Adjust risk based on position size
        if allocation_percentage > 15:  # Large position in volatile asset
            risk_score *= 1.5
        
        return risk_score
    
    def _check_correlation_risk(self, current_positions: Dict, symbol: str, action: str) -> float:
        """Check correlation risk between positions."""
        
        risk_score = 0.0
        
        if action == "BUY" and current_positions:
            # Simplified correlation check - all crypto assets are somewhat correlated
            crypto_positions = len(current_positions)
            
            # Major coins (BTC, ETH) have lower correlation risk
            major_coins = ["BTCUSDT", "ETHUSDT"]
            
            if symbol not in major_coins:
                # Adding more altcoins increases correlation risk
                altcoin_count = sum(1 for pos_symbol in current_positions.keys() 
                                  if pos_symbol not in major_coins)
                
                if altcoin_count >= 2:
                    risk_score += 1.0
                if altcoin_count >= 4:
                    risk_score += 1.0
        
        return risk_score
    
    async def _calculate_safe_position_size(self, requested_allocation: float, risk_score: float, 
                                           available_balance: float, portfolio_value: float, symbol: str = None) -> float:
        """Calculate safe position size based on risk score and real Binance minimums."""
        
        # Base allocation adjustment based on risk score
        risk_multiplier = max(0.2, 1.0 - (risk_score * 0.15))  # Reduce by 15% per risk point
        
        adjusted_allocation = requested_allocation * risk_multiplier
        
        # Ensure we don't exceed available balance
        max_allocation_by_balance = (available_balance / portfolio_value) * 100 * 0.9  # 90% of available
        adjusted_allocation = min(adjusted_allocation, max_allocation_by_balance)
        
        # Get real minimum trade value from Binance if symbol provided
        min_trade_value = float(self.config.min_trade_amount)  # Fallback
        
        if symbol and hasattr(self, '_exchange_ref'):
            try:
                # Get real Binance minimum for this symbol
                symbol_info = await self._exchange_ref.get_symbol_info(symbol)
                min_trade_value = symbol_info.get("min_notional", min_trade_value)
                self.logger.logger.info(f"Using real Binance minimum ${min_trade_value:.2f} for {symbol}")
            except Exception:
                self.logger.logger.warning(f"Could not get Binance minimums for {symbol}, using config default")
        
        min_allocation = (min_trade_value / portfolio_value) * 100
        
        # If requested trade is below minimum, try to adjust upward (but within risk limits)
        if adjusted_allocation < min_allocation:
            max_risk_allocation = float(self.config.max_portfolio_risk) * 100  # Max risk per trade
            
            self.logger.logger.info(f"Need {min_allocation:.1f}% allocation (${min_trade_value:.2f}) vs max risk {max_risk_allocation:.1f}%")
            
            if min_allocation <= max_risk_allocation:
                # Increase to minimum if within risk limits
                adjusted_allocation = min_allocation
                self.logger.logger.info(f"✅ Increased allocation to {min_allocation:.1f}% to meet Binance minimum ${min_trade_value:.2f}")
            else:
                # Try a smaller symbol or reject the trade
                self.logger.logger.warning(f"❌ {symbol} requires {min_allocation:.1f}% but max risk is {max_risk_allocation:.1f}%")
                self.logger.logger.info(f"💡 Consider trading a symbol with lower minimum or adding more funds")
                return 0.0
        
        # Round to reasonable precision
        return round(adjusted_allocation, 2)
    
    async def check_emergency_stops(self, portfolio_data: Dict) -> bool:
        """Check for emergency stop conditions."""
        
        try:
            portfolio_value = portfolio_data.get("total_value", 0)
            
            # Update peak portfolio value
            if portfolio_value > self.peak_portfolio_value:
                self.peak_portfolio_value = portfolio_value
            
            # Calculate current drawdown
            if self.peak_portfolio_value > 0:
                current_drawdown = (self.peak_portfolio_value - portfolio_value) / self.peak_portfolio_value
                self.max_drawdown = max(self.max_drawdown, current_drawdown)
                
                # Check emergency stop threshold
                emergency_threshold = float(self.config.emergency_stop_loss)
                if current_drawdown >= emergency_threshold:
                    if not self.emergency_stop_triggered:
                        self.emergency_stop_triggered = True
                        self.logger.log_risk_event(
                            "EMERGENCY_STOP", 
                            f"Portfolio drawdown {current_drawdown:.2%} exceeds threshold {emergency_threshold:.2%}"
                        )
                    return True
            
            return False
            
        except Exception as e:
            self.logger.log_error("check_emergency_stops", e)
            return False
    
    def record_trade(self, action: str, symbol: str, amount: float, success: bool):
        """Record a completed trade for risk tracking."""
        
        trade_record = {
            "timestamp": datetime.now(),
            "action": action,
            "symbol": symbol,
            "amount": amount,
            "success": success
        }
        
        self.daily_trades.append(trade_record)
    
    def get_risk_metrics(self, portfolio_data: Dict, market_data: Dict) -> Dict:
        """Calculate current risk metrics for the portfolio."""
        
        try:
            portfolio_value = portfolio_data.get("total_value", 0)
            positions = portfolio_data.get("positions", {})
            
            # Portfolio risk metrics
            position_count = len(positions)
            
            # Calculate portfolio concentration
            largest_position = 0.0
            total_crypto_value = 0.0
            
            for position in positions.values():
                position_value = position.get("value", 0)
                total_crypto_value += position_value
                
                if portfolio_value > 0:
                    position_pct = (position_value / portfolio_value) * 100
                    largest_position = max(largest_position, position_pct)
            
            crypto_concentration = (total_crypto_value / portfolio_value * 100) if portfolio_value > 0 else 0
            
            # Calculate average volatility
            total_volatility = 0.0
            volatility_count = 0
            
            for symbol, position in positions.items():
                symbol_data = market_data.get(symbol, {})
                price_change_24h = abs(symbol_data.get("price_change_24h", 0))
                total_volatility += price_change_24h
                volatility_count += 1
            
            avg_volatility = total_volatility / volatility_count if volatility_count > 0 else 0
            
            # Overall portfolio risk score
            portfolio_risk = 0.0
            
            # Risk from position count
            if position_count > self.config.max_open_positions * 0.8:
                portfolio_risk += 1.0
            
            # Risk from concentration
            if largest_position > 20:
                portfolio_risk += 2.0
            elif largest_position > 10:
                portfolio_risk += 1.0
            
            if crypto_concentration > 80:
                portfolio_risk += 2.0
            elif crypto_concentration > 60:
                portfolio_risk += 1.0
            
            # Risk from volatility
            if avg_volatility > 15:
                portfolio_risk += 1.5
            elif avg_volatility > 10:
                portfolio_risk += 1.0
            
            return {
                "portfolio_risk": portfolio_risk,
                "position_count": position_count,
                "max_positions": self.config.max_open_positions,
                "largest_position_pct": largest_position,
                "crypto_concentration": crypto_concentration,
                "avg_volatility": avg_volatility,
                "max_drawdown": self.max_drawdown * 100,
                "daily_trades": len(self.daily_trades),
                "emergency_stop_active": self.emergency_stop_triggered,
                "correlation_risk": min(position_count * 0.5, 5.0)  # Simplified correlation measure
            }
            
        except Exception as e:
            self.logger.log_error("get_risk_metrics", e)
            return {
                "portfolio_risk": 10.0,  # High risk if calculation fails
                "error": str(e)
            }
    
    def calculate_var(self, portfolio_data: Dict, market_data: Dict, confidence_level: float = 0.05) -> float:
        """Calculate Value at Risk (VaR) for the portfolio."""
        try:
            positions = portfolio_data.get("positions", {})
            portfolio_value = portfolio_data.get("total_value", 0)
            
            if not positions or portfolio_value == 0:
                return 0.0
            
            # Simplified VaR calculation using volatility
            portfolio_volatility = 0.0
            
            for symbol, position in positions.items():
                weight = position.get("value", 0) / portfolio_value
                
                # Get historical volatility estimate
                symbol_data = market_data.get(symbol, {})
                daily_volatility = abs(symbol_data.get("price_change_24h", 0)) / 100
                
                portfolio_volatility += (weight ** 2) * (daily_volatility ** 2)
            
            # Add correlation effect (simplified)
            if len(positions) > 1:
                avg_correlation = 0.7  # Assume 70% correlation between crypto assets
                for i, symbol1 in enumerate(positions.keys()):
                    for j, symbol2 in enumerate(positions.keys()):
                        if i != j:
                            weight1 = positions[symbol1].get("value", 0) / portfolio_value
                            weight2 = positions[symbol2].get("value", 0) / portfolio_value
                            vol1 = abs(market_data.get(symbol1, {}).get("price_change_24h", 0)) / 100
                            vol2 = abs(market_data.get(symbol2, {}).get("price_change_24h", 0)) / 100
                            
                            portfolio_volatility += 2 * weight1 * weight2 * vol1 * vol2 * avg_correlation
            
            portfolio_volatility = math.sqrt(portfolio_volatility)
            
            # Calculate VaR using normal distribution assumption
            # Z-score for 95% confidence = 1.645
            z_score = 1.645 if confidence_level == 0.05 else 2.326
            
            var_amount = portfolio_value * portfolio_volatility * z_score
            
            return var_amount
            
        except Exception as e:
            self.logger.log_error("calculate_var", e)
            return 0.0
    
    def stress_test_portfolio(self, portfolio_data: Dict, market_data: Dict) -> Dict[str, float]:
        """Perform stress testing scenarios on the portfolio."""
        try:
            portfolio_value = portfolio_data.get("total_value", 0)
            positions = portfolio_data.get("positions", {})
            
            if not positions or portfolio_value == 0:
                return {"market_crash": 0.0, "crypto_winter": 0.0, "flash_crash": 0.0}
            
            stress_scenarios = {}
            
            # Scenario 1: Market crash (-50% for all assets)
            crash_loss = 0.0
            for symbol, position in positions.items():
                position_value = position.get("value", 0)
                crash_loss += position_value * 0.5  # 50% loss
            stress_scenarios["market_crash"] = crash_loss
            
            # Scenario 2: Crypto winter (-80% for altcoins, -30% for BTC/ETH)
            winter_loss = 0.0
            major_coins = ["BTCUSDT", "ETHUSDT"]
            for symbol, position in positions.items():
                position_value = position.get("value", 0)
                if symbol in major_coins:
                    winter_loss += position_value * 0.3  # 30% loss
                else:
                    winter_loss += position_value * 0.8  # 80% loss
            stress_scenarios["crypto_winter"] = winter_loss
            
            # Scenario 3: Flash crash (-20% immediate drop)
            flash_loss = portfolio_value * 0.2
            stress_scenarios["flash_crash"] = flash_loss
            
            return stress_scenarios
            
        except Exception as e:
            self.logger.log_error("stress_test_portfolio", e)
            return {"market_crash": 0.0, "crypto_winter": 0.0, "flash_crash": 0.0} 