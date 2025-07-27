"""Main trading bot that orchestrates all components."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from .config import Config
from .logger import TradingLogger
from .ai_advisor import AITradingAdvisor
from .market_data import MarketDataProvider
from .exchange import BinanceExchange
from .risk_manager import RiskManager
from .performance_tracker import PerformanceTracker, Trade, PortfolioSnapshot


class TradingBot:
    """Main cryptocurrency trading bot with AI decision making."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = TradingLogger(__name__)
        
        # Initialize components
        self.ai_advisor = AITradingAdvisor(config)
        self.market_data = MarketDataProvider(config)
        self.exchange = BinanceExchange(config)
        self.risk_manager = RiskManager(config, self.exchange)  # Pass exchange reference
        self.performance_tracker = PerformanceTracker(initial_balance=float(config.demo_initial_balance), exchange=self.exchange)
        
        # Trading state
        self.is_running = False
        self.cycle_count = 0
        self.last_portfolio_update = None
    
    async def initialize(self):
        """Initialize all bot components."""
        try:
            self.logger.logger.info("Initializing trading bot...")
            
            # Initialize exchange connection
            await self.exchange.initialize()
            
            # Get initial portfolio status
            await self._update_portfolio_status()
            
            self.logger.logger.info("Trading bot initialization complete")
            
        except Exception as e:
            self.logger.log_error("initialize", e)
            raise
    
    async def run_cycle(self):
        """Run one complete trading cycle."""
        try:
            self.cycle_count += 1
            self.logger.logger.info(f"Starting trading cycle #{self.cycle_count}")
            
            # 1. Update portfolio status
            portfolio_data = await self._update_portfolio_status()
            
            # 1.5. Process any manual trade requests from dashboard
            await self._process_manual_trade_requests()
            
            # 2. Check emergency stops
            emergency_triggered = await self.risk_manager.check_emergency_stops(portfolio_data)
            if emergency_triggered:
                self.logger.log_risk_event("EMERGENCY_STOP", "Emergency stop triggered, skipping trading cycle")
                return
            
            # 3. Get current market data
            market_data = await self.market_data.get_current_prices(self.config.supported_symbols)
            if not market_data:
                self.logger.logger.warning("No market data available, skipping cycle")
                return
            
            # 4. Calculate risk metrics
            risk_metrics = self.risk_manager.get_risk_metrics(portfolio_data, market_data)
            
            # 5. Get AI trading decision
            ai_decision = await self.ai_advisor.get_trading_decision(
                market_data, portfolio_data, risk_metrics
            )
            
            # 6. Evaluate and execute trade if approved
            await self._process_trading_decision(ai_decision, portfolio_data, market_data)
            
            # 7. Log cycle completion
            self._log_cycle_summary(portfolio_data, risk_metrics, ai_decision)
            
        except Exception as e:
            self.logger.log_error("run_cycle", e)
    
    async def _process_manual_trade_requests(self):
        """Process manual trade requests from dashboard."""
        try:
            # Check for manual trade queue file
            import os
            import json
            
            queue_file = 'logs/manual_trades_queue.json'
            if not os.path.exists(queue_file):
                return
            
            # Read all pending requests
            with open(queue_file, 'r') as f:
                lines = f.readlines()
            
            if not lines:
                return
            
            processed_requests = []
            remaining_requests = []
            
            for line in lines:
                if not line.strip():
                    continue
                    
                try:
                    request = json.loads(line.strip())
                    
                    # Skip if already processed
                    if request.get('status') != 'pending':
                        continue
                    
                    self.logger.logger.info(f"Processing manual trade request: {request}")
                    
                    # Execute the trade
                    action = request.get('action')
                    symbol = request.get('symbol')
                    allocation = request.get('allocation', 10.0)
                    
                    # Use the force_trade method
                    result = await self.force_trade(action, symbol, allocation)
                    
                    # Update request status
                    request['status'] = 'completed' if result else 'failed'
                    request['processed_at'] = datetime.now().isoformat()
                    request['result'] = str(result)
                    
                    processed_requests.append(request)
                    
                    self.logger.logger.info(f"Manual trade request processed: {request['status']}")
                    
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue
                except Exception as e:
                    self.logger.logger.error(f"Error processing manual trade request: {e}")
                    continue
            
            # Rewrite the queue file with only unprocessed requests
            with open(queue_file, 'w') as f:
                for request in remaining_requests:
                    f.write(json.dumps(request) + '\n')
            
            # Log processed requests to a separate file
            if processed_requests:
                with open('logs/manual_trades_processed.json', 'a') as f:
                    for request in processed_requests:
                        f.write(json.dumps(request) + '\n')
            
        except Exception as e:
            self.logger.log_error("_process_manual_trade_requests", e)
    
    async def _update_portfolio_status(self) -> Dict:
        """Update and return current portfolio status."""
        try:
            portfolio_data = await self.exchange.get_portfolio_value()
            
            # Log portfolio update
            total_value = portfolio_data.get("total_value", 0)
            positions = portfolio_data.get("positions", {})
            available_balance = portfolio_data.get("available_balance", 0)
            
            # Calculate unrealized PnL (simplified)
            total_pnl = 0.0
            for position in positions.values():
                total_pnl += position.get("unrealized_pnl", 0)
            
            self.logger.log_portfolio_update(total_value, total_pnl, positions)
            
            # Record portfolio snapshot for performance tracking
            position_values = {symbol: pos.get("value", 0) for symbol, pos in positions.items()}
            snapshot = PortfolioSnapshot(
                timestamp=datetime.now(),
                total_value=total_value,
                available_balance=available_balance,
                positions=position_values,
                unrealized_pnl=total_pnl
            )
            self.performance_tracker.record_portfolio_snapshot(snapshot)
            
            self.last_portfolio_update = portfolio_data
            return portfolio_data
            
        except Exception as e:
            self.logger.log_error("_update_portfolio_status", e)
            return {"total_value": 0, "available_balance": 0, "positions": {}}
    
    async def _process_trading_decision(self, ai_decision: Dict, portfolio_data: Dict, market_data: Dict):
        """Process and execute AI trading decision."""
        try:
            action = ai_decision.get("action", "HOLD")
            symbol = ai_decision.get("symbol")
            allocation_percentage = ai_decision.get("allocation_percentage", 0)
            confidence = ai_decision.get("confidence", 0)
            
            self.logger.logger.info(
                f"AI Decision: {action} {symbol or 'N/A'} "
                f"({allocation_percentage}% allocation, {confidence}/10 confidence)"
            )
            
            # Log AI decision for reference (database removed - using Binance API for analytics)
            self.logger.logger.info(f"AI Decision recorded: {action} {symbol} with {confidence}/10 confidence")
            
            if action == "HOLD":
                self.logger.logger.info("Holding current positions as recommended by AI")
                return
            
            if not symbol:
                self.logger.logger.warning("No symbol specified for action, skipping")
                return
            
            # Evaluate trade risk
            risk_assessment = await self.risk_manager.evaluate_trade_risk(
                action, symbol, allocation_percentage, portfolio_data, market_data
            )
            
            if not risk_assessment.get("approved", False):
                self.logger.logger.warning(f"Trade rejected by risk manager: {risk_assessment.get('reason')}")
                return
            
            # Apply any risk adjustments
            adjustments = risk_assessment.get("adjustments", {})
            if "allocation_percentage" in adjustments:
                allocation_percentage = adjustments["allocation_percentage"]
                self.logger.logger.info(f"Position size adjusted to {allocation_percentage}%")
            
            # Execute the trade
            success = await self._execute_trade(action, symbol, allocation_percentage, portfolio_data)
            
            # Record trade for risk tracking
            self.risk_manager.record_trade(action, symbol, allocation_percentage, success)
            
            # Update AI performance tracking
            if success:
                trade_result = {
                    "symbol": symbol,
                    "action": action,
                    "pnl": 0  # Would need to track this over time
                }
                self.ai_advisor.update_performance(trade_result)
            
        except Exception as e:
            self.logger.log_error("_process_trading_decision", e)
    
    async def _execute_trade(self, action: str, symbol: str, allocation_percentage: float, portfolio_data: Dict) -> bool:
        """Execute a trade based on the decision."""
        try:
            portfolio_value = portfolio_data.get("total_value", 0)
            available_balance = portfolio_data.get("available_balance", 0)
            positions = portfolio_data.get("positions", {})
            
            if action == "BUY":
                # Calculate trade amount
                trade_amount = round((allocation_percentage / 100) * available_balance, 2)
                
                # For small portfolios, use smart minimum trade validation
                # (Risk manager already validated this trade is safe)
                min_trade_amount = float(self.config.min_trade_amount)
                if portfolio_value < 100:  # Small portfolio exception
                    effective_min = max(1.0, portfolio_value * 0.05)  # 5% of portfolio or $1 minimum
                    # Use small tolerance for floating point comparison
                    if trade_amount < (effective_min - 0.01):
                        self.logger.logger.warning(f"Trade amount ${trade_amount:.2f} below effective minimum ${effective_min:.2f} for small portfolio")
                        return False
                elif trade_amount < (min_trade_amount - 0.01):
                    self.logger.logger.warning(f"Trade amount ${trade_amount:.2f} below minimum ${min_trade_amount}")
                    return False
                
                # Execute buy order
                self.logger.logger.info(f"Executing BUY order: {symbol} for ${trade_amount:.2f}")
                
                order_result = await self.exchange.place_buy_order(symbol, trade_amount)
                
                if "error" in order_result:
                    self.logger.logger.error(f"Buy order failed: {order_result['error']}")
                    return False
                
                self.logger.logger.info(f"Buy order successful: {order_result.get('orderId')}")
                
                # Record trade for performance tracking
                trade = Trade(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action="BUY",
                    quantity=float(order_result.get("executedQty", 0)),
                    price=float(order_result.get("price", 0)),
                    amount=trade_amount,
                    order_id=str(order_result.get("orderId", "")),
                    success=True
                )
                self.performance_tracker.record_trade(trade)
                
                return True
            
            elif action in ["SELL", "CLOSE"]:
                # Check if we have the position
                if symbol not in positions:
                    self.logger.logger.warning(f"No position found for {symbol} to sell")
                    return False
                
                position = positions[symbol]
                quantity = position.get("quantity", 0)
                
                if quantity <= 0:
                    self.logger.logger.warning(f"Invalid quantity for {symbol}: {quantity}")
                    return False
                
                # Execute sell order
                self.logger.logger.info(f"Executing SELL order: {symbol} quantity {quantity}")
                
                order_result = await self.exchange.place_sell_order(symbol, quantity)
                
                if "error" in order_result:
                    self.logger.logger.error(f"Sell order failed: {order_result['error']}")
                    return False
                
                self.logger.logger.info(f"Sell order successful: {order_result.get('orderId')}")
                
                # Record trade for performance tracking
                trade = Trade(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action="SELL",
                    quantity=quantity,
                    price=float(order_result.get("price", 0)),
                    amount=quantity * float(order_result.get("price", 0)),
                    order_id=str(order_result.get("orderId", "")),
                    success=True
                )
                self.performance_tracker.record_trade(trade)
                
                return True
            
            else:
                self.logger.logger.warning(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            self.logger.log_error("_execute_trade", e)
            return False
    
    def _log_cycle_summary(self, portfolio_data: Dict, risk_metrics: Dict, ai_decision: Dict):
        """Log summary of the trading cycle."""
        
        total_value = portfolio_data.get("total_value", 0)
        position_count = len(portfolio_data.get("positions", {}))
        portfolio_risk = risk_metrics.get("portfolio_risk", 0)
        
        action = ai_decision.get("action", "HOLD")
        symbol = ai_decision.get("symbol", "N/A")
        confidence = ai_decision.get("confidence", 0)
        
        self.logger.logger.info(
            f"Cycle #{self.cycle_count} Summary: "
            f"Portfolio: ${total_value:.2f}, "
            f"Positions: {position_count}, "
            f"Risk Score: {portfolio_risk:.1f}, "
            f"AI Decision: {action} {symbol} (confidence: {confidence}/10)"
        )
    
    async def shutdown(self):
        """Gracefully shutdown the trading bot."""
        try:
            self.logger.logger.info("Shutting down trading bot...")
            
            # Cancel any open orders (if supported)
            # await self._cancel_open_orders()
            
            # Log final portfolio status
            if self.last_portfolio_update:
                final_value = self.last_portfolio_update.get("total_value", 0)
                positions = self.last_portfolio_update.get("positions", {})
                self.logger.logger.info(
                    f"Final portfolio: ${final_value:.2f} with {len(positions)} positions"
                )
            
            # Shutdown exchange connection with timeout
            try:
                await asyncio.wait_for(self.exchange.shutdown(), timeout=5.0)
                self.logger.logger.info("Exchange shutdown completed")
            except asyncio.TimeoutError:
                self.logger.logger.warning("Exchange shutdown timed out after 5 seconds")
            except Exception as e:
                self.logger.logger.warning(f"Exchange shutdown error: {e}")
            
            self.logger.logger.info("Trading bot shutdown complete")
            
        except Exception as e:
            self.logger.log_error("shutdown", e)
    
    async def get_status(self) -> Dict:
        """Get current bot status for monitoring."""
        try:
            portfolio_data = self.last_portfolio_update or await self._update_portfolio_status()
            risk_metrics = self.risk_manager.get_risk_metrics(portfolio_data, {})
            
            # Get performance metrics
            performance_metrics = self.performance_tracker.get_performance_metrics()
            
            return {
                "cycle_count": self.cycle_count,
                "is_running": self.is_running,
                "portfolio_value": portfolio_data.get("total_value", 0),
                "positions": len(portfolio_data.get("positions", {})),
                "available_balance": portfolio_data.get("available_balance", 0),
                "risk_score": risk_metrics.get("portfolio_risk", 0),
                "emergency_stop": risk_metrics.get("emergency_stop_active", False),
                "daily_trades": risk_metrics.get("daily_trades", 0),
                "max_drawdown": risk_metrics.get("max_drawdown", 0),
                "last_update": datetime.now().isoformat(),
                "performance": {
                    "total_return": performance_metrics.total_return,
                    "total_return_pct": performance_metrics.total_return_pct,
                    "sharpe_ratio": performance_metrics.sharpe_ratio,
                    "win_rate": performance_metrics.win_rate,
                    "total_trades": performance_metrics.total_trades
                }
            }
            
        except Exception as e:
            self.logger.log_error("get_status", e)
            return {"error": str(e)}
    
    async def force_trade(self, action: str, symbol: str, allocation_percentage: float = None) -> Dict:
        """Force execute a trade (for manual intervention)."""
        try:
            self.logger.logger.warning(f"Force trade requested: {action} {symbol}")
            
            # Get current data
            portfolio_data = await self._update_portfolio_status()
            market_data = await self.market_data.get_current_prices([symbol])
            
            # Use default allocation if not specified
            if allocation_percentage is None:
                allocation_percentage = float(self.config.max_portfolio_risk) * 100
            
            # Execute with basic validation only
            success = await self._execute_trade(action, symbol, allocation_percentage, portfolio_data)
            
            return {
                "success": success,
                "action": action,
                "symbol": symbol,
                "allocation": allocation_percentage,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.log_error("force_trade", e)
            return {"success": False, "error": str(e)}
    
    def get_performance_report(self) -> str:
        """Generate a comprehensive performance report."""
        return self.performance_tracker.generate_performance_report() 