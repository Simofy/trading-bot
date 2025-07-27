# Trading Bot Usage Guide

## 🚀 Running Bot and Dashboard Separately

Your trading bot now supports **independent operation** - you can run the trading bot and dashboard as separate processes!

---

## 📊 **Option 1: Standalone Dashboard (Recommended)**

**Run the dashboard independently** - reads data from database and files.

```bash
# Start the standalone dashboard
python3 dashboard_standalone.py
```

**✅ Features:**
- 📈 **Portfolio tracking** from database
- 🧠 **AI decision history**
- 📊 **Performance analytics**
- ⚡ **Real-time market data**
- 🔄 **Manual trade queueing** (executed when bot runs)
- 📱 **Mobile-responsive interface**
- 🗄️ **Works without bot running**

**🌐 URL**: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🤖 **Option 2: Trading Bot Only**

**Run the actual trading bot** - makes trades and updates database.

```bash
# Single trading cycle
python3 demo_single_cycle.py

# Continuous trading
python3 main.py
```

**✅ Features:**
- 🧠 **AI-powered trading decisions**
- 📊 **Real market data analysis**
- 🛡️ **Risk management**
- 💼 **Automatic trade execution**
- 📝 **Complete logging**
- ⚡ **Processes manual trades from dashboard**

---

## 🔄 **Option 3: Both Together (Advanced)**

**Run bot and dashboard together** with live integration.

```bash
# Terminal 1: Start the bot
python3 main.py

# Terminal 2: Start dashboard with live bot features
python3 demo_dashboard.py  # (includes live technical analysis)
```

---

## 📋 **How It Works**

### **Data Flow:**
1. **Trading Bot** → Writes to database + JSON files
2. **Dashboard** → Reads from database + JSON files
3. **Manual Trades** → Dashboard queues → Bot executes

### **Shared Data Sources:**
- **Database**: `logs/trading_bot.db`
- **Portfolio**: `logs/performance_snapshots.json`
- **Trades**: `logs/performance_trades.json`
- **Logs**: `logs/trading_bot.log`
- **Manual Trade Queue**: `logs/manual_trades_queue.json`

---

## 🎯 **Common Usage Scenarios**

### **🔍 Monitoring Only**
```bash
# Just view analytics (no trading)
python3 dashboard_standalone.py
```

### **🤖 Trading Only**
```bash
# Just run trading bot (no dashboard)
python3 main.py
```

### **⚡ Development/Testing**
```bash
# Terminal 1: Start dashboard
python3 dashboard_standalone.py

# Terminal 2: Run single test cycle
python3 demo_single_cycle.py
```

### **🚀 Production Setup**
```bash
# Terminal 1: Continuous trading
python3 main.py

# Terminal 2: Monitoring dashboard
python3 dashboard_standalone.py
```

---

## 🔧 **Manual Trading**

### **When Bot is Running:**
- ✅ **Immediate execution** via dashboard
- ⚡ **Live technical analysis**
- 📊 **Real-time updates**

### **When Bot is Offline:**
- 📝 **Trade requests queued** in `logs/manual_trades_queue.json`
- ⏰ **Executed when bot starts**
- 📋 **Status tracked** in dashboard

---

## 📊 **Analytics Access**

### **Real-time Dashboard:**
- 🌐 **Web Interface**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 📱 **Mobile friendly**
- 🔄 **Auto-refresh every 30 seconds**

### **Database Queries:**
```bash
# Direct database access
sqlite3 logs/trading_bot.db

# Quick portfolio check
sqlite3 logs/trading_bot.db "SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT 1;"

# Recent AI decisions  
sqlite3 logs/trading_bot.db "SELECT * FROM ai_decisions ORDER BY timestamp DESC LIMIT 5;"
```

### **JSON Files:**
```bash
# Latest portfolio
tail -1 logs/performance_snapshots.json | python3 -m json.tool

# Trading history
cat logs/performance_trades.json
```

---

## ⚠️ **Important Notes**

### **🔐 Security:**
- Dashboard runs on `127.0.0.1:8000` (localhost only)
- No external access by default
- API keys remain secure in `.env`

### **📊 Performance:**
- Dashboard reads from database (minimal resource usage)
- Bot writes to database (tracks everything)
- Both can run on same or different machines

### **🛡️ Safety:**
- Manual trades respect risk management rules
- Emergency stops work in both modes
- All trades logged and tracked

---

## 🎉 **Quick Start Commands**

```bash
# 1. Start standalone dashboard (most common)
python3 dashboard_standalone.py

# 2. Run a single trading cycle
python3 demo_single_cycle.py

# 3. View analytics overview
python3 -c "
# Database removed - now using Binance API for all analytics
# Historical data is fetched directly from exchange
stats = db.get_trading_statistics()
print(f'Total trades: {stats[\"total_trades\"]}')
print(f'Portfolio value: ${stats.get(\"latest_portfolio_value\", 0):,.2f}')
"
```

---

**🚀 Enjoy your independent trading bot setup!** The dashboard and bot can now run completely separately while sharing data seamlessly. 