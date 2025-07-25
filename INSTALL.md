# 🚀 Quick Installation Guide

## 📦 Automated Setup (Recommended)

Choose your preferred setup method:

### 🐍 **Python Setup Script (All Platforms)**
```bash
python3 setup.py
```

### 🐧 **Bash Setup Script (Unix/Linux/macOS)**
```bash
chmod +x setup.sh
./setup.sh
```

---

## ✅ **What the Setup Scripts Do:**

1. **🐍 Check Python 3.8+** - Verifies Python installation
2. **🌐 Create Virtual Environment** - Isolates dependencies  
3. **📦 Install Dependencies** - Installs all required packages
4. **🔧 Setup Configuration** - Creates `.env` file from template
5. **📁 Create Directories** - Sets up `logs/`, `cache/`, `temp/`
6. **🔍 Verify Installation** - Tests that everything works

---

## 🔧 **Manual Setup (Alternative)**

If you prefer manual installation:

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate  # Unix/Mac
# OR
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env

# 5. Create directories
mkdir -p logs cache temp
```

---

## 📝 **After Setup:**

1. **Configure API Keys** in `.env` file:
   - `OPENAI_API_KEY` (required)
   - `BINANCE_TESTNET_API_KEY` (for testing)
   - `BINANCE_LIVE_API_KEY` (for live trading)

2. **Test the installation**:
   ```bash
   python3 validate_apis.py
   ```

3. **Start using**:
   ```bash
   # Dashboard only
   python3 dashboard_standalone.py

   # Trading bot
   python3 main.py
   ```

---

## 🆘 **Troubleshooting:**

### **Python not found:**
- Install Python 3.8+ from [python.org](https://python.org)

### **Permission denied:**
```bash
chmod +x setup.sh
```

### **Dependencies fail to install:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### **Virtual environment issues:**
```bash
rm -rf venv
python3 -m venv venv
```

---

## 🎯 **Quick Start Commands:**

```bash
# Option 1: Python setup (recommended)
python3 setup.py

# Option 2: Bash setup (Unix/Linux/macOS)
./setup.sh

# Then configure your API keys and run:
python3 dashboard_standalone.py
```

**📖 For detailed usage, see `USAGE_GUIDE.md`** 