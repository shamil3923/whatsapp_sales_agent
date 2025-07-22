# 📱 WhatsApp Integration Setup Guide

## Overview
This guide will help you integrate your Sales Agent with WhatsApp using two different approaches:
1. **Meta WhatsApp Business Cloud API** (Recommended - Free)
2. **Twilio WhatsApp API** (Alternative - Paid but easier)

## 🚀 Option 1: Meta WhatsApp Business Cloud API (FREE)

### Step 1: Create Meta Developer Account
1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create a developer account or log in
3. Create a new app → Business → WhatsApp

### Step 2: Get WhatsApp Business API Access
1. In your app dashboard, add "WhatsApp" product
2. Go to WhatsApp → Getting Started
3. Note down:
   - **Phone Number ID** (from the test number)
   - **Access Token** (temporary - 24 hours)

### Step 3: Generate Permanent Access Token
1. Go to WhatsApp → Configuration
2. Create a System User in Business Manager
3. Generate a permanent access token with `whatsapp_business_messaging` permission

### Step 4: Configure Webhook
1. Set webhook URL: `https://your-domain.com/webhook`
2. Set verify token: `sales_agent_verify_token`
3. Subscribe to `messages` field

### Step 5: Update Environment Variables
```bash
# In your .env file
WHATSAPP_ACCESS_TOKEN="your_permanent_access_token"
WHATSAPP_PHONE_NUMBER_ID="your_phone_number_id"
WHATSAPP_VERIFY_TOKEN="sales_agent_verify_token"
```

### Step 6: Run the Integration
```bash
# Install dependencies
pip install flask

# Run WhatsApp integration
python whatsapp_integration.py
```

### Step 7: Deploy to Production
Use services like:
- **Heroku**: Easy deployment with webhook support
- **Railway**: Modern deployment platform
- **DigitalOcean**: VPS with more control
- **ngrok**: For local testing with public URL

---

## 🔧 Option 2: Twilio WhatsApp API (PAID)

### Step 1: Create Twilio Account
1. Sign up at [twilio.com](https://www.twilio.com)
2. Get $15 free credit for testing
3. Go to Console → WhatsApp → Senders

### Step 2: Set Up WhatsApp Sandbox
1. Enable WhatsApp Sandbox
2. Note the sandbox number: `+1 415 523 8886`
3. Send "join [sandbox-name]" to the number from your WhatsApp

### Step 3: Get Credentials
1. Account SID (from Console Dashboard)
2. Auth Token (from Console Dashboard)
3. WhatsApp number: `whatsapp:+14155238886`

### Step 4: Configure Environment
```bash
# In your .env file
TWILIO_ACCOUNT_SID="your_account_sid"
TWILIO_AUTH_TOKEN="your_auth_token"
TWILIO_WHATSAPP_NUMBER="whatsapp:+14155238886"
```

### Step 5: Set Up Webhook
1. In Twilio Console → WhatsApp → Sandbox
2. Set webhook URL: `https://your-domain.com/twilio-webhook`
3. Method: POST

### Step 6: Run Twilio Integration
```bash
# Run Twilio WhatsApp integration
python twilio_whatsapp_integration.py
```

---

## 🧪 Testing Your Integration

### Test Meta WhatsApp API
```bash
# Send test message
curl -X POST http://localhost:5000/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "1234567890",
    "message": "Hello from Sales Agent!"
  }'
```

### Test Twilio API
```bash
# Send test message
curl -X POST http://localhost:5001/send-twilio-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "message": "Hello from Sales Agent!"
  }'
```

### Test Sales Agent Features
Send these messages to your WhatsApp bot:
- "Convert $500 to EUR"
- "What are current exchange rates?"
- "Show me laptop prices"
- "Compare iPhone models"

---

## 🌐 Deployment Options

### 1. Heroku (Easiest)
```bash
# Install Heroku CLI
# Create Procfile
echo "web: python whatsapp_integration.py" > Procfile

# Deploy
heroku create your-sales-agent
git push heroku main
```

### 2. Railway
```bash
# Install Railway CLI
railway login
railway init
railway up
```

### 3. Local Testing with ngrok
```bash
# Install ngrok
ngrok http 5000

# Use the https URL for webhook configuration
```

---

## 📊 Features Available via WhatsApp

### Sales Features
- ✅ Product recommendations
- ✅ Price comparisons
- ✅ Market insights
- ✅ Stock availability
- ✅ Technical specifications

### Currency Features
- ✅ Real-time currency conversion
- ✅ Exchange rate display
- ✅ Multi-currency pricing
- ✅ International sales support

### WhatsApp-Specific Features
- ✅ Message formatting for mobile
- ✅ Emoji support
- ✅ Character limit handling
- ✅ Quick response suggestions

---

## 🔧 Troubleshooting

### Common Issues

**Webhook not receiving messages:**
- Check webhook URL is publicly accessible
- Verify webhook token matches
- Check webhook subscription fields

**Messages not sending:**
- Verify access token is valid
- Check phone number format
- Ensure recipient has opted in

**Twilio sandbox limitations:**
- Only works with pre-approved numbers
- Limited to sandbox environment
- Upgrade to production for full access

### Debug Commands
```bash
# Check webhook health
curl http://localhost:5000/health

# Check Twilio health
curl http://localhost:5001/twilio-health
```

---

## 💡 Next Steps

1. **Choose your preferred integration method**
2. **Set up the webhook endpoint**
3. **Configure environment variables**
4. **Deploy to production**
5. **Test with real WhatsApp messages**

Your Sales Agent with currency conversion is now ready for WhatsApp! 🎉📱💱
