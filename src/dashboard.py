"""Real-time monitoring dashboard for the trading bot."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import Config
from .logger import TradingLogger
from .market_data import MarketDataProvider
from .performance_tracker import PerformanceTracker


class TradingDashboard:
    """Real-time dashboard for monitoring trading bot performance - works independently."""
    
    def __init__(self, bot: 'TradingBot' = None):
        self.app = FastAPI(title="AI Trading Bot Dashboard", version="1.0.0")
        self.logger = TradingLogger(__name__)
        self.config = Config()
        
        # Independent components (don't require bot instance)
        self.market_data = MarketDataProvider(config=self.config)
        self.performance_tracker = PerformanceTracker(initial_balance=float(self.config.demo_initial_balance), exchange=bot.exchange if bot else None)
        
        # Optional bot instance for advanced features
        self.bot = bot
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def dashboard_home():
            """Serve the main dashboard HTML."""
            return HTMLResponse(self._generate_dashboard_html())
        
        @self.app.get("/api/status")
        async def get_bot_status():
            """Get current bot status from exchange/live data."""
            try:
                # Initialize default values
                portfolio_value = self.performance_tracker.initial_balance
                last_activity = "No recent activity"
                system_status = "offline"
                
                # Check for recent AI decisions as activity indicator
                ai_decision_time = None
                try:
                    with open('logs/ai_decisions.json', 'r') as f:
                        lines = f.readlines()
                        if lines:
                            # Get the most recent decision
                            last_decision = json.loads(lines[-1].strip())
                            ai_decision_time = datetime.fromisoformat(last_decision['timestamp'])
                            
                            # Consider system active if AI decision was made within last 2 hours
                            if (datetime.now() - ai_decision_time).total_seconds() < 7200:
                                system_status = "monitoring"
                                last_activity = f"AI decision at {last_decision['timestamp'][:19]}"
                            else:
                                last_activity = f"Last AI decision: {last_decision['timestamp'][:19]}"
                except FileNotFoundError:
                    pass
                
                # Try to get live data if bot is connected
                if self.bot and hasattr(self.bot, 'exchange'):
                    try:
                        portfolio_data = await self.bot.exchange.get_portfolio_value()
                        portfolio_value = portfolio_data.get('total_value', portfolio_value)
                        
                        # Check for recent trades
                        recent_trades = await self.bot.exchange.get_historical_trades(limit=1)
                        if recent_trades:
                            last_trade_time = datetime.fromisoformat(recent_trades[0].get('timestamp', datetime.now().isoformat()))
                            if (datetime.now() - last_trade_time).total_seconds() < 3600:  # Within 1 hour
                                last_activity = f"Recent trade: {recent_trades[0]['timestamp'][:19]}"
                                system_status = "active"
                        
                        # Check if bot is actually running
                        if hasattr(self.bot, 'is_running') and self.bot.is_running:
                            system_status = "running"
                            
                    except Exception as e:
                        self.logger.logger.warning(f"Could not get live portfolio data: {e}")
                
                # Use performance tracker data if available (but don't override newer AI decisions)
                if self.performance_tracker.portfolio_snapshots:
                    latest_snapshot = self.performance_tracker.portfolio_snapshots[-1]
                    portfolio_value = latest_snapshot.total_value
                    snapshot_time = latest_snapshot.timestamp
                    
                    # Only use portfolio update as activity if it's more recent than AI decision
                    use_portfolio_activity = False
                    if (datetime.now() - snapshot_time).total_seconds() < 1800:  # Within 30 minutes
                        if ai_decision_time is None or snapshot_time > ai_decision_time:
                            last_activity = f"Portfolio update: {snapshot_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            use_portfolio_activity = True
                        
                        if system_status == "offline":
                            system_status = "monitoring"
                
                # Determine final running status
                is_running = system_status in ["running", "active"]
                
                status = {
                    "is_running": is_running,
                    "system_status": system_status,
                    "last_activity": last_activity,
                    "mode": "testnet" if self.config.use_sandbox else "live",
                    "portfolio_value": portfolio_value,
                    "data_source": "binance_api" if self.bot else "monitoring"
                }
                
                return {"success": True, "data": status}
                
            except Exception as e:
                self.logger.log_error("get_bot_status", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/portfolio")
        async def get_portfolio():
            """Get current portfolio from Binance API and performance tracker."""
            try:
                portfolio_data = {
                    "timestamp": datetime.now().isoformat(),
                    "total_value": self.performance_tracker.initial_balance,
                    "available_balance": self.performance_tracker.initial_balance,
                    "positions": {},
                    "unrealized_pnl": 0.0
                }
                
                # Try to get live portfolio data from exchange
                if self.bot and hasattr(self.bot, 'exchange'):
                    try:
                        live_portfolio = await self.bot.exchange.get_portfolio_value()
                        portfolio_data.update({
                            "total_value": live_portfolio.get('total_value', self.performance_tracker.initial_balance),
                            "available_balance": live_portfolio.get('available_balance', self.performance_tracker.initial_balance),
                            "positions": live_portfolio.get('positions', {}),
                            "unrealized_pnl": live_portfolio.get('total_value', self.performance_tracker.initial_balance) - self.performance_tracker.initial_balance
                        })
                    except Exception as e:
                        self.logger.logger.warning(f"Could not get live portfolio: {e}")
                
                # Use performance tracker snapshots if available
                if self.performance_tracker.portfolio_snapshots:
                    latest_snapshot = self.performance_tracker.portfolio_snapshots[-1]
                    portfolio_data.update({
                        "timestamp": latest_snapshot.timestamp.isoformat(),
                        "total_value": latest_snapshot.total_value,
                        "available_balance": latest_snapshot.available_balance,
                        "positions": latest_snapshot.positions,
                        "unrealized_pnl": latest_snapshot.unrealized_pnl
                    })
                
                # Fallback to JSON file if no other data available
                if portfolio_data["total_value"] == self.performance_tracker.initial_balance and not portfolio_data["positions"]:
                    try:
                        with open('logs/performance_snapshots.json', 'r') as f:
                            lines = f.readlines()
                            if lines:
                                latest = json.loads(lines[-1])
                                portfolio_data.update(latest)
                    except FileNotFoundError:
                        pass  # Use default values
                
                return {"success": True, "data": portfolio_data}
                
            except Exception as e:
                self.logger.log_error("get_portfolio", e)
                return {"success": False, "error": str(e)}

        @self.app.get("/api/trades")
        async def get_trades(limit: int = 20):
            """Get trade history from Binance API."""
            try:
                if self.bot and hasattr(self.bot, 'exchange'):
                    trades = await self.bot.exchange.get_historical_trades(limit=limit)
                else:
                    # Fallback to performance tracker trades
                    trades = [
                        {
                            'symbol': trade.symbol,
                            'action': trade.action,
                            'quantity': trade.quantity,
                            'price': trade.price,
                            'amount': trade.amount,
                            'fees': trade.fees,
                            'timestamp': trade.timestamp.isoformat(),
                            'success': trade.success
                        }
                        for trade in self.performance_tracker.trades[-limit:]
                    ]
                
                return {"success": True, "data": trades}
            except Exception as e:
                self.logger.log_error("get_trades", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/performance")
        async def get_performance():
            """Get performance metrics from Binance API and performance tracker."""
            try:
                # Get performance metrics using performance tracker with Binance data
                metrics = self.performance_tracker.get_performance_metrics()
                
                # Get additional stats from Binance API if available
                api_stats = {}
                if self.bot and hasattr(self.bot, 'exchange'):
                    try:
                        # Get 24hr ticker stats for additional context
                        ticker_stats = await self.bot.exchange.get_24hr_ticker_stats()
                        api_stats = {
                            "market_data": ticker_stats,
                            "data_source": "binance_api"
                        }
                    except Exception as e:
                        self.logger.logger.warning(f"Could not get market stats: {e}")
                
                performance_data = {
                    "metrics": {
                        "total_return": metrics.total_return,
                        "total_return_pct": metrics.total_return_pct,
                        "annualized_return": metrics.annualized_return,
                        "sharpe_ratio": metrics.sharpe_ratio,
                        "sortino_ratio": metrics.sortino_ratio,
                        "calmar_ratio": metrics.calmar_ratio,
                        "max_drawdown": metrics.max_drawdown,
                        "max_drawdown_pct": metrics.max_drawdown_pct,
                        "win_rate": metrics.win_rate,
                        "total_trades": metrics.total_trades,
                        "volatility": metrics.volatility,
                        "profit_factor": metrics.profit_factor
                    },
                    "api_stats": api_stats,
                    "report": self.performance_tracker.generate_performance_report()
                }
                
                return {"success": True, "data": performance_data}
                
            except Exception as e:
                self.logger.log_error("get_performance", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/ai-decisions")
        async def get_ai_decisions(limit: int = 20):
            """Get recent AI decisions from stored file."""
            try:
                decisions = []
                
                # First, try to load from AI decisions file
                try:
                    with open('logs/ai_decisions.json', 'r') as f:
                        lines = f.readlines()
                        for line in lines[-limit:]:  # Get last N decisions
                            if line.strip():
                                decision_data = json.loads(line.strip())
                                decision = decision_data.get('decision', {})
                                
                                decisions.append({
                                    "action": decision.get('action', 'HOLD'),
                                    "symbol": decision.get('symbol', 'N/A'),
                                    "confidence": decision.get('confidence', 0),
                                    "timestamp": decision_data.get('timestamp', datetime.now().isoformat()),
                                    "reasoning": decision.get('reasoning', 'No reasoning provided')[:200] + "..." if len(decision.get('reasoning', '')) > 200 else decision.get('reasoning', 'No reasoning provided'),
                                    "allocation_percentage": decision.get('allocation_percentage', 0),
                                    "source": "ai_gpt4"
                                })
                                
                except FileNotFoundError:
                    # If no AI decisions file exists, fall back to other data sources
                    pass
                
                # If we don't have AI decisions, try to get recent market insights
                if not decisions:
                    if self.bot and hasattr(self.bot, 'exchange'):
                        # Get recent trades as backup
                        recent_trades = await self.bot.exchange.get_historical_trades(limit=min(limit, 5))
                        
                        for trade in recent_trades[-limit:]:
                            decisions.append({
                                "action": "BUY" if trade.get('isBuyer', True) else "SELL",
                                "symbol": trade.get('symbol', ''),
                                "confidence": 8,
                                "timestamp": trade.get('timestamp', datetime.now().isoformat()),
                                "reasoning": f"Market trade executed at ${trade.get('price', 0):.4f}",
                                "allocation_percentage": 0,
                                "source": "binance_trades"
                            })
                        
                        # Add market insights if still no trades
                        if not decisions:
                            try:
                                stats = await self.bot.exchange.get_24hr_ticker_stats()
                                for symbol, data in list(stats.items())[:min(limit, 5)]:
                                    change_pct = data.get('priceChangePercent', 0)
                                    action = "BUY" if change_pct > 0 else "SELL" if change_pct < -2 else "HOLD"
                                    
                                    decisions.append({
                                        "action": action,
                                        "symbol": symbol,
                                        "confidence": min(9, max(1, int(5 + abs(change_pct) / 2))),
                                        "timestamp": datetime.now().isoformat(),
                                        "reasoning": f"24h change: {change_pct:.2f}%",
                                        "allocation_percentage": 0,
                                        "source": "market_analysis"
                                    })
                            except Exception:
                                pass
                    else:
                        # Final fallback to performance tracker trades
                        for trade in self.performance_tracker.trades[-limit:]:
                            decisions.append({
                                "action": trade.action,
                                "symbol": trade.symbol,
                                "confidence": 7,
                                "timestamp": trade.timestamp.isoformat(),
                                "reasoning": f"Trade executed at ${trade.price:.4f}",
                                "allocation_percentage": 0,
                                "source": "performance_tracker"
                            })
                
                return {"success": True, "data": decisions}
                
            except Exception as e:
                self.logger.log_error("get_ai_decisions", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/market-analysis")
        async def get_market_analysis(symbol: str = "BTCUSDT"):
            """Get market analysis data from Binance API."""
            try:
                if self.bot and hasattr(self.bot, 'exchange'):
                    # Get kline data for technical analysis
                    klines = await self.bot.exchange.get_klines(symbol=symbol, interval="1h", limit=100)
                    ticker_stats = await self.bot.exchange.get_24hr_ticker_stats(symbol=symbol)
                    
                    analysis = {
                        "symbol": symbol,
                        "price_data": klines[-50:] if klines else [],  # Last 50 hours
                        "ticker_stats": ticker_stats,
                        "data_source": "binance_api"
                    }
                else:
                    analysis = {"error": "No live bot connection available"}
                
                return {"success": True, "data": analysis}
            except Exception as e:
                self.logger.log_error("get_market_analysis", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/portfolio-history")
        async def get_portfolio_history(days: int = 7):
            """Get portfolio value history from performance tracker and Binance API."""
            try:
                history = []
                
                # Get from performance tracker snapshots
                snapshots = self.performance_tracker.portfolio_snapshots
                
                if snapshots:
                    # Use existing snapshots
                    for snapshot in snapshots[-days*24:]:  # Last N days worth
                        history.append({
                            "timestamp": snapshot.timestamp.isoformat(),
                            "value": snapshot.total_value
                        })
                else:
                    # If no snapshots, try to get current portfolio value from exchange
                    if self.bot and hasattr(self.bot, 'exchange'):
                        try:
                            portfolio_data = await self.bot.exchange.get_portfolio_value()
                            current_value = portfolio_data.get('total_value', self.performance_tracker.initial_balance)
                            
                            # Create a single current data point
                            history.append({
                                "timestamp": datetime.now().isoformat(),
                                "value": current_value
                            })
                        except Exception as e:
                            self.logger.logger.warning(f"Could not get current portfolio value: {e}")
                            # Fallback to initial balance
                            history.append({
                                "timestamp": datetime.now().isoformat(),
                                "value": self.performance_tracker.initial_balance
                            })
                    
                    # Also try to load from JSON file as backup
                    if not history:
                        try:
                            with open('logs/performance_snapshots.json', 'r') as f:
                                for line in f:
                                    if line.strip():
                                        snapshot_data = json.loads(line.strip())
                                        history.append({
                                            "timestamp": snapshot_data['timestamp'],
                                            "value": snapshot_data.get('total_value', 0)
                                        })
                        except FileNotFoundError:
                            pass
                
                return {"success": True, "data": history[-days*24:] if history else []}
                
            except Exception as e:
                self.logger.log_error("get_portfolio_history", e)
                return {"success": False, "error": str(e)}
        
        @self.app.post("/api/manual-trade")
        async def manual_trade(trade_data: dict):
            """Execute manual trade - requires live bot or queues for bot."""
            try:
                action = trade_data.get("action")
                symbol = trade_data.get("symbol")
                allocation = trade_data.get("allocation", 10.0)
                
                if self.bot:
                    # Live bot available - execute immediately
                    result = await self.bot.force_trade(action, symbol, allocation)
                    return {"success": True, "data": result}
                else:
                    # No live bot - save manual trade request to database for bot to pick up
                    manual_trade_request = {
                        'timestamp': datetime.now().isoformat(),
                        'action': action,
                        'symbol': symbol,
                        'allocation': allocation,
                        'status': 'pending',
                        'source': 'dashboard'
                    }
                    
                    # Save to a manual trades table/file
                    try:
                        with open('logs/manual_trades_queue.json', 'a') as f:
                            f.write(json.dumps(manual_trade_request) + '\n')
                    except Exception:
                        pass
                    
                    return {
                        "success": True, 
                        "data": {
                            "message": "Trade request queued. Will execute when bot is running.",
                            "request": manual_trade_request
                        }
                    }
                    
            except Exception as e:
                self.logger.log_error("manual_trade", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/market-data")
        async def get_market_data():
            """Get current market data independently."""
            try:
                # Get market data independently
                symbols = self.config.supported_symbols
                market_data = await self.market_data.get_current_prices(symbols)
                
                # Add any technical analysis if available
                enhanced_data = {}
                for symbol, data in market_data.items():
                    enhanced_data[symbol] = {
                        **data,
                        "technical_indicators": self._get_technical_indicators(symbol) if self.bot else None
                    }
                
                return {"success": True, "data": enhanced_data}
                
            except Exception as e:
                self.logger.log_error("get_market_data", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/technical-analysis/{symbol}")
        async def get_technical_analysis(symbol: str):
            """Get technical analysis for a symbol."""
            try:
                if self.bot and hasattr(self.bot, 'ai_advisor') and hasattr(self.bot.ai_advisor, 'technical_analyzer'):
                    indicators = self.bot.ai_advisor.technical_analyzer.get_technical_indicators(symbol)
                    signals = self.bot.ai_advisor.technical_analyzer.generate_trading_signals(symbol)
                    return {"success": True, "data": {"indicators": indicators, "signals": signals}}
                else:
                    return {"success": False, "error": "Technical analysis not available (requires live bot)"}
            except Exception as e:
                self.logger.log_error("get_technical_analysis", e)
                return {"success": False, "error": str(e)}
    
    def _get_technical_indicators(self, symbol: str) -> Optional[Dict]:
        """Get technical indicators if available."""
        try:
            if self.bot and hasattr(self.bot, 'ai_advisor') and hasattr(self.bot.ai_advisor, 'technical_analyzer'):
                return self.bot.ai_advisor.technical_analyzer.get_technical_indicators(symbol)
        except Exception:
            pass
        return None
    
    def _generate_dashboard_html(self) -> str:
        """Generate the dashboard HTML interface."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Trading Bot Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    color: #fff;
                    min-height: 100vh;
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                
                h1 {
                    font-size: 2.5em;
                    margin-bottom: 10px;
                    background: linear-gradient(45deg, #fff, #a0d2ff);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                
                .dashboard-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                }
                
                .card {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 20px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }
                
                .card h3 {
                    margin-bottom: 15px;
                    color: #a0d2ff;
                    border-bottom: 2px solid #a0d2ff;
                    padding-bottom: 5px;
                }
                
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                
                .status-online { background-color: #4CAF50; }
                .status-offline { background-color: #f44336; }
                .status-warning { background-color: #ff9800; }
                
                .metric {
                    display: flex;
                    justify-content: space-between;
                    margin: 10px 0;
                    padding: 5px 0;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .metric-label {
                    font-weight: 500;
                }
                
                .metric-value {
                    font-weight: bold;
                    color: #a0d2ff;
                }
                
                .positive { color: #4CAF50 !important; }
                .negative { color: #f44336 !important; }
                
                button {
                    background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: bold;
                    margin: 5px;
                    transition: transform 0.2s;
                }
                
                button:hover {
                    transform: translateY(-2px);
                }
                
                .refresh-btn {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
                    border-radius: 50%;
                    width: 60px;
                    height: 60px;
                    font-size: 18px;
                }
                
                .chart-container {
                    height: 300px;
                    margin-top: 15px;
                }
                
                .trade-list {
                    max-height: 300px;
                    overflow-y: auto;
                }
                
                .trade-item {
                    background: rgba(255, 255, 255, 0.05);
                    margin: 5px 0;
                    padding: 10px;
                    border-radius: 8px;
                    font-size: 0.9em;
                }
                
                .buy { border-left: 4px solid #4CAF50; }
                .sell { border-left: 4px solid #f44336; }
                
                .loading {
                    text-align: center;
                    opacity: 0.7;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>🤖 AI Trading Bot Dashboard</h1>
                    <p>Real-time monitoring and analytics</p>
                </header>
                
                <div class="dashboard-grid">
                    <!-- Bot Status Card -->
                    <div class="card">
                        <h3>🟢 Bot Status</h3>
                        <div id="bot-status" class="loading">Loading...</div>
                    </div>
                    
                    <!-- Portfolio Overview -->
                    <div class="card">
                        <h3>💰 Portfolio Overview</h3>
                        <div id="portfolio-overview" class="loading">Loading...</div>
                    </div>
                    
                    <!-- Performance Metrics -->
                    <div class="card">
                        <h3>📈 Performance Metrics</h3>
                        <div id="performance-metrics" class="loading">Loading...</div>
                    </div>
                    
                    <!-- Portfolio Chart -->
                    <div class="card" style="grid-column: span 2;">
                        <h3>📊 Portfolio Value History</h3>
                        <div class="chart-container">
                            <canvas id="portfolioChart"></canvas>
                        </div>
                    </div>
                    
                    <!-- Recent Trades -->
                    <div class="card">
                        <h3>🔄 Recent Trades</h3>
                        <div id="recent-trades" class="trade-list loading">Loading...</div>
                    </div>
                    
                    <!-- AI Decisions -->
                    <div class="card">
                        <h3>🧠 AI Decisions</h3>
                        <div id="ai-decisions" class="trade-list loading">Loading...</div>
                    </div>
                    
                    <!-- Market Data -->
                    <div class="card">
                        <h3>📊 Market Data</h3>
                        <div id="market-data" class="loading">Loading...</div>
                    </div>
                <button class="refresh-btn" onclick="refreshAll()" title="Refresh All Data">
                    🔄
                </button>
            </div>
            
            <script>
                let portfolioChart;
                
                // Initialize dashboard
                document.addEventListener('DOMContentLoaded', function() {
                    initPortfolioChart();
                    refreshAll();
                    
                    // Auto-refresh every 30 seconds
                    setInterval(refreshAll, 30000);
                });
                
                async function fetchData(endpoint) {
                    try {
                        const response = await fetch(`/api/${endpoint}`);
                        const data = await response.json();
                        return data.success ? data.data : null;
                    } catch (error) {
                        console.error(`Error fetching ${endpoint}:`, error);
                        return null;
                    }
                }
                
                async function refreshAll() {
                    await Promise.all([
                        updateBotStatus(),
                        updatePortfolio(),
                        updatePerformance(),
                        updateTrades(),
                        updateAIDecisions(),
                        updateMarketData(),
                        updatePortfolioChart()
                    ]);
                }
                
                async function updateBotStatus() {
                    const status = await fetchData('status');
                    const element = document.getElementById('bot-status');
                    
                    if (status) {
                        const isRunning = status.is_running;
                        const statusClass = isRunning ? 'status-online' : 'status-offline';
                        const statusText = isRunning ? 'Online' : 'Offline';
                        
                        element.innerHTML = `
                            <div class="metric">
                                <span class="metric-label">Status</span>
                                <span class="metric-value">
                                    <span class="status-indicator ${statusClass}"></span>${statusText}
                                </span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Mode</span>
                                <span class="metric-value">${status.mode || 'Unknown'}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Last Activity</span>
                                <span class="metric-value">${status.last_activity ? new Date(status.last_activity).toLocaleTimeString() : 'Never'}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Total Decisions</span>
                                <span class="metric-value">${status.total_decisions || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Data Source</span>
                                <span class="metric-value">${status.data_source || 'Unknown'}</span>
                            </div>
                        `;
                    } else {
                        element.innerHTML = '<div class="metric"><span class="status-indicator status-offline"></span>Bot Offline - No Data</div>';
                    }
                }
                
                async function updatePortfolio() {
                    const portfolio = await fetchData('portfolio');
                    const element = document.getElementById('portfolio-overview');
                    
                    if (portfolio) {
                        element.innerHTML = `
                            <div class="metric">
                                <span class="metric-label">Total Value</span>
                                <span class="metric-value">$${portfolio.total_value.toFixed(2)}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Available Balance</span>
                                <span class="metric-value">$${portfolio.available_balance.toFixed(2)}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Unrealized P&L</span>
                                <span class="metric-value ${portfolio.unrealized_pnl >= 0 ? 'positive' : 'negative'}">
                                    $${portfolio.unrealized_pnl.toFixed(2)}
                                </span>
                            </div>
                        `;
                    } else {
                        element.innerHTML = '<div class="loading">No portfolio data</div>';
                    }
                }
                
                async function updatePerformance() {
                    const performance = await fetchData('performance');
                    const element = document.getElementById('performance-metrics');
                    
                    if (performance && performance.metrics) {
                        const metrics = performance.metrics;
                        element.innerHTML = `
                            <div class="metric">
                                <span class="metric-label">Total Return</span>
                                <span class="metric-value ${metrics.total_return >= 0 ? 'positive' : 'negative'}">
                                    ${(metrics.total_return_pct * 100).toFixed(2)}%
                                </span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Sharpe Ratio</span>
                                <span class="metric-value">${metrics.sharpe_ratio.toFixed(2)}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Win Rate</span>
                                <span class="metric-value">${(metrics.win_rate * 100).toFixed(1)}%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Total Trades</span>
                                <span class="metric-value">${metrics.total_trades}</span>
                            </div>
                        `;
                    } else {
                        element.innerHTML = '<div class="loading">No performance data</div>';
                    }
                }
                
                async function updateTrades() {
                    const trades = await fetchData('trades?limit=10');
                    const element = document.getElementById('recent-trades');
                    
                    if (trades && trades.length > 0) {
                        element.innerHTML = trades.map(trade => `
                            <div class="trade-item ${trade.action.toLowerCase()}">
                                <strong>${trade.action}</strong> ${trade.symbol}<br>
                                <small>
                                    ${new Date(trade.timestamp).toLocaleString()}<br>
                                    $${trade.amount.toFixed(2)} @ $${trade.price.toFixed(4)}
                                </small>
                            </div>
                        `).join('');
                    } else {
                        element.innerHTML = '<div class="loading">No recent trades</div>';
                    }
                }
                
                async function updateAIDecisions() {
                    const decisions = await fetchData('ai-decisions?limit=5');
                    const element = document.getElementById('ai-decisions');
                    
                    if (decisions && decisions.length > 0) {
                        element.innerHTML = decisions.map(decision => `
                            <div class="trade-item">
                                <strong>${decision.action}</strong> ${decision.symbol || 'N/A'}<br>
                                <small>
                                    Confidence: ${decision.confidence}/10<br>
                                    ${new Date(decision.timestamp).toLocaleString()}
                                </small>
                            </div>
                        `).join('');
                    } else {
                        element.innerHTML = '<div class="loading">No AI decisions</div>';
                    }
                }
                
                async function updateMarketData() {
                    const marketData = await fetchData('market-data');
                    const element = document.getElementById('market-data');
                    
                    if (marketData) {
                        element.innerHTML = Object.entries(marketData).map(([symbol, data]) => `
                            <div class="metric">
                                <span class="metric-label">${symbol}</span>
                                <span class="metric-value">
                                    $${data.price.toFixed(4)}
                                    <small class="${data.price_change_24h >= 0 ? 'positive' : 'negative'}">
                                        (${data.price_change_24h.toFixed(2)}%)
                                    </small>
                                </span>
                            </div>
                        `).join('');
                    } else {
                        element.innerHTML = '<div class="loading">No market data</div>';
                    }
                }
                
                function initPortfolioChart() {
                    const ctx = document.getElementById('portfolioChart').getContext('2d');
                    portfolioChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Portfolio Value',
                                data: [],
                                borderColor: '#a0d2ff',
                                backgroundColor: 'rgba(160, 210, 255, 0.1)',
                                fill: true,
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: false,
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                                    ticks: { color: '#fff' }
                                },
                                x: {
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                                    ticks: { color: '#fff' }
                                }
                            },
                            plugins: {
                                legend: { labels: { color: '#fff' } }
                            }
                        }
                    });
                }
                
                async function updatePortfolioChart() {
                    const history = await fetchData('portfolio-history?days=7');
                    
                    if (history && history.timestamps && history.values) {
                        portfolioChart.data.labels = history.timestamps.map(ts => 
                            new Date(ts).toLocaleDateString()
                        );
                        portfolioChart.data.datasets[0].data = history.values;
                        portfolioChart.update();
                    }
                }
                
                async function executeTrade(action) {
                    const symbol = document.getElementById('trade-symbol').value;
                    const amount = document.getElementById('trade-amount').value;
                    
                    try {
                        const response = await fetch('/api/manual-trade', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                action: action,
                                symbol: symbol,
                                allocation: parseFloat(amount)
                            })
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            alert(`Trade executed successfully: ${action} ${symbol}`);
                            setTimeout(refreshAll, 2000); // Refresh after 2 seconds
                        } else {
                            alert(`Trade failed: ${result.error}`);
                        }
                    } catch (error) {
                        alert(`Error executing trade: ${error.message}`);
                    }
                }
            </script>
        </body>
        </html>
        """
    
    async def start_server(self, host: str = "127.0.0.1", port: int = 8000):
        """Start the dashboard server."""
        self.logger.logger.info(f"Starting dashboard server on http://{host}:{port}")
        
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()


async def start_dashboard(bot: 'TradingBot' = None, host: str = "127.0.0.1", port: int = 8000):
    """Start the trading dashboard."""
    dashboard = TradingDashboard(bot)
    await dashboard.start_server(host, port)


# For standalone dashboard server
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Create a config and bot instance
        config = Config()
        bot = None # No longer need a bot instance for the dashboard to run independently
        
        # Start dashboard
        await start_dashboard(bot)
    
    asyncio.run(main()) 