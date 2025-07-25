"""Logging configuration for the trading bot."""

import logging
import logging.handlers
import os
from datetime import datetime


def setup_logger(log_level: str = "INFO", log_file: str = "trading_bot.log"):
    """Setup logging configuration for the trading bot."""
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    log_file_path = os.path.join("logs", log_file)
    
    # Configure logging
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized - Level: {log_level}, File: {log_file_path}")


class TradingLogger:
    """Specialized logger for trading operations."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
        # Create a separate file for trading actions
        trade_log_path = os.path.join("logs", "trades.log")
        trade_handler = logging.handlers.RotatingFileHandler(
            trade_log_path,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10
        )
        trade_formatter = logging.Formatter(
            '%(asctime)s - TRADE - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        trade_handler.setFormatter(trade_formatter)
        
        # Create trading logger
        self.trade_logger = logging.getLogger(f"{name}.trades")
        self.trade_logger.addHandler(trade_handler)
        self.trade_logger.setLevel(logging.INFO)
    
    def log_trade(self, action: str, symbol: str, amount: float, price: float, **kwargs):
        """Log trading actions."""
        trade_info = {
            "action": action,
            "symbol": symbol,
            "amount": amount,
            "price": price,
            **kwargs
        }
        self.trade_logger.info(f"{trade_info}")
    
    def log_ai_decision(self, prompt: str, response: str, decision: dict):
        """Log AI trading decisions."""
        self.logger.info(f"AI Decision - Prompt length: {len(prompt)}, Response: {response[:200]}..., Decision: {decision}")
    
    def log_portfolio_update(self, portfolio_value: float, pnl: float, positions: dict):
        """Log portfolio status updates."""
        self.logger.info(f"Portfolio Update - Value: ${portfolio_value:.2f}, PnL: ${pnl:.2f}, Positions: {len(positions)}")
    
    def log_risk_event(self, event_type: str, details: str):
        """Log risk management events."""
        self.logger.warning(f"Risk Event - {event_type}: {details}")
    
    def log_error(self, operation: str, error: Exception):
        """Log errors with context."""
        self.logger.error(f"Error in {operation}: {error}", exc_info=True) 