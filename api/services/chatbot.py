"""
Gemini AI Chatbot Service
Provides intelligent responses about weather and electricity demand.
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import google.generativeai as genai

from .storage import get_storage_service
from .weather import get_weather_service
from .cache import get_redis_client

logger = logging.getLogger(__name__)


class VoltCastChatbot:
    """Intelligent chatbot for weather and electricity demand queries."""
    
    def __init__(self):
        """Initialize the chatbot with Gemini API."""
        # Configure Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'your_gemini_api_key_here':
            raise ValueError("GEMINI_API_KEY not configured in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Initialize Gemini model (using latest available model)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # Initialize services
        self.storage_service = get_storage_service()
        redis_client = get_redis_client()
        self.weather_service = get_weather_service(redis_client)
        
        logger.info("VoltCast Chatbot initialized with Gemini API")
    
    def _get_current_context(self) -> Dict[str, Any]:
        """Get current system context for the chatbot."""
        try:
            # Get latest demand data
            latest_data = self.storage_service.get_last_n_hours(24)
            current_demand = latest_data['demand'].iloc[-1] if len(latest_data) > 0 else None
            avg_demand_24h = latest_data['demand'].mean() if len(latest_data) > 0 else None
            
            # Get current weather
            current_weather = self.weather_service.get_weather_for_hours([datetime.now()])[0]
            
            # Get recent trends
            if len(latest_data) >= 24:
                demand_trend = "increasing" if latest_data['demand'].iloc[-1] > latest_data['demand'].iloc[-24] else "decreasing"
            else:
                demand_trend = "stable"
            
            return {
                "current_demand_mw": current_demand * 10 if current_demand else None,  # Apply 10x scaling
                "avg_demand_24h_mw": avg_demand_24h * 10 if avg_demand_24h else None,
                "current_temperature": current_weather.get('temperature'),
                "current_weather": current_weather.get('description', 'clear'),
                "humidity": current_weather.get('humidity'),
                "wind_speed": current_weather.get('wind_speed'),
                "cloud_cover": current_weather.get('cloud_cover'),
                "demand_trend": demand_trend,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"Could not get current context: {e}")
            return {
                "current_demand_mw": "unavailable",
                "current_temperature": "unavailable",
                "error": "Data temporarily unavailable"
            }
    
    def _create_system_prompt(self, context: Dict[str, Any]) -> str:
        """Create system prompt with current context."""
        return f"""You are VoltCast AI, an intelligent assistant for electricity demand forecasting in Delhi, India. 

CURRENT SYSTEM STATUS:
- Current electricity demand: {context.get('current_demand_mw', 'N/A')} MW
- 24-hour average demand: {context.get('avg_demand_24h_mw', 'N/A')} MW
- Current temperature: {context.get('current_temperature', 'N/A')}°C
- Weather conditions: {context.get('current_weather', 'N/A')}
- Humidity: {context.get('humidity', 'N/A')}%
- Demand trend: {context.get('demand_trend', 'N/A')}
- Last updated: {context.get('timestamp', 'N/A')}

KNOWLEDGE BASE:
- You specialize in electricity demand forecasting and weather impact analysis
- Delhi's typical demand ranges from 3,000-7,000 MW (scaled display values)
- Peak demand usually occurs during summer afternoons (12-4 PM) due to AC usage
- Weather factors affecting demand:
  * Temperature: Higher temps increase AC usage (cooling demand)
  * Humidity: High humidity increases perceived temperature and AC usage
  * Rain: Can reduce demand slightly due to cooling effect
  * Cloud cover: Reduces solar heating, may decrease AC demand
- Seasonal patterns:
  * Summer (Apr-Jun): Highest demand due to cooling
  * Winter (Dec-Feb): Moderate demand due to heating
  * Monsoon (Jul-Sep): Variable demand due to weather changes
- Daily patterns:
  * Morning peak: 8-10 AM (residential + commercial)
  * Evening peak: 6-9 PM (residential + commercial)
  * Night minimum: 2-5 AM

RESPONSE GUIDELINES:
- Provide specific, actionable insights about electricity demand
- Explain weather-demand relationships clearly
- Use the current context data in your responses
- Be conversational but informative
- If asked about predictions, mention that VoltCast uses SARIMAX models
- Always provide MW values in the scaled format (10x original)
- Keep responses concise but comprehensive (2-4 sentences)

Answer the user's question about weather and electricity demand:"""

    async def chat(self, user_message: str, conversation_history: Optional[list] = None) -> Dict[str, Any]:
        """
        Process user message and return chatbot response.
        
        Args:
            user_message: User's question/message
            conversation_history: Previous conversation context (optional)
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Get current system context
            context = self._get_current_context()
            
            # Create system prompt
            system_prompt = self._create_system_prompt(context)
            
            # Build conversation context
            if conversation_history:
                # Include recent conversation for context
                conversation_context = "\n".join([
                    f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}"
                    for msg in conversation_history[-3:]  # Last 3 exchanges
                ])
                full_prompt = f"{system_prompt}\n\nRECENT CONVERSATION:\n{conversation_context}\n\nUser: {user_message}\nAssistant:"
            else:
                full_prompt = f"{system_prompt}\n\nUser: {user_message}\nAssistant:"
            
            # Generate response using Gemini
            response = self.model.generate_content(full_prompt)
            
            # Extract response text
            response_text = response.text if response.text else "I'm sorry, I couldn't generate a response. Please try again."
            
            return {
                "response": response_text,
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "model": "gemini-2.5-flash",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Chatbot error: {e}", exc_info=True)
            return {
                "response": "I'm experiencing technical difficulties. Please try again in a moment.",
                "context": context if 'context' in locals() else {},
                "timestamp": datetime.now().isoformat(),
                "model": "gemini-2.5-flash",
                "success": False,
                "error": str(e)
            }
    
    def get_suggested_questions(self) -> list:
        """Get list of suggested questions for users."""
        return [
            "Why is the electricity demand so high today?",
            "How will rain tomorrow affect the power demand?",
            "What's the typical demand pattern during summer?",
            "How does temperature affect electricity usage?",
            "When is peak demand usually highest?",
            "What's the current demand trend?",
            "How accurate are the demand forecasts?",
            "What factors influence electricity demand the most?"
        ]


# Global chatbot instance
_chatbot_instance = None


def get_chatbot() -> VoltCastChatbot:
    """Get or create chatbot instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = VoltCastChatbot()
    return _chatbot_instance