#!/usr/bin/env python3
"""
Cryptocurrency Trading Bot with AI Decision Making
Main entry point for the trading bot application.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from src.trading_bot import TradingBot
from src.config import Config
from src.logger import setup_logger


class BotRunner:
    """Main bot runner class that handles initialization and lifecycle."""
    
    def __init__(self):
        self.bot: Optional[TradingBot] = None
        self.running = False
        
    async def initialize(self):
        """Initialize the trading bot and all its components."""
        try:
            # Setup logging
            print("Setting up logging...")
            setup_logger()
            self.logger = logging.getLogger(__name__)
            
            # Load configuration
            print("Loading configuration...")
            config = Config()
            
            # Initialize trading bot
            print("Creating trading bot...")
            self.bot = TradingBot(config)
            
            print("Initializing bot components...")
            await self.bot.initialize()
            
            self.logger.info("Trading bot initialized successfully")
            return True
            
        except Exception as e:
            import traceback
            print(f"Failed to initialize bot: {e}")
            print("Traceback:")
            traceback.print_exc()
            return False
    
    async def run(self):
        """Main bot execution loop."""
        if not self.bot:
            raise RuntimeError("Bot not initialized")
            
        self.running = True
        self.logger.info("Starting trading bot main loop")
        
        cycle_count = 0
        
        try:
            while self.running:
                cycle_count += 1
                
                # Run one trading cycle
                print(f"\n🔄 === TRADING CYCLE #{cycle_count} ===")
                await self.bot.run_cycle()
                
                # Show completion and next cycle info
                interval_minutes = self.bot.config.trading_interval // 60
                print(f"\n✅ Cycle #{cycle_count} completed!")
                print(f"⏰ Waiting {interval_minutes} minutes until next cycle...")
                print(f"💡 Press Ctrl+C to stop the bot")
                print("━" * 50)
                
                # Wait with countdown for next cycle
                for remaining in range(self.bot.config.trading_interval, 0, -10):
                    if not self.running:
                        break
                    
                    minutes = remaining // 60
                    seconds = remaining % 60
                    print(f"⏳ Next cycle in: {minutes:02d}:{seconds:02d}", end="\r", flush=True)
                    
                    try:
                        await asyncio.sleep(10)  # Update every 10 seconds
                    except asyncio.CancelledError:
                        break
                
                print()  # New line after countdown
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
            print("\n🛑 Shutting down bot...")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
            print(f"\n❌ Error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shutdown the bot."""
        self.running = False
        if self.bot:
            await self.bot.shutdown()
        self.logger.info("Bot shutdown complete")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False


async def main():
    """Main application entry point."""
    runner = BotRunner()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, runner.signal_handler)
    signal.signal(signal.SIGTERM, runner.signal_handler)
    
    # Initialize and run
    if await runner.initialize():
        await runner.run()
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1) 