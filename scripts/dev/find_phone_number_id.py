#!/usr/bin/env python3
"""
Find WhatsApp Phone Number ID using Meta API
This script helps you find your Phone Number ID using your access token
"""

import requests
import json
from dotenv import load_dotenv
import os

def find_phone_number_id():
    """Find Phone Number ID using the access token"""
    load_dotenv()
    
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    
    if not access_token or 'PASTE_' in access_token:
        print("❌ Access token not found in .env file")
        return
    
    print("🔍 Finding your WhatsApp Phone Number ID...")
    print("=" * 50)
    
    # Try to get WhatsApp Business Account ID first
    try:
        # Get business accounts
        url = "https://graph.facebook.com/v18.0/me/businesses"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            businesses = response.json().get('data', [])
            print(f"✅ Found {len(businesses)} business account(s)")
            
            for business in businesses:
                business_id = business['id']
                business_name = business.get('name', 'Unknown')
                print(f"   Business: {business_name} (ID: {business_id})")
                
                # Get WhatsApp Business Accounts for this business
                waba_url = f"https://graph.facebook.com/v18.0/{business_id}/owned_whatsapp_business_accounts"
                waba_response = requests.get(waba_url, headers=headers, timeout=10)
                
                if waba_response.status_code == 200:
                    wabas = waba_response.json().get('data', [])
                    print(f"   Found {len(wabas)} WhatsApp Business Account(s)")
                    
                    for waba in wabas:
                        waba_id = waba['id']
                        waba_name = waba.get('name', 'Unknown')
                        print(f"     WABA: {waba_name} (ID: {waba_id})")
                        
                        # Get phone numbers for this WABA
                        phone_url = f"https://graph.facebook.com/v18.0/{waba_id}/phone_numbers"
                        phone_response = requests.get(phone_url, headers=headers, timeout=10)
                        
                        if phone_response.status_code == 200:
                            phones = phone_response.json().get('data', [])
                            print(f"       Found {len(phones)} phone number(s):")
                            
                            for phone in phones:
                                phone_id = phone['id']
                                phone_number = phone.get('display_phone_number', 'Unknown')
                                status = phone.get('verified_name', 'Unknown')
                                
                                print(f"         📱 Phone: {phone_number}")
                                print(f"         🆔 Phone Number ID: {phone_id}")
                                print(f"         ✅ Status: {status}")
                                print()
                                
                                # This is what you need!
                                print("🎯 USE THIS PHONE NUMBER ID:")
                                print(f"   WHATSAPP_PHONE_NUMBER_ID=\"{phone_id}\"")
                                print()
                                
                                return phone_id
        else:
            print(f"❌ Error getting businesses: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    return None

def test_phone_number_id(phone_id):
    """Test if the phone number ID works"""
    load_dotenv()
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    
    print(f"🧪 Testing Phone Number ID: {phone_id}")
    print("=" * 50)
    
    try:
        url = f"https://graph.facebook.com/v18.0/{phone_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Phone Number ID is valid!")
            print(f"   Display Number: {data.get('display_phone_number', 'N/A')}")
            print(f"   Verified Name: {data.get('verified_name', 'N/A')}")
            print(f"   Status: {data.get('code_verification_status', 'N/A')}")
            return True
        else:
            print(f"❌ Invalid Phone Number ID: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Phone Number ID: {str(e)}")
        return False

def main():
    """Main function"""
    print("🚀 WhatsApp Phone Number ID Finder")
    print("=" * 60)
    
    # Find Phone Number ID
    phone_id = find_phone_number_id()
    
    if phone_id:
        # Test it
        if test_phone_number_id(phone_id):
            print("\n" + "=" * 60)
            print("🎉 SUCCESS! Your Phone Number ID is working.")
            print("\n📝 Next steps:")
            print("1. Copy the Phone Number ID above")
            print("2. Update your .env file:")
            print(f'   WHATSAPP_PHONE_NUMBER_ID="{phone_id}"')
            print("3. Run: python verify_meta_setup.py")
            print("4. Test your WhatsApp bot!")
        else:
            print("\n❌ Phone Number ID found but not working properly.")
    else:
        print("\n❌ Could not find Phone Number ID automatically.")
        print("\n💡 Manual method:")
        print("1. Go to developers.facebook.com")
        print("2. Select your app → WhatsApp → Getting Started")
        print("3. Look for 'From phone number ID' - copy that number")
        print("4. Update your .env file with that number")

if __name__ == "__main__":
    main()
