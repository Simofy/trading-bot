"""Performance tracking and analytics for the trading bot."""

import json
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass, asdict

from .logger import TradingLogger
from .database import TradingDatabase


@dataclass
class Trade:
    """Represents a completed trade."""
    timestamp: datetime
    symbol: str
    action: str  # BUY, SELL, CLOSE
    quantity: float
    price: float
    amount: float
    fees: float = 0.0
    order_id: str = ""
    success: bool = True


@dataclass
class PortfolioSnapshot:
    """Represents portfolio state at a point in time."""
    timestamp: datetime
    total_value: float
    available_balance: float
    positions: Dict[str, float]  # symbol -> value
    unrealized_pnl: float = 0.0


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    total_return: float
    total_return_pct: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    time_in_market: float
    calmar_ratio: float
    sortino_ratio: float


class PerformanceTracker:
    """Tracks and analyzes trading performance with advanced metrics."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.logger = TradingLogger(__name__)
        
        # Core data
        self.initial_balance = initial_balance
        self.trades: List[Trade] = []
        self.portfolio_snapshots: List[PortfolioSnapshot] = []
        self.daily_returns: List[float] = []
        
        # Performance tracking
        self.peak_portfolio_value = initial_balance
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Risk-free rate (annualized) - US 10-year treasury approximation
        self.risk_free_rate = 0.04  # 4%
        
        # Database integration
        self.db = TradingDatabase()
        
        # Load historical data if available
        self._load_historical_data()
    
    def record_trade(self, trade: Trade):
        """Record a new trade and update metrics."""
        self.trades.append(trade)
        
        # Save to database
        trade_data = {
            'timestamp': trade.timestamp.isoformat(),
            'symbol': trade.symbol,
            'action': trade.action,
            'quantity': trade.quantity,
            'price': trade.price,
            'amount': trade.amount,
            'fees': trade.fees,
            'order_id': trade.order_id,
            'success': trade.success
        }
        self.db.insert_trade(trade_data)
        
        # Also save to JSON for backward compatibility
        self._save_trade(trade)
        
        self.logger.logger.info(
            f"Trade recorded: {trade.action} {trade.symbol} "
            f"${trade.amount:.2f} @ ${trade.price:.4f}"
        )
    
    def record_portfolio_snapshot(self, snapshot: PortfolioSnapshot):
        """Record portfolio state and calculate returns."""
        self.portfolio_snapshots.append(snapshot)
        
        # Calculate daily return if we have previous snapshot
        if len(self.portfolio_snapshots) > 1:
            prev_value = self.portfolio_snapshots[-2].total_value
            current_value = snapshot.total_value
            
            if prev_value > 0:
                daily_return = (current_value - prev_value) / prev_value
                self.daily_returns.append(daily_return)
        
        # Update drawdown tracking
        self._update_drawdown(snapshot.total_value)
        
        # Save to database
        snapshot_data = {
            'timestamp': snapshot.timestamp.isoformat(),
            'total_value': snapshot.total_value,
            'available_balance': snapshot.available_balance,
            'positions': snapshot.positions,
            'unrealized_pnl': snapshot.unrealized_pnl
        }
        self.db.insert_portfolio_snapshot(snapshot_data)
        
        # Also save to JSON for backward compatibility
        self._save_snapshot(snapshot)
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        if not self.portfolio_snapshots:
            return self._get_empty_metrics()
        
        current_value = self.portfolio_snapshots[-1].total_value
        
        # Basic returns
        total_return = current_value - self.initial_balance
        total_return_pct = total_return / self.initial_balance
        
        # Time period analysis
        start_date = self.portfolio_snapshots[0].timestamp
        end_date = self.portfolio_snapshots[-1].timestamp
        days_elapsed = (end_date - start_date).days
        years_elapsed = days_elapsed / 365.25 if days_elapsed > 0 else 1
        
        # Annualized return
        if years_elapsed > 0 and current_value > 0:
            annualized_return = (current_value / self.initial_balance) ** (1 / years_elapsed) - 1
        else:
            annualized_return = 0.0
        
        # Volatility and risk metrics
        volatility = self._calculate_volatility()
        sharpe_ratio = self._calculate_sharpe_ratio(annualized_return, volatility)
        sortino_ratio = self._calculate_sortino_ratio(annualized_return)
        calmar_ratio = self._calculate_calmar_ratio(annualized_return)
        
        # Trade statistics
        trade_stats = self._calculate_trade_statistics()
        
        return PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=self.max_drawdown,
            max_drawdown_pct=self.max_drawdown / self.peak_portfolio_value if self.peak_portfolio_value > 0 else 0,
            time_in_market=self._calculate_time_in_market(),
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            **trade_stats
        )
    
    def _calculate_volatility(self) -> float:
        """Calculate annualized volatility."""
        if len(self.daily_returns) < 2:
            return 0.0
        
        # Standard deviation of daily returns
        daily_vol = statistics.stdev(self.daily_returns)
        
        # Annualize (assuming 252 trading days per year)
        return daily_vol * math.sqrt(252)
    
    def _calculate_sharpe_ratio(self, annual_return: float, volatility: float) -> float:
        """Calculate Sharpe ratio."""
        if volatility == 0:
            return 0.0
        
        excess_return = annual_return - self.risk_free_rate
        return excess_return / volatility
    
    def _calculate_sortino_ratio(self, annual_return: float) -> float:
        """Calculate Sortino ratio (uses downside deviation)."""
        if not self.daily_returns:
            return 0.0
        
        # Calculate downside deviation
        negative_returns = [r for r in self.daily_returns if r < 0]
        
        if not negative_returns:
            return float('inf') if annual_return > self.risk_free_rate else 0.0
        
        downside_deviation = statistics.stdev(negative_returns) * math.sqrt(252)
        
        if downside_deviation == 0:
            return 0.0
        
        excess_return = annual_return - self.risk_free_rate
        return excess_return / downside_deviation
    
    def _calculate_calmar_ratio(self, annual_return: float) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)."""
        if self.max_drawdown == 0:
            return 0.0
        
        max_dd_pct = self.max_drawdown / self.peak_portfolio_value
        return annual_return / max_dd_pct if max_dd_pct > 0 else 0.0
    
    def _calculate_trade_statistics(self) -> Dict:
        """Calculate detailed trade statistics."""
        if not self.trades:
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0
            }
        
        # Calculate P&L for each trade (simplified - would need entry/exit tracking for accuracy)
        winning_trades = []
        losing_trades = []
        
        # Group trades by symbol to calculate P&L
        position_tracker = {}
        
        for trade in self.trades:
            symbol = trade.symbol
            
            if symbol not in position_tracker:
                position_tracker[symbol] = []
            
            position_tracker[symbol].append(trade)
        
        # Calculate P&L for completed round trips
        for symbol, symbol_trades in position_tracker.items():
            buys = [t for t in symbol_trades if t.action == "BUY"]
            sells = [t for t in symbol_trades if t.action in ["SELL", "CLOSE"]]
            
            # Simple FIFO matching
            for sell in sells:
                for buy in buys:
                    if buy.quantity > 0:
                        trade_qty = min(buy.quantity, sell.quantity)
                        pnl = (sell.price - buy.price) * trade_qty - sell.fees - buy.fees
                        
                        if pnl > 0:
                            winning_trades.append(pnl)
                        else:
                            losing_trades.append(abs(pnl))
                        
                        buy.quantity -= trade_qty
                        sell.quantity -= trade_qty
                        
                        if sell.quantity <= 0:
                            break
        
        # Calculate statistics
        total_trades = len(winning_trades) + len(losing_trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        
        win_rate = winning_count / total_trades if total_trades > 0 else 0.0
        
        avg_win = statistics.mean(winning_trades) if winning_trades else 0.0
        avg_loss = statistics.mean(losing_trades) if losing_trades else 0.0
        
        largest_win = max(winning_trades) if winning_trades else 0.0
        largest_loss = max(losing_trades) if losing_trades else 0.0
        
        total_profit = sum(winning_trades)
        total_loss = sum(losing_trades)
        profit_factor = total_profit / total_loss if total_loss > 0 else 0.0
        
        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": total_trades,
            "winning_trades": winning_count,
            "losing_trades": losing_count,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss
        }
    
    def _calculate_time_in_market(self) -> float:
        """Calculate percentage of time with open positions."""
        if not self.portfolio_snapshots:
            return 0.0
        
        time_with_positions = 0
        total_time = 0
        
        for i in range(1, len(self.portfolio_snapshots)):
            prev_snapshot = self.portfolio_snapshots[i-1]
            curr_snapshot = self.portfolio_snapshots[i]
            
            time_diff = (curr_snapshot.timestamp - prev_snapshot.timestamp).total_seconds()
            total_time += time_diff
            
            if prev_snapshot.positions:
                time_with_positions += time_diff
        
        return time_with_positions / total_time if total_time > 0 else 0.0
    
    def _update_drawdown(self, current_value: float):
        """Update drawdown calculations."""
        if current_value > self.peak_portfolio_value:
            self.peak_portfolio_value = current_value
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = self.peak_portfolio_value - current_value
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
    
    def _get_empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics when no data available."""
        return PerformanceMetrics(
            total_return=0.0,
            total_return_pct=0.0,
            annualized_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win=0.0,
            avg_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            time_in_market=0.0,
            calmar_ratio=0.0,
            sortino_ratio=0.0
        )
    
    def _save_trade(self, trade: Trade):
        """Save trade to persistent storage."""
        try:
            # Convert to dictionary for JSON serialization
            trade_dict = {
                "timestamp": trade.timestamp.isoformat(),
                "symbol": trade.symbol,
                "action": trade.action,
                "quantity": trade.quantity,
                "price": trade.price,
                "amount": trade.amount,
                "fees": trade.fees,
                "order_id": trade.order_id,
                "success": trade.success
            }
            
            # Append to trades file
            with open("logs/performance_trades.json", "a") as f:
                f.write(json.dumps(trade_dict) + "\n")
                
        except Exception as e:
            self.logger.log_error("_save_trade", e)
    
    def _save_snapshot(self, snapshot: PortfolioSnapshot):
        """Save portfolio snapshot to persistent storage."""
        try:
            snapshot_dict = {
                "timestamp": snapshot.timestamp.isoformat(),
                "total_value": snapshot.total_value,
                "available_balance": snapshot.available_balance,
                "positions": snapshot.positions,
                "unrealized_pnl": snapshot.unrealized_pnl
            }
            
            with open("logs/performance_snapshots.json", "a") as f:
                f.write(json.dumps(snapshot_dict) + "\n")
                
        except Exception as e:
            self.logger.log_error("_save_snapshot", e)
    
    def _load_historical_data(self):
        """Load historical performance data."""
        try:
            # Load trades
            try:
                with open("logs/performance_trades.json", "r") as f:
                    for line in f:
                        trade_dict = json.loads(line.strip())
                        trade = Trade(
                            timestamp=datetime.fromisoformat(trade_dict["timestamp"]),
                            symbol=trade_dict["symbol"],
                            action=trade_dict["action"],
                            quantity=trade_dict["quantity"],
                            price=trade_dict["price"],
                            amount=trade_dict["amount"],
                            fees=trade_dict.get("fees", 0.0),
                            order_id=trade_dict.get("order_id", ""),
                            success=trade_dict.get("success", True)
                        )
                        self.trades.append(trade)
            except FileNotFoundError:
                pass  # No historical trades yet
            
            # Load snapshots
            try:
                with open("logs/performance_snapshots.json", "r") as f:
                    for line in f:
                        snapshot_dict = json.loads(line.strip())
                        snapshot = PortfolioSnapshot(
                            timestamp=datetime.fromisoformat(snapshot_dict["timestamp"]),
                            total_value=snapshot_dict["total_value"],
                            available_balance=snapshot_dict["available_balance"],
                            positions=snapshot_dict["positions"],
                            unrealized_pnl=snapshot_dict.get("unrealized_pnl", 0.0)
                        )
                        self.portfolio_snapshots.append(snapshot)
            except FileNotFoundError:
                pass  # No historical snapshots yet
            
            # Recalculate metrics from loaded data
            self._recalculate_from_snapshots()
            
        except Exception as e:
            self.logger.log_error("_load_historical_data", e)
    
    def _recalculate_from_snapshots(self):
        """Recalculate metrics from loaded portfolio snapshots."""
        if len(self.portfolio_snapshots) < 2:
            return
        
        # Recalculate daily returns
        self.daily_returns = []
        for i in range(1, len(self.portfolio_snapshots)):
            prev_value = self.portfolio_snapshots[i-1].total_value
            curr_value = self.portfolio_snapshots[i].total_value
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                self.daily_returns.append(daily_return)
        
        # Recalculate drawdown metrics
        self.max_drawdown = 0.0
        self.peak_portfolio_value = self.initial_balance
        
        for snapshot in self.portfolio_snapshots:
            self._update_drawdown(snapshot.total_value)
    
    def generate_performance_report(self) -> str:
        """Generate a comprehensive performance report."""
        metrics = self.get_performance_metrics()
        
        report = f"""
