#!/usr/bin/env python3
"""
AI Trading Bot - Project Setup Script
=====================================
Automatically sets up the trading bot environment, installs dependencies,
and prepares the project for use.

Usage: python3 setup.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

class TradingBotSetup:
    """Setup manager for the AI Trading Bot project."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.venv_path = self.project_root / "venv"
        self.requirements_file = self.project_root / "requirements.txt"
        self.env_example = self.project_root / ".env.example"
        self.env_file = self.project_root / ".env"
        
    def print_banner(self):
        """Display setup banner."""
        print("🚀 AI TRADING BOT - SETUP SCRIPT")
        print("=" * 60)
        print("🤖 Automated project initialization")
        print("📦 Dependency installation")
        print("🔧 Configuration setup")
        print("=" * 60)
        print()
        
    def check_python_version(self):
        """Check if Python 3.8+ is available."""
        print("🐍 Checking Python version...")
        
        python_version = sys.version_info
        if python_version.major != 3 or python_version.minor < 8:
            print(f"❌ Python 3.8+ required. Found: {python_version.major}.{python_version.minor}")
            print("💡 Please install Python 3.8 or newer")
            return False
        
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro} detected")
        return True
    
    def create_virtual_environment(self):
        """Create and activate virtual environment."""
        print("\n🌐 Setting up virtual environment...")
        
        if self.venv_path.exists():
            print("⚠️  Virtual environment already exists")
            response = input("🔄 Recreate virtual environment? (y/n): ").lower()
            if response == 'y':
                print("🗑️  Removing existing virtual environment...")
                shutil.rmtree(self.venv_path)
            else:
                print("✅ Using existing virtual environment")
                return True
        
        try:
            print("📦 Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], 
                         check=True, capture_output=True)
            print("✅ Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    
    def get_pip_path(self):
        """Get the pip executable path for the virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "pip"
        else:  # Unix/Linux/macOS
            return self.venv_path / "bin" / "pip"
    
    def install_dependencies(self):
        """Install required dependencies."""
        print("\n📦 Installing dependencies...")
        
        pip_path = self.get_pip_path()
        
        if not pip_path.exists():
            print("❌ Virtual environment not properly created")
            return False
        
        if not self.requirements_file.exists():
            print("❌ requirements.txt not found")
            return False
        
        try:
            print("⬇️  Installing packages from requirements.txt...")
            subprocess.run([str(pip_path), "install", "-r", str(self.requirements_file)], 
                         check=True)
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    def setup_environment_file(self):
        """Create .env file from template."""
        print("\n🔧 Setting up environment configuration...")
        
        if self.env_file.exists():
            print("⚠️  .env file already exists")
            response = input("🔄 Overwrite existing .env file? (y/n): ").lower()
            if response != 'y':
                print("✅ Keeping existing .env file")
                return True
        
        if not self.env_example.exists():
            print("❌ .env.example template not found")
            return False
        
        try:
            shutil.copy2(self.env_example, self.env_file)
            print("✅ .env file created from template")
            print("⚠️  IMPORTANT: Update .env with your actual API keys!")
            return True
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    
    def create_directories(self):
        """Create necessary directories."""
        print("\n📁 Creating project directories...")
        
        directories = [
            "logs",
            "cache", 
            "temp"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"📂 Created: {directory}/")
            else:
                print(f"✅ Exists: {directory}/")
        
        return True
    
    def verify_setup(self):
        """Verify the setup is working."""
        print("\n🔍 Verifying setup...")
        
        # Check virtual environment
        if not self.venv_path.exists():
            print("❌ Virtual environment missing")
            return False
        
        # Check .env file
        if not self.env_file.exists():
            print("❌ .env file missing")
            return False
        
        # Check Python executable in venv
        if os.name == 'nt':
            python_path = self.venv_path / "Scripts" / "python"
        else:
            python_path = self.venv_path / "bin" / "python"
        
        if not python_path.exists():
            print("❌ Python executable missing in virtual environment")
            return False
        
        try:
            # Test import of key modules
            result = subprocess.run([
                str(python_path), "-c", 
                "import aiohttp, fastapi, openai, python_binance; print('✅ Key modules available')"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ All key dependencies verified")
                return True
            else:
                print("❌ Some dependencies may be missing")
                print(f"Error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Verification timed out")
            return False
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
    
    def display_next_steps(self):
        """Display what to do next."""
        print("\n🎉 SETUP COMPLETE!")
        print("=" * 60)
        print()
        print("📋 NEXT STEPS:")
        print()
        print("1️⃣  CONFIGURE API KEYS:")
        print("   📝 Edit .env file with your API keys:")
        print("   • OPENAI_API_KEY (required)")
        print("   • BINANCE_TESTNET_API_KEY (for testing)")
        print("   • BINANCE_LIVE_API_KEY (for live trading)")
        print("   • COINGECKO_API_KEY (optional)")
        print()
        print("2️⃣  ACTIVATE VIRTUAL ENVIRONMENT:")
        if os.name == 'nt':
            print("   🖥️  Windows: venv\\Scripts\\activate")
        else:
            print("   🐧 Unix/Mac: source venv/bin/activate")
        print()
        print("3️⃣  TEST THE SETUP:")
        print("   🧪 python3 validate_apis.py")
        print()
        print("4️⃣  START USING:")
        print("   📊 Dashboard: python3 dashboard_standalone.py")
        print("   🤖 Trading Bot: python3 main.py")
        print("   🔄 Single Test: python3 demo_single_cycle.py")
        print()
        print("📖 For detailed instructions, see:")
        print("   • README.md")
        print("   • USAGE_GUIDE.md")
        print()
        print("🌐 Dashboard URL: http://127.0.0.1:8000")
        print("=" * 60)
        print("🚀 Happy Trading! 📈")
    
    def run(self):
        """Run the complete setup process."""
        self.print_banner()
        
        # Step 1: Check Python version
        if not self.check_python_version():
            return False
        
        # Step 2: Create virtual environment
        if not self.create_virtual_environment():
            return False
        
        # Step 3: Install dependencies
        if not self.install_dependencies():
            return False
        
        # Step 4: Setup environment file
        if not self.setup_environment_file():
            return False
        
        # Step 5: Create directories
        if not self.create_directories():
            return False
        
        # Step 6: Verify setup
        if not self.verify_setup():
            print("⚠️  Setup completed with warnings")
        
        # Step 7: Display next steps
        self.display_next_steps()
        
        return True

def main():
    """Main setup function."""
    try:
        setup = TradingBotSetup()
        success = setup.run()
        
        if success:
            print("\n✅ Setup completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Setup failed!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 