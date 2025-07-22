"""
Simple webhook test to verify WhatsApp connection
"""
import os
import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# WhatsApp configuration
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook for WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ Webhook verified successfully!")
        return challenge
    else:
        logger.error("❌ Webhook verification failed!")
        return 'Verification failed', 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        logger.info(f"📨 Received webhook data: {json.dumps(data, indent=2)}")
        
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
                                
                                logger.info(f"📱 Message from {phone_number}: {message_text}")
                                
                                # Send simple test response
                                response_text = f"🤖 Hello! I received your message: '{message_text}'\n\n✅ Webhook is working!\n🧠 Memory system is active!\n⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                                
                                success = send_message(phone_number, response_text)
                                
                                if success:
                                    logger.info(f"✅ Response sent successfully to {phone_number}")
                                else:
                                    logger.error(f"❌ Failed to send response to {phone_number}")
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error handling webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

def send_message(phone_number: str, message: str) -> bool:
    """Send message via WhatsApp API"""
    try:
        headers = {
            'Authorization': f'Bearer {WHATSAPP_ACCESS_TOKEN}',
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
            logger.info(f"✅ Message sent successfully: {response.json()}")
            return True
        else:
            logger.error(f"❌ Failed to send message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending message: {str(e)}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "WhatsApp Webhook Test"
    })

if __name__ == '__main__':
    # Check required environment variables
    required_vars = ['WHATSAPP_ACCESS_TOKEN', 'WHATSAPP_PHONE_NUMBER_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        exit(1)
    
    logger.info("🚀 Starting WhatsApp Webhook Test...")
    logger.info(f"📱 Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
    logger.info(f"🔗 Webhook URL: https://your-ngrok-url.ngrok-free.app/webhook")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
