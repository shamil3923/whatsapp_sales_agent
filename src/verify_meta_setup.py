#!/usr/bin/env python3
"""
Meta WhatsApp API Setup Verification
Test your Meta WhatsApp Business API credentials and setup
"""

import os
import requests
import json
from dotenv import load_dotenv

def check_credentials():
    """Check if Meta WhatsApp credentials are configured"""
    load_dotenv()
    
    token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    print("🔍 Checking Meta WhatsApp Credentials...")
    print("=" * 50)
    
    if not token or 'your_' in token or 'PASTE_' in token:
        print("❌ WHATSAPP_ACCESS_TOKEN not configured")
        print("   Please update your .env file with the permanent access token from Meta")
        return False, None, None
    else:
        print(f"✅ Access Token: Configured ({token[:20]}...)")
    
    if not phone_id or 'your_' in phone_id or 'PASTE_' in phone_id:
        print("❌ WHATSAPP_PHONE_NUMBER_ID not configured")
        print("   Please update your .env file with your Phone Number ID from Meta")
        return False, None, None
    else:
        print(f"✅ Phone Number ID: {phone_id}")
    
    return True, token, phone_id

def test_api_connection(token, phone_id):
    """Test connection to Meta WhatsApp API"""
    print("\n🌐 Testing API Connection...")
    print("=" * 50)
    
    # Test API endpoint
    url = f"https://graph.facebook.com/v18.0/{phone_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Connection: Success")
            print(f"   Phone Number: {data.get('display_phone_number', 'N/A')}")
            print(f"   Status: {data.get('verified_name', 'N/A')}")
            return True
        else:
            print(f"❌ API Connection Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error: {str(e)}")
        return False

def test_webhook_endpoint():
    """Test if webhook endpoint is accessible"""
    print("\n🔗 Testing Webhook Endpoint...")
    print("=" * 50)
    
    try:
        # Test local webhook
        response = requests.get('http://localhost:5000/health', timeout=5)
        
        if response.status_code == 200:
            print("✅ Local Webhook: Running")
            data = response.json()
            print(f"   Status: {data.get('status', 'N/A')}")
            print(f"   Service: {data.get('service', 'N/A')}")
            return True
        else:
            print(f"❌ Local Webhook Error: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException:
        print("❌ Local Webhook: Not running")
        print("   Start it with: python whatsapp_integration.py")
        return False

def test_webhook_verification():
    """Test webhook verification"""
    print("\n✅ Testing Webhook Verification...")
    print("=" * 50)
    
    verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'sales_agent_verify_token')
    
    try:
        url = f"http://localhost:5000/webhook"
        params = {
            'hub.mode': 'subscribe',
            'hub.verify_token': verify_token,
            'hub.challenge': 'test_challenge_123'
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200 and response.text == 'test_challenge_123':
            print("✅ Webhook Verification: Success")
            print(f"   Verify Token: {verify_token}")
            return True
        else:
            print(f"❌ Webhook Verification Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Webhook Verification Error: {str(e)}")
        return False

def send_test_message(token, phone_id, test_number):
    """Send a test message"""
    print(f"\n📱 Sending Test Message to {test_number}...")
    print("=" * 50)
    
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": test_number,
        "type": "text",
        "text": {
            "body": "🤖 Hello! This is a test message from your Sales Agent. The WhatsApp integration is working! Try asking me: 'Convert $100 to EUR'"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            message_id = data.get('messages', [{}])[0].get('id', 'N/A')
            print("✅ Test Message Sent Successfully!")
            print(f"   Message ID: {message_id}")
            print(f"   To: {test_number}")
            return True
        else:
            print(f"❌ Failed to Send Message: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error: {str(e)}")
        return False

def main():
    """Main verification function"""
    print("🚀 Meta WhatsApp Business API Setup Verification")
    print("=" * 60)
    
    # Check credentials
    creds_ok, token, phone_id = check_credentials()
    if not creds_ok:
        print("\n❌ Setup incomplete. Please configure your credentials first.")
        print("\n📋 Next steps:")
        print("1. Get your credentials from Meta Developer Console")
        print("2. Update the .env file with your actual values")
        print("3. Run this script again")
        return
    
    # Test API connection
    api_ok = test_api_connection(token, phone_id)
    
    # Test webhook
    webhook_ok = test_webhook_endpoint()
    webhook_verify_ok = test_webhook_verification() if webhook_ok else False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Verification Summary:")
    print(f"   ✅ Credentials: {'✅' if creds_ok else '❌'}")
    print(f"   ✅ API Connection: {'✅' if api_ok else '❌'}")
    print(f"   ✅ Webhook Running: {'✅' if webhook_ok else '❌'}")
    print(f"   ✅ Webhook Verification: {'✅' if webhook_verify_ok else '❌'}")
    
    if all([creds_ok, api_ok, webhook_ok, webhook_verify_ok]):
        print("\n🎉 All checks passed! Your setup is ready.")
        
        # Offer to send test message
        test_number = input("\n📱 Enter a phone number to send test message (with country code, e.g., +1234567890): ").strip()
        if test_number:
            send_test_message(token, phone_id, test_number.replace('+', ''))
        
        print("\n🔗 Next steps:")
        print("1. Deploy your webhook to a public URL (Heroku, Railway, etc.)")
        print("2. Configure the webhook URL in Meta Developer Console")
        print("3. Test with real WhatsApp messages")
        
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        
        if not webhook_ok:
            print("\n💡 To start the webhook:")
            print("   python whatsapp_integration.py")

if __name__ == "__main__":
    main()
