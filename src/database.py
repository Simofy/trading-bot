"""Database management for persistent storage of trading data."""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from contextlib import contextmanager

from .logger import TradingLogger


class TradingDatabase:
    """SQLite database for persistent trading data storage."""
    
    def __init__(self, db_path: str = "logs/trading_bot.db"):
        self.logger = TradingLogger(__name__)
        self.db_path = Path(db_path)
        
        # Ensure logs directory exists
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Trades table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        action TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        amount REAL NOT NULL,
                        fees REAL DEFAULT 0.0,
                        order_id TEXT,
                        success BOOLEAN DEFAULT TRUE,
                        strategy TEXT,
                        ai_confidence REAL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Portfolio snapshots table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        total_value REAL NOT NULL,
                        available_balance REAL NOT NULL,
                        positions TEXT NOT NULL,  -- JSON string
                        unrealized_pnl REAL DEFAULT 0.0,
                        realized_pnl REAL DEFAULT 0.0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Performance metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        total_return REAL NOT NULL,
                        total_return_pct REAL NOT NULL,
                        daily_return REAL DEFAULT 0.0,
                        volatility REAL DEFAULT 0.0,
                        sharpe_ratio REAL DEFAULT 0.0,
                        max_drawdown REAL DEFAULT 0.0,
                        win_rate REAL DEFAULT 0.0,
                        total_trades INTEGER DEFAULT 0,
                        portfolio_value REAL NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date)
                    )
                ''')
                
                # AI decisions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ai_decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        symbol TEXT,
                        action TEXT NOT NULL,
                        allocation_percentage REAL,
                        confidence REAL,
                        reasoning TEXT,
                        market_data TEXT,  -- JSON string
                        technical_analysis TEXT,  -- JSON string
                        executed BOOLEAN DEFAULT FALSE,
                        execution_result TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Risk events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS risk_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        description TEXT NOT NULL,
                        portfolio_value REAL,
                        affected_symbol TEXT,
                        action_taken TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Market data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS market_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        price REAL NOT NULL,
                        volume_24h REAL DEFAULT 0.0,
                        price_change_24h REAL DEFAULT 0.0,
                        market_cap REAL DEFAULT 0.0,
                        source TEXT DEFAULT 'unknown',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_portfolio_timestamp ON portfolio_snapshots(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_decisions_timestamp ON ai_decisions(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp)')
                
                conn.commit()
                self.logger.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.log_error("_initialize_database", e)
            raise
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def insert_trade(self, trade_data: Dict) -> int:
        """Insert a new trade record."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO trades (
                        timestamp, symbol, action, quantity, price, amount,
                        fees, order_id, success, strategy, ai_confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade_data.get('timestamp', datetime.now().isoformat()),
                    trade_data['symbol'],
                    trade_data['action'],
                    trade_data['quantity'],
                    trade_data['price'],
                    trade_data['amount'],
                    trade_data.get('fees', 0.0),
                    trade_data.get('order_id', ''),
                    trade_data.get('success', True),
                    trade_data.get('strategy', 'ai_advisor'),
                    trade_data.get('ai_confidence', 0.0)
                ))
                
                trade_id = cursor.lastrowid
                conn.commit()
                
                self.logger.logger.info(f"Trade inserted with ID: {trade_id}")
                return trade_id
                
        except Exception as e:
            self.logger.log_error("insert_trade", e)
            return -1
    
    def insert_portfolio_snapshot(self, snapshot_data: Dict) -> int:
        """Insert a portfolio snapshot."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert positions dict to JSON string
                positions_json = json.dumps(snapshot_data.get('positions', {}))
                
                cursor.execute('''
                    INSERT INTO portfolio_snapshots (
                        timestamp, total_value, available_balance, positions,
                        unrealized_pnl, realized_pnl
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    snapshot_data.get('timestamp', datetime.now().isoformat()),
                    snapshot_data['total_value'],
                    snapshot_data['available_balance'],
                    positions_json,
                    snapshot_data.get('unrealized_pnl', 0.0),
                    snapshot_data.get('realized_pnl', 0.0)
                ))
                
                snapshot_id = cursor.lastrowid
                conn.commit()
                
                return snapshot_id
                
        except Exception as e:
            self.logger.log_error("insert_portfolio_snapshot", e)
            return -1
    
    def insert_performance_metrics(self, metrics_data: Dict) -> int:
        """Insert daily performance metrics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO performance_metrics (
                        date, total_return, total_return_pct, daily_return,
                        volatility, sharpe_ratio, max_drawdown, win_rate,
                        total_trades, portfolio_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                    metrics_data['total_return'],
                    metrics_data['total_return_pct'],
                    metrics_data.get('daily_return', 0.0),
                    metrics_data.get('volatility', 0.0),
                    metrics_data.get('sharpe_ratio', 0.0),
                    metrics_data.get('max_drawdown', 0.0),
                    metrics_data.get('win_rate', 0.0),
                    metrics_data.get('total_trades', 0),
                    metrics_data['portfolio_value']
                ))
                
                metrics_id = cursor.lastrowid
                conn.commit()
                
                return metrics_id
                
        except Exception as e:
            self.logger.log_error("insert_performance_metrics", e)
            return -1
    
    def insert_ai_decision(self, decision_data: Dict) -> int:
        """Insert an AI trading decision."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert complex data to JSON strings
                market_data_json = json.dumps(decision_data.get('market_data', {}))
                technical_analysis_json = json.dumps(decision_data.get('technical_analysis', {}))
                
                cursor.execute('''
                    INSERT INTO ai_decisions (
                        timestamp, symbol, action, allocation_percentage,
                        confidence, reasoning, market_data, technical_analysis,
                        executed, execution_result
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    decision_data.get('timestamp', datetime.now().isoformat()),
                    decision_data.get('symbol'),
                    decision_data['action'],
                    decision_data.get('allocation_percentage'),
                    decision_data.get('confidence', 0.0),
                    decision_data.get('reasoning', ''),
                    market_data_json,
                    technical_analysis_json,
                    decision_data.get('executed', False),
                    decision_data.get('execution_result', '')
                ))
                
                decision_id = cursor.lastrowid
                conn.commit()
                
                return decision_id
                
        except Exception as e:
            self.logger.log_error("insert_ai_decision", e)
            return -1
    
    def insert_risk_event(self, event_data: Dict) -> int:
        """Insert a risk management event."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO risk_events (
                        timestamp, event_type, severity, description,
                        portfolio_value, affected_symbol, action_taken
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_data.get('timestamp', datetime.now().isoformat()),
                    event_data['event_type'],
                    event_data.get('severity', 'INFO'),
                    event_data['description'],
                    event_data.get('portfolio_value'),
                    event_data.get('affected_symbol'),
                    event_data.get('action_taken', '')
                ))
                
                event_id = cursor.lastrowid
                conn.commit()
                
                return event_id
                
        except Exception as e:
            self.logger.log_error("insert_risk_event", e)
            return -1
    
    def insert_market_data(self, market_data: Dict) -> int:
        """Insert market data point."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO market_data (
                        timestamp, symbol, price, volume_24h,
                        price_change_24h, market_cap, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    market_data.get('timestamp', datetime.now().isoformat()),
                    market_data['symbol'],
                    market_data['price'],
                    market_data.get('volume_24h', 0.0),
                    market_data.get('price_change_24h', 0.0),
                    market_data.get('market_cap', 0.0),
                    market_data.get('source', 'unknown')
                ))
                
                data_id = cursor.lastrowid
                conn.commit()
                
                return data_id
                
        except Exception as e:
            self.logger.log_error("insert_market_data", e)
            return -1
    
    def get_trades(self, symbol: str = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get trade history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if symbol:
                    cursor.execute('''
                        SELECT * FROM trades 
                        WHERE symbol = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ? OFFSET ?
                    ''', (symbol, limit, offset))
                else:
                    cursor.execute('''
                        SELECT * FROM trades 
                        ORDER BY timestamp DESC 
                        LIMIT ? OFFSET ?
                    ''', (limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.log_error("get_trades", e)
            return []
    
    def get_portfolio_snapshots(self, limit: int = 100) -> List[Dict]:
        """Get portfolio snapshots."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM portfolio_snapshots 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                snapshots = []
                
                for row in rows:
                    snapshot = dict(row)
                    # Parse JSON positions
                    snapshot['positions'] = json.loads(snapshot['positions'])
                    snapshots.append(snapshot)
                
                return snapshots
                
        except Exception as e:
            self.logger.log_error("get_portfolio_snapshots", e)
            return []
    
    def get_performance_metrics(self, days: int = 30) -> List[Dict]:
        """Get performance metrics for the last N days."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM performance_metrics 
                    ORDER BY date DESC 
                    LIMIT ?
                ''', (days,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.log_error("get_performance_metrics", e)
            return []
    
    def get_ai_decisions(self, limit: int = 50) -> List[Dict]:
        """Get AI decision history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM ai_decisions 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                decisions = []
                
                for row in rows:
                    decision = dict(row)
                    # Parse JSON data
                    decision['market_data'] = json.loads(decision['market_data'])
                    decision['technical_analysis'] = json.loads(decision['technical_analysis'])
                    decisions.append(decision)
                
                return decisions
                
        except Exception as e:
            self.logger.log_error("get_ai_decisions", e)
            return []
    
    def get_risk_events(self, severity: str = None, limit: int = 50) -> List[Dict]:
        """Get risk events."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if severity:
                    cursor.execute('''
                        SELECT * FROM risk_events 
                        WHERE severity = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (severity, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM risk_events 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.log_error("get_risk_events", e)
            return []
    
    def get_trading_statistics(self) -> Dict:
        """Get comprehensive trading statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total trades
                cursor.execute('SELECT COUNT(*) as total_trades FROM trades')
                total_trades = cursor.fetchone()['total_trades']
                
                # Successful trades
                cursor.execute('SELECT COUNT(*) as successful_trades FROM trades WHERE success = 1')
                successful_trades = cursor.fetchone()['successful_trades']
                
                # Trade by action
                cursor.execute('SELECT action, COUNT(*) as count FROM trades GROUP BY action')
                trades_by_action = {row['action']: row['count'] for row in cursor.fetchall()}
                
                # Most traded symbols
                cursor.execute('''
                    SELECT symbol, COUNT(*) as count 
                    FROM trades 
                    GROUP BY symbol 
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                top_symbols = [dict(row) for row in cursor.fetchall()]
                
                # Recent portfolio value
                cursor.execute('''
                    SELECT total_value 
                    FROM portfolio_snapshots 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''')
                latest_value_row = cursor.fetchone()
                latest_portfolio_value = latest_value_row['total_value'] if latest_value_row else 0
                
                return {
                    'total_trades': total_trades,
                    'successful_trades': successful_trades,
                    'success_rate': successful_trades / total_trades if total_trades > 0 else 0,
                    'trades_by_action': trades_by_action,
                    'top_symbols': top_symbols,
                    'latest_portfolio_value': latest_portfolio_value
                }
                
        except Exception as e:
            self.logger.log_error("get_trading_statistics", e)
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to manage database size."""
        try:
            cutoff_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Keep recent trades but clean up very old ones
                cursor.execute('''
                    DELETE FROM market_data 
                    WHERE DATE(timestamp) < DATE(?, '-{} days')
                '''.format(days_to_keep), (cutoff_date,))
                
                # Clean up old portfolio snapshots (keep daily snapshots)
                cursor.execute('''
                    DELETE FROM portfolio_snapshots 
                    WHERE DATE(timestamp) < DATE(?, '-{} days')
                    AND id NOT IN (
                        SELECT MIN(id) 
                        FROM portfolio_snapshots 
                        GROUP BY DATE(timestamp)
                    )
                '''.format(days_to_keep), (cutoff_date,))
                
                conn.commit()
                self.logger.logger.info("Database cleanup completed")
                
        except Exception as e:
            self.logger.log_error("cleanup_old_data", e)
    
    def export_data(self, output_path: str, table_name: str = None):
        """Export data to JSON file."""
        try:
            export_data = {}
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if table_name:
                    tables = [table_name]
                else:
                    # Get all table names
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    export_data[table] = [dict(row) for row in rows]
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.logger.logger.info(f"Data exported to {output_path}")
            
        except Exception as e:
            self.logger.log_error("export_data", e)
    
    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent trades."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM trades 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.log_error("get_recent_trades", e)
            return [] 