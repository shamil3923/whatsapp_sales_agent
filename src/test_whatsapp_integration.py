#!/usr/bin/env python3
"""
WhatsApp Integration Test Script
Test the Sales Agent WhatsApp integration locally
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from whatsapp_integration import WhatsAppBot
from twilio_whatsapp_integration import TwilioWhatsAppBot
import json

def test_message_processing():
    """Test message processing with Sales Agent"""
    print("🧪 Testing WhatsApp Message Processing")
    print("=" * 50)
    
    # Test messages
    test_messages = [
        "Hello! What products do you have?",
        "Convert $1000 to EUR",
        "What are the current exchange rates?",
        "Show me laptop prices in different currencies",
        "Compare iPhone 15 Pro with Samsung Galaxy S24",
        "What's the price of MacBook Pro in British pounds?"
    ]
    
    # Test with Meta WhatsApp Bot
    print("\n📱 Testing Meta WhatsApp Bot:")
    meta_bot = WhatsAppBot()
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        print(f"User: {message}")
        
        try:
            response = meta_bot.process_message("+1234567890", message)
            print(f"Bot: {response[:200]}..." if len(response) > 200 else f"Bot: {response}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # Test with Twilio Bot
    print("\n\n📞 Testing Twilio WhatsApp Bot:")
    twilio_bot = TwilioWhatsAppBot()
    
    for i, message in enumerate(test_messages[:3], 1):  # Test fewer for brevity
        print(f"\n--- Test {i} ---")
        print(f"User: {message}")
        
        try:
            response = twilio_bot.process_message("+1234567890", message)
            print(f"Bot: {response[:200]}..." if len(response) > 200 else f"Bot: {response}")
        except Exception as e:
            print(f"Error: {str(e)}")

def test_message_formatting():
    """Test WhatsApp message formatting"""
    print("\n\n🎨 Testing Message Formatting")
    print("=" * 50)
    
    # Test long message formatting
    long_message = """
    **Product Comparison Results:**
    
    ### iPhone 15 Pro vs Samsung Galaxy S24
    
    **iPhone 15 Pro:**
    - Display: 6.1" Super Retina XDR
    - Processor: A17 Pro chip
    - Camera: 48MP main, 12MP ultra-wide
    - Price: $999 USD
    
    **Samsung Galaxy S24:**
    - Display: 6.2" Dynamic AMOLED 2X
    - Processor: Snapdragon 8 Gen 3
    - Camera: 50MP main, 12MP ultra-wide
    - Price: $899 USD
    
    **Currency Conversions:**
    - iPhone: €857 EUR, £742 GBP
    - Samsung: €771 EUR, £668 GBP
    """
    
    meta_bot = WhatsAppBot()
    formatted = meta_bot.format_for_whatsapp(long_message)
    
    print("Original length:", len(long_message))
    print("Formatted length:", len(formatted))
    print("\nFormatted message:")
    print(formatted)

def test_currency_integration():
    """Test currency conversion integration"""
    print("\n\n💱 Testing Currency Conversion Integration")
    print("=" * 50)
    
    currency_tests = [
        "Convert 500 USD to EUR",
        "What's 1000 GBP in Japanese Yen?",
        "Show me current exchange rates",
        "Convert the iPhone price to Indian Rupees"
    ]
    
    meta_bot = WhatsAppBot()
    
    for test in currency_tests:
        print(f"\nTest: {test}")
        try:
            response = meta_bot.process_message("+1234567890", test)
            # Look for currency symbols and numbers in response
            has_currency = any(symbol in response for symbol in ['$', '€', '£', '¥', '₹'])
            has_numbers = any(char.isdigit() for char in response)
            
            print(f"Response contains currency: {has_currency}")
            print(f"Response contains numbers: {has_numbers}")
            print(f"Response preview: {response[:150]}...")
            
        except Exception as e:
            print(f"Error: {str(e)}")

def test_webhook_simulation():
    """Simulate webhook data processing"""
    print("\n\n🔗 Testing Webhook Data Processing")
    print("=" * 50)
    
    # Simulate Meta webhook data
    meta_webhook_data = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "text": {"body": "Convert $500 to EUR"}
                    }]
                }
            }]
        }]
    }
    
    print("Simulated Meta webhook data:")
    print(json.dumps(meta_webhook_data, indent=2))
    
    # Extract message (simulate webhook processing)
    try:
        for entry in meta_webhook_data['entry']:
            for change in entry['changes']:
                if 'messages' in change['value']:
                    for message in change['value']['messages']:
                        phone = message['from']
                        text = message['text']['body']
                        print(f"\nExtracted - Phone: {phone}, Message: {text}")
    except Exception as e:
        print(f"Webhook processing error: {str(e)}")

def main():
    """Run all tests"""
    print("🚀 WhatsApp Integration Test Suite")
    print("=" * 60)
    
    try:
        test_message_processing()
        test_message_formatting()
        test_currency_integration()
        test_webhook_simulation()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("\n💡 Next steps:")
        print("1. Set up your WhatsApp API credentials in .env")
        print("2. Deploy the webhook to a public URL")
        print("3. Configure webhook in WhatsApp Business API")
        print("4. Test with real WhatsApp messages")
        
    except Exception as e:
        print(f"\n❌ Test suite error: {str(e)}")
        print("Make sure all dependencies are installed and the sales agent is working")

if __name__ == "__main__":
    main()