📊 TRADING PERFORMANCE REPORT
{'=' * 50}

💰 RETURNS
Total Return: ${metrics.total_return:,.2f} ({metrics.total_return_pct:.2%})
Annualized Return: {metrics.annualized_return:.2%}
Initial Balance: ${self.initial_balance:,.2f}
Current Value: ${self.initial_balance + metrics.total_return:,.2f}

📈 RISK METRICS  
Volatility (Annual): {metrics.volatility:.2%}
Sharpe Ratio: {metrics.sharpe_ratio:.2f}
Sortino Ratio: {metrics.sortino_ratio:.2f}
Calmar Ratio: {metrics.calmar_ratio:.2f}
Max Drawdown: ${metrics.max_drawdown:,.2f} ({metrics.max_drawdown_pct:.2%})

📋 TRADING STATISTICS
Total Trades: {metrics.total_trades}
Win Rate: {metrics.win_rate:.1%}
Profit Factor: {metrics.profit_factor:.2f}
Winning Trades: {metrics.winning_trades}
Losing Trades: {metrics.losing_trades}
Average Win: ${metrics.avg_win:.2f}
Average Loss: ${metrics.avg_loss:.2f}
Largest Win: ${metrics.largest_win:.2f}
Largest Loss: ${metrics.largest_loss:.2f}

⏱️ MARKET EXPOSURE
Time in Market: {metrics.time_in_market:.1%}

📅 PERIOD
Data Points: {len(self.portfolio_snapshots)}
Daily Returns: {len(self.daily_returns)}
"""
        return report 