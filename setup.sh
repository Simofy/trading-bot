#!/bin/bash

# =============================================================================
# AI Trading Bot - Setup Script (Bash Version)
# =============================================================================
# Quick setup script for Unix/Linux/macOS systems
# Usage: chmod +x setup.sh && ./setup.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
print_banner() {
    echo -e "${CYAN}🚀 AI TRADING BOT - SETUP SCRIPT${NC}"
    echo "=============================================="
    echo -e "${BLUE}🤖 Automated project initialization${NC}"
    echo -e "${BLUE}📦 Dependency installation${NC}"
    echo -e "${BLUE}🔧 Configuration setup${NC}"
    echo "=============================================="
    echo
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    echo -e "${BLUE}🐍 Checking Python installation...${NC}"
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
        return 0
    else
        echo -e "${RED}❌ Python 3 not found${NC}"
        echo -e "${YELLOW}💡 Please install Python 3.8 or newer${NC}"
        return 1
    fi
}

# Create virtual environment
create_venv() {
    echo -e "${BLUE}🌐 Setting up virtual environment...${NC}"
    
    if [ -d "venv" ]; then
        echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
        read -p "🔄 Recreate virtual environment? (y/n): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}🗑️  Removing existing virtual environment...${NC}"
            rm -rf venv
        else
            echo -e "${GREEN}✅ Using existing virtual environment${NC}"
            return 0
        fi
    fi
    
    echo -e "${BLUE}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
}

# Install dependencies
install_deps() {
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}❌ requirements.txt not found${NC}"
        return 1
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    echo -e "${BLUE}⬇️  Installing packages from requirements.txt...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
}

# Setup environment file
setup_env() {
    echo -e "${BLUE}🔧 Setting up environment configuration...${NC}"
    
    if [ -f ".env" ]; then
        echo -e "${YELLOW}⚠️  .env file already exists${NC}"
        read -p "🔄 Overwrite existing .env file? (y/n): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}✅ Keeping existing .env file${NC}"
            return 0
        fi
    fi
    
    if [ ! -f ".env.example" ]; then
        echo -e "${RED}❌ .env.example template not found${NC}"
        return 1
    fi
    
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created from template${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Update .env with your actual API keys!${NC}"
}

# Create directories
create_dirs() {
    echo -e "${BLUE}📁 Creating project directories...${NC}"
    
    directories=("logs" "cache" "temp")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            echo -e "${GREEN}📂 Created: $dir/${NC}"
        else
            echo -e "${GREEN}✅ Exists: $dir/${NC}"
        fi
    done
}

# Verify setup
verify_setup() {
    echo -e "${BLUE}🔍 Verifying setup...${NC}"
    
    # Check virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${RED}❌ Virtual environment missing${NC}"
        return 1
    fi
    
    # Check .env file
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ .env file missing${NC}"
        return 1
    fi
    
    # Test Python in virtual environment
    if ! source venv/bin/activate && python -c "import aiohttp, fastapi, openai, binance" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Some dependencies may be missing${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Setup verification passed${NC}"
    return 0
}

# Display next steps
show_next_steps() {
    echo
    echo -e "${GREEN}🎉 SETUP COMPLETE!${NC}"
    echo "=============================================="
    echo
    echo -e "${PURPLE}📋 NEXT STEPS:${NC}"
    echo
    echo -e "${CYAN}1️⃣  CONFIGURE API KEYS:${NC}"
    echo "   📝 Edit .env file with your API keys:"
    echo "   • OPENAI_API_KEY (required)"
    echo "   • BINANCE_TESTNET_API_KEY (for testing)"
    echo "   • BINANCE_LIVE_API_KEY (for live trading)"
    echo "   • COINGECKO_API_KEY (optional)"
    echo
    echo -e "${CYAN}2️⃣  ACTIVATE VIRTUAL ENVIRONMENT:${NC}"
    echo "   🐧 source venv/bin/activate"
    echo
    echo -e "${CYAN}3️⃣  TEST THE SETUP:${NC}"
    echo "   🧪 python3 validate_apis.py"
    echo
    echo -e "${CYAN}4️⃣  START USING:${NC}"
    echo "   📊 Dashboard: python3 dashboard_standalone.py"
    echo "   🤖 Trading Bot: python3 main.py"
    echo "   🔄 Single Test: python3 demo_single_cycle.py"
    echo
    echo -e "${YELLOW}📖 For detailed instructions, see:${NC}"
    echo "   • README.md"
    echo "   • USAGE_GUIDE.md"
    echo
    echo -e "${CYAN}🌐 Dashboard URL: http://127.0.0.1:8000${NC}"
    echo "=============================================="
    echo -e "${GREEN}🚀 Happy Trading! 📈${NC}"
}

# Main setup function
main() {
    print_banner
    
    # Check if running on supported system
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo -e "${YELLOW}⚠️  For Windows, please use: python3 setup.py${NC}"
        exit 1
    fi
    
    # Run setup steps
    check_python || exit 1
    create_venv || exit 1
    install_deps || exit 1
    setup_env || exit 1
    create_dirs || exit 1
    
    if verify_setup; then
        show_next_steps
        echo -e "${GREEN}✅ Setup completed successfully!${NC}"
    else
        echo -e "${YELLOW}⚠️  Setup completed with warnings${NC}"
        show_next_steps
    fi
}

# Handle Ctrl+C
trap 'echo -e "\n${RED}🛑 Setup interrupted by user${NC}"; exit 1' INT

# Run main function
main "$@" 