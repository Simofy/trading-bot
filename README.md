# AI-Powered Cryptocurrency Trading Bot

An intelligent cryptocurrency trading bot that uses AI (OpenAI GPT-4) to make trading decisions with comprehensive risk management and safety features.

## 🚀 Features

- **AI-Powered Decision Making**: Uses OpenAI GPT-4 for intelligent trading recommendations with technical analysis
- **Technical Analysis**: Comprehensive indicators (RSI, MACD, Bollinger Bands, trend analysis, support/resistance)
- **Advanced Performance Analytics**: Sharpe ratio, Sortino ratio, Calmar ratio, VaR calculations, stress testing
- **Database Integration**: SQLite database for persistent storage of trades, performance, and AI decisions
- **Real-time Web Dashboard**: FastAPI-based dashboard with interactive charts and manual trading interface
- **Enhanced Risk Management**: Multi-layered risk assessment with VaR, correlation analysis, and stress testing
- **Real-time Market Data**: Integration with CoinGecko for live cryptocurrency prices with robust error handling
- **Exchange Integration**: Binance spot trading support (testnet and live) with multiple fallback modes
- **Smart Safety Features**: Emergency stops, daily limits, portfolio protection, and concentration limits
- **Advanced Logging**: Detailed trade logging, performance tracking, and comprehensive audit trails
- **Configurable Parameters**: Extensive configuration options for risk tolerance and trading strategies

## 🛡️ Safety Features

- **Sandbox Mode**: Test trading strategies without real money
- **Emergency Stop Loss**: Automatic portfolio protection
- **Position Limits**: Maximum number of concurrent positions
- **Daily Trade Limits**: Prevent over-trading
- **Risk Scoring**: AI decisions evaluated against risk metrics
- **Concentration Limits**: Prevent over-exposure to single assets

## 📋 Prerequisites

- Python 3.8+
- OpenAI API key (required)
- Binance account (for live trading)
- CoinGecko API key (optional, for enhanced data)

## 🔧 Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd trading_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and preferences
```

## ⚙️ Configuration

### Required API Keys

1. **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
2. **Binance API Key**: Create from [Binance API Management](https://www.binance.com/en/my/settings/api-management)

### Key Configuration Options

```bash
# Start with sandbox mode for testing
USE_SANDBOX=true

# Conservative risk settings (recommended for beginners)
MAX_PORTFOLIO_RISK=0.02  # 2% max risk per trade
STOP_LOSS_PERCENTAGE=0.05  # 5% stop loss
MAX_TRADES_PER_DAY=10

# Trading interval (in seconds)
TRADING_INTERVAL=300  # 5 minutes between cycles
```

## 🚀 Usage

### Basic Usage

```bash
# Run the standard trading bot
python main.py

# Run enhanced system demo (showcases all new features)
python demo_enhanced_system.py

# Start web dashboard for real-time monitoring
python demo_dashboard.py

# Quick testing with 30-second cycles
python demo_quick_cycles.py

