"""Configuration management for the trading bot."""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from decimal import Decimal

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load from .env file (standard convention)
except ImportError:
    pass  # dotenv not available, use environment variables directly


@dataclass
class Config:
    """Configuration class for the trading bot."""
    
    # API Keys
    openai_api_key: str = ""
    
    # Binance API Keys - Separate for Live and Testnet
    binance_live_api_key: str = ""
    binance_live_secret_key: str = ""
    binance_testnet_api_key: str = ""
    binance_testnet_secret_key: str = ""
    
    # CoinGecko API Key
    coingecko_api_key: str = ""  # Optional, free tier available
    
    # Trading Configuration
    trading_interval: int = 300  # 5 minutes between cycles
    max_portfolio_risk: Decimal = Decimal("0.75")  # 75% max risk for small portfolios (demo)
    stop_loss_percentage: Decimal = Decimal("0.05")  # 5% stop loss
    take_profit_percentage: Decimal = Decimal("0.10")  # 10% take profit
    max_trades_per_day: int = 10
    min_trade_amount: Decimal = Decimal("10.0")  # Minimum trade in USDT
    max_trade_amount: Decimal = Decimal("100.0")  # Maximum trade in USDT
    
    # Demo/Testing Configuration
    demo_initial_balance: Decimal = Decimal("10000.0")  # Initial demo balance in USDT
    
    # Supported cryptocurrencies
    supported_symbols: List[str] = None
    base_currency: str = "USDT"
    
    # Risk Management
    max_open_positions: int = 3
    portfolio_rebalance_threshold: Decimal = Decimal("0.20")  # 20%
    emergency_stop_loss: Decimal = Decimal("0.15")  # 15% portfolio loss
    
    # AI Configuration
    ai_model: str = "gpt-4o-mini"  # Much cheaper than gpt-4
    ai_temperature: float = 0.3
    max_ai_retries: int = 3
    ai_timeout: int = 30
    # Cost optimization
    ai_max_tokens: int = 300  # Reduced from 500
    ai_cache_decisions: bool = True  # Cache similar market conditions
    
    # Exchange Configuration
    use_sandbox: bool = False  # Default to live mode (set USE_SANDBOX=true for testing)
    exchange: str = "binance"  # Currently supports binance

    # Market Data Configuration
    use_real_market_data: bool = True  # Use real CoinGecko data by default
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "trading_bot.log"
    
    # Computed properties for backward compatibility and convenience
    @property
    def binance_api_key(self) -> str:
        """Get the appropriate Binance API key based on sandbox mode."""
        if self.use_sandbox:
            return self.binance_testnet_api_key
        else:
            return self.binance_live_api_key
    
    @property
    def binance_secret_key(self) -> str:
        """Get the appropriate Binance secret key based on sandbox mode."""
        if self.use_sandbox:
            return self.binance_testnet_secret_key
        else:
            return self.binance_live_secret_key

    @property 
    def should_use_real_market_data(self) -> bool:
        """Determine if we should use real market data from CoinGecko.
        
        For backward compatibility, we maintain the current logic:
        - If USE_REAL_MARKET_DATA is explicitly set, use that
        - Otherwise, fall back to the confusing USE_SANDBOX logic
        """
        # Check if the new setting is explicitly configured
        if hasattr(self, '_use_real_market_data_set'):
            return self.use_real_market_data
        
        # Fall back to the existing (confusing) logic for backward compatibility
        return self.use_sandbox
    
    def __post_init__(self):
        """Initialize configuration from environment variables."""
        self._load_from_env()
        self._validate_config()
        
        if self.supported_symbols is None:
            self.supported_symbols = [
                "BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", 
                "LINKUSDT", "SOLUSDT", "MATICUSDT", "AVAXUSDT"
            ]
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        
        # Binance API Keys
        self.binance_live_api_key = os.getenv("BINANCE_LIVE_API_KEY", self.binance_live_api_key)
        self.binance_live_secret_key = os.getenv("BINANCE_LIVE_SECRET_KEY", self.binance_live_secret_key)
        self.binance_testnet_api_key = os.getenv("BINANCE_TESTNET_API_KEY", self.binance_testnet_api_key)
        self.binance_testnet_secret_key = os.getenv("BINANCE_TESTNET_SECRET_KEY", self.binance_testnet_secret_key)
        
        # CoinGecko API Key
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY", self.coingecko_api_key)
        
        # Backward compatibility: if old env vars are set and new ones aren't, use old ones
        if not self.binance_testnet_api_key and os.getenv("BINANCE_API_KEY"):
            self.binance_testnet_api_key = os.getenv("BINANCE_API_KEY")
            self.binance_testnet_secret_key = os.getenv("BINANCE_SECRET_KEY", "")
        
        # Trading Configuration
        self.trading_interval = int(os.getenv("TRADING_INTERVAL", self.trading_interval))
        self.max_portfolio_risk = Decimal(os.getenv("MAX_PORTFOLIO_RISK", str(self.max_portfolio_risk)))
        self.stop_loss_percentage = Decimal(os.getenv("STOP_LOSS_PERCENTAGE", str(self.stop_loss_percentage)))
        self.take_profit_percentage = Decimal(os.getenv("TAKE_PROFIT_PERCENTAGE", str(self.take_profit_percentage)))
        self.max_trades_per_day = int(os.getenv("MAX_TRADES_PER_DAY", self.max_trades_per_day))
        self.min_trade_amount = Decimal(os.getenv("MIN_TRADE_AMOUNT", str(self.min_trade_amount)))
        self.max_trade_amount = Decimal(os.getenv("MAX_TRADE_AMOUNT", str(self.max_trade_amount)))
        
        # Demo/Testing Configuration
        self.demo_initial_balance = Decimal(os.getenv("DEMO_INITIAL_BALANCE", str(self.demo_initial_balance)))
        
        # Risk Management
        self.max_open_positions = int(os.getenv("MAX_OPEN_POSITIONS", self.max_open_positions))
        self.emergency_stop_loss = Decimal(os.getenv("EMERGENCY_STOP_LOSS", str(self.emergency_stop_loss)))
        
        # AI Configuration
        self.ai_model = os.getenv("AI_MODEL", self.ai_model)
        self.ai_temperature = float(os.getenv("AI_TEMPERATURE", self.ai_temperature))
        self.ai_max_tokens = int(os.getenv("AI_MAX_TOKENS", getattr(self, 'ai_max_tokens', 300)))
        self.ai_cache_decisions = os.getenv("AI_CACHE_DECISIONS", "true").lower() == "true"
        
        # Exchange Configuration
        self.use_sandbox = os.getenv("USE_SANDBOX", "false").lower() == "true"
        self.exchange = os.getenv("EXCHANGE", self.exchange)
        
        # Handle the new market data setting
        market_data_env = os.getenv("USE_REAL_MARKET_DATA")
        if market_data_env is not None:
            self._use_real_market_data_set = True
            self.use_real_market_data = market_data_env.lower() == "true"
        else:
            self._use_real_market_data_set = False
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_file = os.getenv("LOG_FILE", self.log_file)
    
    def _validate_config(self):
        """Validate configuration values."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        # Validate Binance API keys based on mode
        if self.use_sandbox:
            if not self.binance_testnet_api_key or not self.binance_testnet_secret_key:
                print("⚠️  Warning: Binance testnet API credentials not configured - will use demo mode")
        else:
            if not self.binance_live_api_key or not self.binance_live_secret_key:
                raise ValueError("Binance live API credentials required for live trading")
        
        if self.max_portfolio_risk <= 0 or self.max_portfolio_risk > Decimal("0.8"):
            raise ValueError("Max portfolio risk must be between 0 and 80%")
        
        if self.stop_loss_percentage <= 0 or self.stop_loss_percentage > Decimal("0.2"):
            raise ValueError("Stop loss percentage must be between 0 and 20%")
        
        if self.min_trade_amount >= self.max_trade_amount:
            raise ValueError("Min trade amount must be less than max trade amount")
    
    def get_symbol_config(self, symbol: str) -> Dict:
        """Get configuration specific to a trading symbol."""
        return {
            "min_trade_amount": self.min_trade_amount,
            "max_trade_amount": self.max_trade_amount,
            "stop_loss": self.stop_loss_percentage,
            "take_profit": self.take_profit_percentage
        } 