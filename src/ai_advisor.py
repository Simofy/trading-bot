"""AI Advisor for cryptocurrency trading decisions."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import openai
from openai import AsyncOpenAI

from .logger import TradingLogger
from .technical_analysis import TechnicalAnalyzer


class AITradingAdvisor:
    """AI-powered trading advisor using OpenAI GPT models."""
    
    def __init__(self, config):
        self.config = config
        self.logger = TradingLogger(__name__)
        
        # Initialize custom OpenAI client to bypass compatibility issues
        if config.openai_api_key and config.openai_api_key.startswith('sk-'):
            try:
                self.openai_api_key = config.openai_api_key
                self.client = "custom_http"
                self.demo_mode = False
                self.logger.logger.info("✅ Connected to OpenAI API (custom HTTP client) - Real AI decisions enabled!")
            except Exception as e:
                self.logger.logger.warning(f"Failed to setup OpenAI client: {e} - falling back to demo mode")
                self.client = None
                self.demo_mode = True
        else:
            self.logger.logger.warning("No valid OpenAI API key found - running in demo mode")
            self.client = None
            self.demo_mode = True
        
        # Trading context and memory
        self.market_context = {}
        self.recent_decisions = []
        self.performance_history = []
        
        # Technical analysis integration
        self.technical_analyzer = TechnicalAnalyzer()
    
    async def get_trading_decision(self, market_data: Dict, portfolio_data: Dict, risk_metrics: Dict) -> Dict:
        """Get AI trading decision based on current market conditions."""
        try:
            # Update technical analysis with current market data
            await self._update_technical_analysis(market_data)
            
            # Generate comprehensive prompt with technical analysis
            prompt = self._create_trading_prompt(market_data, portfolio_data, risk_metrics)
            
            # Get AI response
            response = await self._query_ai(prompt)
            
            # Parse and validate decision
            decision = self._parse_ai_response(response)
            
            # Log the decision
            self.logger.log_ai_decision(prompt, response, decision)
            
            # Store decision for future context
            self._store_decision(decision, market_data)
            
            return decision
            
        except Exception as e:
            self.logger.log_error("get_trading_decision", e)
            return self._get_safe_decision()
    
    def _create_trading_prompt(self, market_data: Dict, portfolio_data: Dict, risk_metrics: Dict) -> str:
        """Create a comprehensive prompt for the AI trading advisor."""
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Build market analysis section
        market_analysis = self._format_market_data(market_data)
        
        # Build portfolio analysis section
        portfolio_analysis = self._format_portfolio_data(portfolio_data)
        
        # Build risk analysis section
        risk_analysis = self._format_risk_metrics(risk_metrics)
        
        # Recent performance context
        performance_context = self._format_performance_history()
        
        # Technical analysis context
        technical_analysis = self._format_technical_analysis(market_data)
        
        prompt = f"""
You are an expert cryptocurrency trading advisor with deep knowledge of market analysis, risk management, and quantitative trading strategies. You have access to real-time market data and must provide actionable trading recommendations.

CURRENT CONTEXT:
Time: {current_time}
Market Conditions: {market_analysis}
Portfolio Status: {portfolio_analysis}
Risk Metrics: {risk_analysis}
Technical Analysis: {technical_analysis}
Recent Performance: {performance_context}

TRADING PARAMETERS:
- Maximum portfolio risk per trade: {self.config.max_portfolio_risk * 100}%
- Stop loss threshold: {self.config.stop_loss_percentage * 100}%
- Take profit target: {self.config.take_profit_percentage * 100}%
- Maximum open positions: {self.config.max_open_positions}
- Supported assets: {', '.join(self.config.supported_symbols)}
- Base currency: {self.config.base_currency}

CRITICAL THINKING FRAMEWORK:
1. TECHNICAL ANALYSIS: Evaluate RSI, MACD, Bollinger Bands, trend strength, and momentum indicators
2. MARKET ANALYSIS: Analyze price trends, volume patterns, and market sentiment
3. RISK ASSESSMENT: Evaluate current portfolio exposure, correlation risks, and market volatility
4. OPPORTUNITY IDENTIFICATION: Look for high-probability setups with favorable risk/reward ratios
5. TIMING ANALYSIS: Consider technical signals, support/resistance levels, and momentum confluence
6. POSITION SIZING: Calculate optimal trade size based on risk management rules and signal strength

DECISION REQUIREMENTS:
Based on your analysis, provide ONE of the following actions:
- BUY: Recommend purchasing a specific cryptocurrency
- SELL: Recommend selling a current position
- HOLD: Maintain current positions
- CLOSE: Close a specific position due to risk or profit-taking

For BUY/SELL decisions, you must specify:
- Symbol (exact trading pair, e.g., "BTCUSDT")
- Percentage of available capital to use (1-100%)
- Confidence level (1-10)
- Reasoning (concise but comprehensive)
- Expected timeframe (short/medium/long term)

