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
from sales_agent import get_sales_agent, get_ai_response

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
        self.user_sessions = {}  # Store user conversation context
    
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
        """Process incoming message with Sales Agent"""
        try:
            # Add context for WhatsApp
            whatsapp_context = f"""
            [WhatsApp Message from {phone_number}]
            User Message: {message}
            
            Please respond in a WhatsApp-friendly format:
            - Keep responses concise but informative
            - Use emojis appropriately
            - Break long responses into shorter paragraphs
            - For currency conversions, format clearly
            - End with a helpful question or suggestion
            """
            
            # Get AI response
            response = get_ai_response(whatsapp_context)
            
            # Format response for WhatsApp
            formatted_response = self.format_for_whatsapp(response.content)
            
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
