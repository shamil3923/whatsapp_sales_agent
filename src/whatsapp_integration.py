#!/usr/bin/env python3
"""
WhatsApp Business API Integration for Sales Agent
This module integrates the Sales Agent with WhatsApp using Meta's Cloud API
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import logging
import sys
import os
sys.path.append(os.path.dirname(__file__))

from sales_agent import get_sales_agent, get_ai_response
from conversation_memory import ConversationMemory

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# WhatsApp API Configuration
WHATSAPP_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN', 'sales_agent_verify_token')
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

class WhatsAppBot:
    def __init__(self):
        self.sales_agent = None
        self.memory = ConversationMemory()  # Initialize conversation memory system
    
    def get_agent(self):
        """Get or create sales agent instance"""
        if not self.sales_agent:
            self.sales_agent = get_sales_agent()
        return self.sales_agent
    
    def send_message(self, phone_number: str, message: str) -> bool:
        """Send message to WhatsApp user"""
        try:
            headers = {
                'Authorization': f'Bearer {WHATSAPP_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message}
            }
            
            response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False
    
    def send_template_message(self, phone_number: str, template_name: str = "hello_world"):
        """Send template message (for initial contact)"""
        try:
            headers = {
                'Authorization': f'Bearer {WHATSAPP_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en_US"}
                }
            }
            
            response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending template: {str(e)}")
            return False
    
    def process_message(self, phone_number: str, message: str) -> str:
        """Process incoming message with conversation memory and generate context-aware response"""
        try:
            # Add user message to memory
            self.memory.add_message(phone_number, "user", message)

            # Get conversation context
            conversation_context = self.memory.get_conversation_context(phone_number)

            # Detect message type and extract insights
            message_type, metadata = self._analyze_message(message)

            # Update user preferences based on message
            self._update_user_preferences(phone_number, message, message_type)

            # Create enhanced context with memory
            whatsapp_context = f"""
            [WhatsApp Sales Agent - Context-Aware Response]

            CONVERSATION CONTEXT:
            {conversation_context}

            CURRENT MESSAGE:
            User: {message}
            Message Type: {message_type}

            RESPONSE GUIDELINES:
            - Use conversation history to provide personalized responses
            - Reference previous interactions when relevant
            - Remember user preferences (currency, interests, etc.)
            - Keep responses WhatsApp-friendly (concise, emojis, clear formatting)
            - For returning users, acknowledge their return
            - For currency conversions, use their preferred currency when possible
            - End with a helpful question or suggestion based on their interests

            Generate a context-aware, personalized response:
            """

            # Get AI response
            response = get_ai_response(whatsapp_context)

            # Format response for WhatsApp
            formatted_response = self.format_for_whatsapp(response.content)

            # Add assistant response to memory
            self.memory.add_message(phone_number, "assistant", formatted_response, message_type, metadata)

            return formatted_response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "Sorry, I'm having trouble processing your request. Please try again! 🤖"
    
    def format_for_whatsapp(self, message: str) -> str:
        """Format message for WhatsApp display"""
        # Remove markdown formatting that doesn't work well in WhatsApp
        formatted = message.replace('**', '*')  # Bold formatting
        formatted = formatted.replace('###', '')  # Remove headers
        formatted = formatted.replace('##', '')
        formatted = formatted.replace('#', '')
        
        # Limit message length (WhatsApp has 4096 char limit)
        if len(formatted) > 4000:
            formatted = formatted[:3900] + "\n\n... (message truncated)\n\nAsk me for more details! 💬"
        
        return formatted

    def _analyze_message(self, message: str) -> tuple[str, dict]:
        """Analyze message type and extract metadata"""
        message_lower = message.lower()
        metadata = {}

        # Currency conversion detection
        currency_keywords = ['convert', 'exchange', 'usd', 'eur', 'gbp', 'jpy', 'currency', 'rate']
        if any(keyword in message_lower for keyword in currency_keywords):
            return "currency_conversion", {"detected_currencies": self._extract_currencies(message)}

        # Product inquiry detection
        product_keywords = ['laptop', 'phone', 'smartphone', 'computer', 'product', 'buy', 'price', 'cost']
        if any(keyword in message_lower for keyword in product_keywords):
            return "product_inquiry", {"detected_products": self._extract_products(message)}

        # Greeting detection
        greeting_keywords = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if any(keyword in message_lower for keyword in greeting_keywords):
            return "greeting", {}

        # Help/support detection
        help_keywords = ['help', 'support', 'assistance', 'problem', 'issue']
        if any(keyword in message_lower for keyword in help_keywords):
            return "support", {}

        return "general", {}

    def _extract_currencies(self, message: str) -> list:
        """Extract currency codes from message"""
        currencies = []
        currency_codes = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'INR', 'KRW']
        message_upper = message.upper()

        for code in currency_codes:
            if code in message_upper:
                currencies.append(code)

        return currencies

    def _extract_products(self, message: str) -> list:
        """Extract product mentions from message"""
        products = []
        product_terms = ['laptop', 'phone', 'smartphone', 'computer', 'tablet', 'headphones', 'charger']
        message_lower = message.lower()

        for term in product_terms:
            if term in message_lower:
                products.append(term)

        return products

    def _update_user_preferences(self, phone_number: str, message: str, message_type: str):
        """Update user preferences based on message content"""
        try:
            # Extract and update preferred currency
            currencies = self._extract_currencies(message)
            if currencies and message_type == "currency_conversion":
                # Use the first currency mentioned as preferred
                self.memory.update_user_preferences(phone_number, preferred_currency=currencies[0])

            # Add interests based on product inquiries
            if message_type == "product_inquiry":
                products = self._extract_products(message)
                for product in products:
                    self.memory.add_user_interest(phone_number, product)

            # Extract name if user introduces themselves
            if "my name is" in message.lower() or "i'm" in message.lower():
                name = self._extract_name(message)
                if name:
                    self.memory.update_user_preferences(phone_number, name=name)

        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")

    def _extract_name(self, message: str) -> str:
        """Extract name from user message"""
        message_lower = message.lower()

        # Simple name extraction patterns
        if "my name is" in message_lower:
            parts = message_lower.split("my name is")
            if len(parts) > 1:
                name_part = parts[1].strip().split()[0]
                return name_part.capitalize()

        if "i'm" in message_lower:
            parts = message_lower.split("i'm")
            if len(parts) > 1:
                name_part = parts[1].strip().split()[0]
                return name_part.capitalize()

        return None

# Initialize bot
whatsapp_bot = WhatsAppBot()

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook for WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return challenge
    else:
        logger.error("Webhook verification failed")
        return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")
        
        # Extract message data
        if 'entry' in data:
            for entry in data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        if 'value' in change and 'messages' in change['value']:
                            messages = change['value']['messages']
                            
                            for message in messages:
                                phone_number = message['from']
                                message_text = message.get('text', {}).get('body', '')
                                
                                if message_text:
                                    logger.info(f"Processing message from {phone_number}: {message_text}")
                                    
                                    # Process with Sales Agent
                                    response = whatsapp_bot.process_message(phone_number, message_text)
                                    
                                    # Send response
                                    whatsapp_bot.send_message(phone_number, response)
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/send-message', methods=['POST'])
def send_manual_message():
    """Manual endpoint to send messages (for testing)"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        message = data.get('message')
        
        if not phone_number or not message:
            return jsonify({"error": "phone_number and message required"}), 400
        
        success = whatsapp_bot.send_message(phone_number, message)
        
        if success:
            return jsonify({"status": "Message sent successfully"})
        else:
            return jsonify({"error": "Failed to send message"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/conversation/<phone_number>', methods=['GET'])
def get_conversation_history(phone_number):
    """Get conversation history for a specific user"""
    try:
        # Remove URL encoding
        phone_number = phone_number.replace('%2B', '+')

        session = whatsapp_bot.memory.get_or_create_session(phone_number)

        conversation_data = {
            "user_profile": {
                "phone_number": session.user_profile.phone_number,
                "name": session.user_profile.name,
                "preferred_currency": session.user_profile.preferred_currency,
                "interests": session.user_profile.interests,
                "total_interactions": session.user_profile.total_interactions,
                "last_interaction": session.user_profile.last_interaction
            },
            "messages": [
                {
                    "timestamp": msg.timestamp,
                    "role": msg.role,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "metadata": msg.metadata
                }
                for msg in session.messages[-20:]  # Last 20 messages
            ],
            "session_info": {
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "total_messages": len(session.messages)
            }
        }

        return jsonify(conversation_data)

    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/analytics/users', methods=['GET'])
def get_users_analytics():
    """Get analytics for all users"""
    try:
        users_summary = whatsapp_bot.memory.get_all_users_summary()

        analytics = {
            "total_users": len(users_summary),
            "users": users_summary,
            "summary": {
                "total_interactions": sum(user.get("total_interactions", 0) for user in users_summary),
                "active_users_24h": len([
                    user for user in users_summary
                    if user.get("last_interaction") and
                    (datetime.now() - datetime.fromisoformat(user["last_interaction"])).days < 1
                ]),
                "top_interests": _get_top_interests(users_summary)
            }
        }

        return jsonify(analytics)

    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def _get_top_interests(users_summary):
    """Get top user interests"""
    interest_count = {}
    for user in users_summary:
        for interest in user.get("interests", []):
            interest_count[interest] = interest_count.get(interest, 0) + 1

    return sorted(interest_count.items(), key=lambda x: x[1], reverse=True)[:5]

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "WhatsApp Sales Agent"
    })

if __name__ == '__main__':
    # Check required environment variables
    required_vars = ['WHATSAPP_ACCESS_TOKEN', 'WHATSAPP_PHONE_NUMBER_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        print("Please set the following environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        exit(1)

    logger.info("Starting WhatsApp Sales Agent...")

    # Get port from environment (Heroku sets PORT)
    port = int(os.environ.get('PORT', 5000))

    # Run in production or development mode
    debug_mode = os.environ.get('FLASK_ENV') == 'development'

    app.run(host='0.0.0.0', port=port, debug=debug_mode)
