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
                self.logger.info(f"Starting trading cycle #{cycle_count}")
                await self.bot.run_cycle()
                
                # Log completion and wait for next cycle
                interval_minutes = self.bot.config.trading_interval // 60
                self.logger.info(f"Cycle #{cycle_count} completed. Next cycle in {interval_minutes} minutes.")
                
                # Wait for next cycle without countdown spam
                try:
                    await asyncio.sleep(self.bot.config.trading_interval)
                except asyncio.CancelledError:
                    break
                
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
            try:
                # Shutdown with overall timeout to prevent hanging
                await asyncio.wait_for(self.bot.shutdown(), timeout=10.0)
            except asyncio.TimeoutError:
                self.logger.warning("Bot shutdown timed out after 10 seconds")
            except Exception as e:
                self.logger.error(f"Error during bot shutdown: {e}")
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