# Single cycle demonstration
python demo_single_cycle.py
```

### Environment Variables

Edit your `.env` file with appropriate values:

```bash
OPENAI_API_KEY=sk-your-key-here
USE_SANDBOX=true  # Start with this for testing
MAX_PORTFOLIO_RISK=0.02  # 2% risk per trade
```

## 🧠 How It Works

1. **Market Analysis**: Fetches real-time cryptocurrency prices and market data
2. **AI Decision Making**: GPT-4 analyzes market conditions and provides trading recommendations
3. **Risk Assessment**: Multi-factor risk evaluation including volatility, correlation, and portfolio concentration
4. **Trade Execution**: Executes approved trades through Binance API
5. **Monitoring**: Continuous portfolio monitoring and emergency stop protection

## 📊 Risk Management

The bot implements multiple layers of risk protection:

- **Portfolio Risk Limits**: Maximum 2% risk per trade (configurable)
- **Position Limits**: Maximum 3 concurrent positions (configurable)
- **Emergency Stops**: 15% portfolio drawdown protection
- **Daily Limits**: Maximum 10 trades per day
- **Volatility Checks**: Higher risk for volatile assets
- **Concentration Limits**: Prevents over-exposure to single assets

## 🔍 Monitoring

### Web Dashboard
Real-time monitoring through a modern web interface:

```bash
python demo_dashboard.py
# Open http://127.0.0.1:8000 in your browser
```

**Dashboard Features:**
- 📊 Real-time portfolio value charts
- 🔄 Live trade execution and history
- 🧠 AI decision tracking and analysis
- 📈 Performance metrics (Sharpe ratio, win rate, etc.)
- ⚡ Manual trading interface
- 📱 Responsive design for mobile/desktop
- 🔄 Auto-refresh every 30 seconds

### Traditional Logging
Comprehensive file-based logging:

- **Trade Logs**: All trading activities logged to `logs/trades.log`
- **System Logs**: General operation logs in `logs/trading_bot.log`
- **Database Storage**: Persistent storage in `logs/trading_bot.db`
- **Performance Files**: JSON exports in `logs/performance_*.json`
- **Portfolio Updates**: Real-time portfolio value and position tracking
- **AI Decisions**: All AI recommendations and reasoning logged

## ⚠️ Important Warnings

1. **Start with Sandbox**: Always test with `USE_SANDBOX=true` first
2. **Small Amounts**: Start with small trading amounts
3. **Monitor Closely**: Especially during initial testing
4. **API Limits**: Respect exchange API rate limits
5. **No Guarantees**: Trading cryptocurrencies involves significant risk

## 🎯 Supported Cryptocurrencies

Currently supports major cryptocurrencies:
- Bitcoin (BTC)
- Ethereum (ETH)
- Cardano (ADA)
- Polkadot (DOT)
- Chainlink (LINK)
- Solana (SOL)
- Polygon (MATIC)
- Avalanche (AVAX)

## 🏗️ Architecture

```
src/
├── config.py              # Configuration management
├── logger.py              # Logging setup
├── ai_advisor.py          # AI decision making with GPT-4
├── technical_analysis.py  # Technical indicators (RSI, MACD, etc.)
├── market_data.py         # Market data provider (CoinGecko)
├── exchange.py            # Exchange integration (Binance)
├── risk_manager.py        # Risk management with VaR
├── performance_tracker.py # Advanced performance analytics
├── database.py            # SQLite database integration
├── dashboard.py           # FastAPI web dashboard
└── trading_bot.py         # Main bot orchestration
```

### Enhanced Components

- **Technical Analysis**: 15+ indicators including RSI, MACD, Bollinger Bands, trend analysis
- **Performance Tracker**: Sharpe ratio, Sortino ratio, Calmar ratio, drawdown analysis
- **Database Layer**: SQLite for persistent storage of trades, decisions, and performance
- **Web Dashboard**: Real-time monitoring with FastAPI and interactive charts
- **Enhanced Risk Management**: VaR calculations, stress testing, correlation analysis

## 🔧 Advanced Configuration

### Risk Management Tuning

```bash
# Conservative settings (recommended)
MAX_PORTFOLIO_RISK=0.01  # 1% per trade
EMERGENCY_STOP_LOSS=0.10  # 10% portfolio stop

# Moderate settings
MAX_PORTFOLIO_RISK=0.02  # 2% per trade
EMERGENCY_STOP_LOSS=0.15  # 15% portfolio stop

# Aggressive settings (high risk)
MAX_PORTFOLIO_RISK=0.05  # 5% per trade
EMERGENCY_STOP_LOSS=0.20  # 20% portfolio stop
```

### AI Model Configuration

```bash
AI_MODEL=gpt-4o-mini     # Most intelligent (recommended)
AI_TEMPERATURE=0.3       # Conservative responses
```

## 📈 Performance Tracking

The bot tracks:
- Total portfolio value
- Individual position performance
- Win/loss ratios
- Maximum drawdown
- Risk-adjusted returns

## 🛠️ Development

To modify or extend the bot:

1. **Add New Exchanges**: Implement exchange interface in `src/exchange.py`
2. **Custom Risk Rules**: Extend `src/risk_manager.py`
3. **Enhanced AI Prompts**: Modify prompts in `src/ai_advisor.py`
4. **New Data Sources**: Add providers in `src/market_data.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Cryptocurrency trading involves substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this software. Always do your own research and never invest more than you can afford to lose.

## 📞 Support

For issues and questions:
1. Check the logs in the `logs/` directory
2. Review configuration in `.env` file
3. Ensure all API keys are valid
4. Start with sandbox mode for testing

## 🔄 Updates

Keep the bot updated:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

Remember to always test updates in sandbox mode first! 