RESPONSE FORMAT (JSON only):
{{
    "action": "BUY/SELL/HOLD/CLOSE",
    "symbol": "SYMBOL or null",
    "allocation_percentage": number_or_null,
    "confidence": number_1_to_10,
    "reasoning": "your_analysis_and_reasoning",
    "timeframe": "short/medium/long",
    "stop_loss": number_or_null,
    "take_profit": number_or_null,
    "urgency": "low/medium/high"
}}

IMPORTANT CONSTRAINTS:
- Only trade symbols from the supported list
- Never exceed maximum risk parameters
- Consider current portfolio concentration
- Factor in recent trading performance
- Be conservative during high volatility periods
- Provide clear, actionable reasoning

Analyze the current situation and provide your recommendation:
"""
        return prompt
    
    def _format_market_data(self, market_data: Dict) -> str:
        """Format market data for the AI prompt."""
        formatted = []
        
        for symbol, data in market_data.items():
            price_change_24h = data.get('price_change_24h', 0)
            volume_24h = data.get('volume_24h', 0)
            
            formatted.append(
                f"{symbol}: ${data.get('price', 0):.4f} "
                f"({price_change_24h:+.2f}%), "
                f"Vol: ${volume_24h:,.0f}"
            )
        
        return " | ".join(formatted)
    
    def _format_portfolio_data(self, portfolio_data: Dict) -> str:
        """Format portfolio data for the AI prompt."""
        total_value = portfolio_data.get('total_value', 0)
        available_balance = portfolio_data.get('available_balance', 0)
        positions = portfolio_data.get('positions', {})
        
        position_summary = []
        for symbol, pos in positions.items():
            pnl = pos.get('unrealized_pnl', 0)
            position_summary.append(f"{symbol}: ${pos.get('value', 0):.2f} ({pnl:+.2f}%)")
        
        return (f"Total Value: ${total_value:.2f}, "
                f"Available: ${available_balance:.2f}, "
                f"Positions: {' | '.join(position_summary) if position_summary else 'None'}")
    
    def _format_risk_metrics(self, risk_metrics: Dict) -> str:
        """Format risk metrics for the AI prompt."""
        portfolio_risk = risk_metrics.get('portfolio_risk', 0)
        volatility = risk_metrics.get('avg_volatility', 0)
        correlation_risk = risk_metrics.get('correlation_risk', 0)
        
        return (f"Portfolio Risk: {portfolio_risk:.2f}%, "
                f"Avg Volatility: {volatility:.2f}%, "
                f"Correlation Risk: {correlation_risk:.2f}")
    
    def _format_performance_history(self) -> str:
        """Format recent performance history for context."""
        if not self.performance_history:
            return "No recent trading history"
        
        recent = self.performance_history[-5:]  # Last 5 trades
        wins = sum(1 for trade in recent if trade.get('pnl', 0) > 0)
        
        return f"Recent trades: {len(recent)}, Win rate: {wins/len(recent)*100:.1f}%"
    
    async def _update_technical_analysis(self, market_data: Dict):
        """Update technical analysis with current market data."""
        for symbol, data in market_data.items():
            price = data.get('price', 0)
            volume = data.get('volume_24h', 0)
            
            if price > 0:
                self.technical_analyzer.update_price_data(symbol, price, volume)
    
    def _format_technical_analysis(self, market_data: Dict) -> str:
        """Format technical analysis for AI prompt."""
        analysis_summary = []
        
        for symbol in market_data.keys():
            # Get technical indicators
            indicators = self.technical_analyzer.get_technical_indicators(symbol)
            signals = self.technical_analyzer.generate_trading_signals(symbol)
            
            # Format key indicators
            rsi = indicators.get("rsi", {}).get("rsi", 50)
            rsi_signal = indicators.get("rsi", {}).get("signal", "NEUTRAL")
            
            macd_trend = indicators.get("macd", {}).get("trend", "NEUTRAL")
            
            bb_position = indicators.get("bollinger_bands", {}).get("position", "NEUTRAL")
            
            trend_direction = indicators.get("trend_strength", {}).get("direction", "SIDEWAYS")
            trend_strength = indicators.get("trend_strength", {}).get("strength", 0)
            
            price_momentum = indicators.get("price_action", {}).get("momentum", "NEUTRAL")
            
            overall_signal = signals.get("overall_signal", "NEUTRAL")
            signal_strength = signals.get("strength", 0)
            bullish_factors = len(signals.get("bullish_factors", []))
            bearish_factors = len(signals.get("bearish_factors", []))
            
            analysis_summary.append(
                f"{symbol}: RSI {rsi:.1f}({rsi_signal}), MACD {macd_trend}, "
                f"BB {bb_position}, Trend {trend_direction}({trend_strength:.0f}%), "
                f"Momentum {price_momentum}, Signal {overall_signal}({signal_strength}%) "
                f"[+{bullish_factors}/-{bearish_factors}]"
            )
        
        return " | ".join(analysis_summary)
    
    async def _query_ai(self, prompt: str) -> str:
        """Query the AI model with retry logic."""
        
        if self.demo_mode:
            # Demo mode - simulate AI trading decisions
            return await self._get_demo_response()
        
        # Live OpenAI API mode using custom HTTP client
        for attempt in range(self.config.max_ai_retries):
            try:
                self.logger.logger.info(f"🤖 Querying live OpenAI GPT-4 (attempt {attempt + 1})...")
                
                # Use custom HTTP client to bypass library compatibility issues
                ai_response = await self._make_openai_request(prompt)
                
                self.logger.logger.info(f"✅ Received live AI response: {ai_response[:100]}...")
                return ai_response
                
            except Exception as e:
                self.logger.logger.warning(f"❌ Live AI query attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_ai_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.logger.error("🚨 All AI attempts failed, falling back to safe response")
                    return self._get_safe_response()
    
    async def _make_openai_request(self, prompt: str) -> str:
        """Make direct HTTP request to OpenAI API."""
        import aiohttp
        import json
        
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.ai_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional cryptocurrency trading advisor with deep expertise in technical analysis, fundamental analysis, and risk management. Always respond with valid JSON in the exact format requested. Your decisions should be based on sound trading principles and market analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.config.ai_temperature,
            "max_tokens": 500
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")
    
    async def _get_demo_response(self) -> str:
        """Generate demo AI responses for testing."""
        import random
        
        await asyncio.sleep(1)  # Simulate AI thinking time
        
        demo_responses = [
            '{"action": "BUY", "symbol": "BTCUSDT", "allocation_percentage": 5, "confidence": 7, "reasoning": "Bitcoin showing strong upward momentum with high volume. Technical indicators suggest potential breakout above resistance.", "timeframe": "medium", "stop_loss": 0.05, "take_profit": 0.10, "urgency": "medium"}',
            '{"action": "BUY", "symbol": "ETHUSDT", "allocation_percentage": 8, "confidence": 8, "reasoning": "Ethereum demonstrates solid fundamentals with upcoming upgrades. Market sentiment is bullish with strong developer activity.", "timeframe": "long", "stop_loss": 0.04, "take_profit": 0.12, "urgency": "medium"}',
            '{"action": "HOLD", "symbol": null, "allocation_percentage": null, "confidence": 5, "reasoning": "Current market conditions show mixed signals. High volatility suggests waiting for clearer trend confirmation before making new positions.", "timeframe": "short", "stop_loss": null, "take_profit": null, "urgency": "low"}'
        ]
        
        response = random.choice(demo_responses)
        self.logger.logger.info(f"Demo AI generated response: {response[:100]}...")
        return response
    
    def _get_safe_response(self) -> str:
        """Return a safe response when AI fails."""
        return '{"action": "HOLD", "symbol": null, "allocation_percentage": null, "confidence": 1, "reasoning": "AI service unavailable, maintaining conservative approach", "timeframe": "short", "stop_loss": null, "take_profit": null, "urgency": "low"}'
    
    def _parse_ai_response(self, response: str) -> Dict:
        """Parse and validate AI response."""
        try:
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:-3]
            elif response.startswith("```"):
                response = response[3:-3]
            
            decision = json.loads(response)
            
            # Validate required fields
            required_fields = ["action", "confidence", "reasoning"]
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate action
            valid_actions = ["BUY", "SELL", "HOLD", "CLOSE"]
            if decision["action"] not in valid_actions:
                raise ValueError(f"Invalid action: {decision['action']}")
            
            # Validate confidence
            confidence = decision["confidence"]
            if not isinstance(confidence, (int, float)) or confidence < 1 or confidence > 10:
                raise ValueError(f"Invalid confidence level: {confidence}")
            
            # Validate symbol for BUY/SELL actions
            if decision["action"] in ["BUY", "SELL"] and decision.get("symbol"):
                if decision["symbol"] not in self.config.supported_symbols:
                    raise ValueError(f"Unsupported symbol: {decision['symbol']}")
            
            return decision
            
        except Exception as e:
            self.logger.log_error("parse_ai_response", e)
            return self._get_safe_decision()
    
    def _get_safe_decision(self) -> Dict:
        """Return a safe default decision when AI fails."""
        return {
            "action": "HOLD",
            "symbol": None,
            "allocation_percentage": None,
            "confidence": 1,
            "reasoning": "AI advisor unavailable, maintaining current positions for safety",
            "timeframe": "short",
            "stop_loss": None,
            "take_profit": None,
            "urgency": "low"
        }
    
    def _store_decision(self, decision: Dict, market_data: Dict):
        """Store decision for future context and learning."""
        decision_record = {
            "timestamp": datetime.now(),
            "decision": decision,
            "market_conditions": {
                symbol: data.get("price") for symbol, data in market_data.items()
            }
        }
        
        self.recent_decisions.append(decision_record)
        
        # Keep only recent decisions (last 50)
        if len(self.recent_decisions) > 50:
            self.recent_decisions = self.recent_decisions[-50:]
    
    def update_performance(self, trade_result: Dict):
        """Update performance history with trade results."""
        self.performance_history.append({
            "timestamp": datetime.now(),
            "symbol": trade_result.get("symbol"),
            "action": trade_result.get("action"),
            "pnl": trade_result.get("pnl", 0),
            "success": trade_result.get("pnl", 0) > 0
        })
        
        # Keep only recent performance (last 100 trades)
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:] 