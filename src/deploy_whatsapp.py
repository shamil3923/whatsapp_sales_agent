#!/usr/bin/env python3
"""
WhatsApp Integration Deployment Helper
Helps set up and deploy the WhatsApp integration
"""

import os
import subprocess
import sys
from dotenv import load_dotenv

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking Environment Configuration...")
    
    load_dotenv()
    
    # Check Google API
    google_api = os.getenv('GOOGLE_API_KEY')
    print(f"✅ Google API Key: {'Configured' if google_api else '❌ Missing'}")
    
    # Check WhatsApp API
    whatsapp_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    whatsapp_phone = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    print(f"📱 WhatsApp Token: {'Configured' if whatsapp_token and 'your_' not in whatsapp_token else '❌ Missing'}")
    print(f"📱 WhatsApp Phone ID: {'Configured' if whatsapp_phone and 'your_' not in whatsapp_phone else '❌ Missing'}")
    
    # Check Twilio API
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
    print(f"📞 Twilio SID: {'Configured' if twilio_sid and 'your_' not in twilio_sid else '❌ Missing'}")
    print(f"📞 Twilio Token: {'Configured' if twilio_token and 'your_' not in twilio_token else '❌ Missing'}")
    
    return {
        'google': bool(google_api),
        'whatsapp': bool(whatsapp_token and 'your_' not in whatsapp_token),
        'twilio': bool(twilio_sid and 'your_' not in twilio_sid)
    }

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing Dependencies...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def test_sales_agent():
    """Test if sales agent is working"""
    print("\n🤖 Testing Sales Agent...")
    
    try:
        from sales_agent import get_sales_agent
        agent = get_sales_agent()
        print("✅ Sales Agent loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Sales Agent error: {e}")
        return False

def create_procfile():
    """Create Procfile for Heroku deployment"""
    print("\n📄 Creating Procfile for deployment...")
    
    procfile_content = """web: python whatsapp_integration.py
twilio: python twilio_whatsapp_integration.py"""
    
    with open('Procfile', 'w') as f:
        f.write(procfile_content)
    
    print("✅ Procfile created")

def create_runtime_txt():
    """Create runtime.txt for Heroku"""
    print("📄 Creating runtime.txt...")
    
    python_version = f"python-{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    with open('runtime.txt', 'w') as f:
        f.write(python_version)
    
    print(f"✅ runtime.txt created with {python_version}")

def show_deployment_instructions(config):
    """Show deployment instructions based on configuration"""
    print("\n🚀 Deployment Instructions")
    print("=" * 50)
    
    if config['whatsapp']:
        print("\n📱 Meta WhatsApp Business API:")
        print("1. Deploy to Heroku/Railway/DigitalOcean")
        print("2. Set webhook URL: https://your-domain.com/webhook")
        print("3. Run: python whatsapp_integration.py")
        print("4. Port: 5000")
    
    if config['twilio']:
        print("\n📞 Twilio WhatsApp API:")
        print("1. Deploy to any hosting service")
        print("2. Set webhook URL: https://your-domain.com/twilio-webhook")
        print("3. Run: python twilio_whatsapp_integration.py")
        print("4. Port: 5001")
    
    if not config['whatsapp'] and not config['twilio']:
        print("\n⚠️  No WhatsApp API configured!")
        print("Please update your .env file with either:")
        print("- WhatsApp Business API credentials, OR")
        print("- Twilio WhatsApp API credentials")

def show_testing_commands():
    """Show testing commands"""
    print("\n🧪 Testing Commands")
    print("=" * 50)
    
    print("\n1. Test integration locally:")
    print("   python test_whatsapp_integration.py")
    
    print("\n2. Test sales agent:")
    print("   python currency_demo.py")
    
    print("\n3. Run WhatsApp webhook (Meta):")
    print("   python whatsapp_integration.py")
    
    print("\n4. Run Twilio webhook:")
    print("   python twilio_whatsapp_integration.py")
    
    print("\n5. Test with ngrok (local public URL):")
    print("   ngrok http 5000")

def main():
    """Main deployment helper"""
    print("🚀 WhatsApp Sales Agent Deployment Helper")
    print("=" * 60)
    
    # Check environment
    config = check_environment()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Deployment failed - dependency installation error")
        return
    
    # Test sales agent
    if not test_sales_agent():
        print("❌ Deployment failed - sales agent error")
        return
    
    # Create deployment files
    create_procfile()
    create_runtime_txt()
    
    # Show instructions
    show_deployment_instructions(config)
    show_testing_commands()
    
    print("\n" + "=" * 60)
    print("✅ Deployment preparation complete!")
    print("\n📋 Summary:")
    print(f"   - Google API: {'✅' if config['google'] else '❌'}")
    print(f"   - WhatsApp API: {'✅' if config['whatsapp'] else '❌'}")
    print(f"   - Twilio API: {'✅' if config['twilio'] else '❌'}")
    print(f"   - Dependencies: ✅")
    print(f"   - Sales Agent: ✅")
    
    if config['whatsapp'] or config['twilio']:
        print("\n🎉 Ready to deploy! Choose your hosting platform and follow the instructions above.")
    else:
        print("\n⚠️  Please configure WhatsApp API credentials in .env file first.")

if __name__ == "__main__":
    main()
