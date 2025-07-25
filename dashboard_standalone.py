#!/usr/bin/env python3
"""
Standalone Dashboard Launcher
Launch the trading bot dashboard independently - reads data from database/files
No need for the trading bot to be running!
"""
import asyncio
import webbrowser
from datetime import datetime

from src.dashboard import start_dashboard
from src.logger import setup_logger

async def launch_standalone_dashboard():
    """Launch the dashboard without a bot instance."""
    
    print("🌐 AI TRADING BOT - STANDALONE DASHBOARD")
    print("━" * 70)
    print("📊 Starting independent monitoring dashboard")
    print("🗄️ Reading data from: Database & JSON files")
    print("⚡ Real-time market data from CoinGecko")
    print("🔄 Updates automatically every 30 seconds")
    print("━" * 70)
    
    try:
        # Setup logging
        setup_logger()
        
        print("🚀 Initializing standalone dashboard...")
        print("✅ No trading bot instance required!")
        print("🌐 Starting web dashboard server...")
        
        # Start dashboard server without bot instance
        dashboard_url = "http://127.0.0.1:8000"
        print(f"📊 Dashboard will be available at: {dashboard_url}")
        print("💡 The dashboard will open automatically in your browser")
        print("🛑 Press Ctrl+C to stop the dashboard")
        print("")
        print("📋 Dashboard Features:")
        print("   • 📈 Portfolio tracking from database")
        print("   • 🧠 AI decision history")
        print("   • 📊 Performance analytics")
        print("   • ⚡ Real-time market data")
        print("   • 🔄 Manual trade queueing (when bot offline)")
        print("   • 📱 Mobile-responsive interface")
        print("━" * 70)
        
        # Try to open browser after a short delay
        async def open_browser():
            await asyncio.sleep(3)  # Wait for server to start
            try:
                webbrowser.open(dashboard_url)
                print("🌐 Dashboard opened in your default browser")
            except Exception as e:
                print(f"⚠️ Could not auto-open browser: {e}")
                print(f"📋 Please manually open: {dashboard_url}")
        
        # Start browser opening task
        asyncio.create_task(open_browser())
        
        # Start the dashboard (this will run indefinitely)
        await start_dashboard(bot=None, host="127.0.0.1", port=8000)
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Dashboard failed to start: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔄 Starting standalone dashboard...")
    asyncio.run(launch_standalone_dashboard()) 