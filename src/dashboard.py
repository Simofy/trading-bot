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

from .database import TradingDatabase
from .config import Config
from .logger import TradingLogger
from .market_data import MarketDataProvider
from .performance_tracker import PerformanceTracker


class TradingDashboard:
    """Real-time dashboard for monitoring trading bot performance - works independently."""
    
    def __init__(self, bot: 'TradingBot' = None):
        self.app = FastAPI(title="AI Trading Bot Dashboard", version="1.0.0")
        self.logger = TradingLogger(__name__)
        self.db = TradingDatabase()
        self.config = Config()
        
        # Independent components (don't require bot instance)
        self.market_data = MarketDataProvider(config=self.config)
        self.performance_tracker = PerformanceTracker(initial_balance=10000.0)
        
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
            """Get current bot status from database/files."""
            try:
                # Read status from database - check recent activity
                recent_trades = self.db.get_recent_trades(1) if hasattr(self.db, 'get_recent_trades') else []
                recent_decisions = self.db.get_ai_decisions(limit=1)
                
                # Check if bot is recently active (within last hour)
                is_active = False
                last_activity = None
                
                if recent_decisions:
                    last_decision_time = datetime.fromisoformat(recent_decisions[0]['timestamp'])
                    if (datetime.now() - last_decision_time).total_seconds() < 3600:  # 1 hour
                        is_active = True
                        last_activity = recent_decisions[0]['timestamp']
                
                # Get portfolio from database
                portfolio_snapshots = self.db.get_portfolio_snapshots(limit=1) if hasattr(self.db, 'get_portfolio_snapshots') else []
                
                status = {
                    "is_running": is_active,
                    "last_activity": last_activity or "No recent activity",
                    "mode": "testnet" if self.config.use_sandbox else "live",
                    "total_decisions": len(self.db.get_ai_decisions(limit=1000)) if hasattr(self.db, 'get_ai_decisions') else 0,
                    "portfolio_value": portfolio_snapshots[0]['total_value'] if portfolio_snapshots else 0,
                    "data_source": "database" if not self.bot else "live_bot"
                }
                
                return {"success": True, "data": status}
                
            except Exception as e:
                self.logger.log_error("get_bot_status", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/portfolio")
        async def get_portfolio():
            """Get current portfolio from database."""
            try:
                # Get latest portfolio snapshot from database
                snapshots = self.db.get_portfolio_snapshots(limit=1) if hasattr(self.db, 'get_portfolio_snapshots') else []
                
                if snapshots:
                    latest = snapshots[0]
                    portfolio_data = {
                        "timestamp": latest['timestamp'],
                        "total_value": latest['total_value'],
                        "available_balance": latest['available_balance'],
                        "positions": json.loads(latest['positions']) if isinstance(latest['positions'], str) else latest['positions'],
                        "unrealized_pnl": latest.get('unrealized_pnl', 0.0)
                    }
                else:
                    # Fallback: try to read from JSON files
                    try:
                        with open('logs/performance_snapshots.json', 'r') as f:
                            lines = f.readlines()
                            if lines:
                                latest = json.loads(lines[-1])
                                portfolio_data = latest
                            else:
                                portfolio_data = {
                                    "timestamp": datetime.now().isoformat(),
                                    "total_value": 0,
                                    "available_balance": 0,
                                    "positions": {},
                                    "unrealized_pnl": 0.0
                                }
                    except FileNotFoundError:
                        portfolio_data = {
                            "timestamp": datetime.now().isoformat(),
                            "total_value": 0,
                            "available_balance": 0,
                            "positions": {},
                            "unrealized_pnl": 0.0
                        }
                
                return {"success": True, "data": portfolio_data}
                
            except Exception as e:
                self.logger.log_error("get_portfolio", e)
                return {"success": False, "error": str(e)}

        @self.app.get("/api/trades")
        async def get_trades(limit: int = 20):
            """Get trade history from database."""
            try:
                trades = self.db.get_recent_trades(limit) if hasattr(self.db, 'get_recent_trades') else []
                return {"success": True, "data": trades}
            except Exception as e:
                self.logger.log_error("get_trades", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/performance")
        async def get_performance():
            """Get performance metrics from database."""
            try:
                # Get performance metrics using independent performance tracker
                metrics = self.performance_tracker.get_performance_metrics()
                
                # Also get trading statistics from database
                db_stats = self.db.get_trading_statistics() if hasattr(self.db, 'get_trading_statistics') else {}
                
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
                    "database_stats": db_stats,
                    "report": self.performance_tracker.generate_performance_report()
                }
                
                return {"success": True, "data": performance_data}
                
            except Exception as e:
                self.logger.log_error("get_performance", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/ai-decisions")
        async def get_ai_decisions(limit: int = 20):
            """Get AI decision history."""
            try:
                decisions = self.db.get_ai_decisions(limit=limit)
                return {"success": True, "data": decisions}
            except Exception as e:
                self.logger.log_error("get_ai_decisions", e)
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/portfolio-history")
        async def get_portfolio_history(days: int = 7):
            """Get portfolio value history."""
            try:
                # Get from database first
                snapshots = self.db.get_portfolio_snapshots(limit=days*24) if hasattr(self.db, 'get_portfolio_snapshots') else []
                
                if not snapshots:
                    # Fallback to JSON file
                    try:
                        with open('logs/performance_snapshots.json', 'r') as f:
                            snapshots = [json.loads(line) for line in f if line.strip()]
                    except FileNotFoundError:
                        snapshots = []
                
                # Format for charting
                history = []
                for snapshot in snapshots[-days*24:]:  # Last N days
                    if isinstance(snapshot, dict):
                        history.append({
                            "timestamp": snapshot['timestamp'],
                            "value": snapshot.get('total_value', 0)
                        })
                
                return {"success": True, "data": history}
                
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
                    
                    <!-- Manual Trading -->
                    <div class="card">
                        <h3>⚡ Manual Trading</h3>
                        <div>
                            <select id="trade-symbol">
                                <option value="BTCUSDT">BTC/USDT</option>
                                <option value="ETHUSDT">ETH/USDT</option>
                                <option value="ADAUSDT">ADA/USDT</option>
                                <option value="SOLUSDT">SOL/USDT</option>
                            </select>
                            <input type="number" id="trade-amount" placeholder="Amount %" value="5" min="1" max="20">
                            <button onclick="executeTrade('BUY')">🟢 BUY</button>
                            <button onclick="executeTrade('SELL')">🔴 SELL</button>
                        </div>
                    </div>
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
                        element.innerHTML = `
                            <div class="metric">
                                <span class="metric-label">Status</span>
                                <span class="metric-value">
                                    <span class="status-indicator status-online"></span>Online
                                </span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Cycle Count</span>
                                <span class="metric-value">${status.cycle_count}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Open Positions</span>
                                <span class="metric-value">${status.positions}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Risk Score</span>
                                <span class="metric-value">${status.risk_score.toFixed(1)}</span>
                            </div>
                        `;
                    } else {
                        element.innerHTML = '<div class="metric"><span class="status-indicator status-offline"></span>Bot Offline</div>';
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