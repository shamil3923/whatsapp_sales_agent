# 📱 Meta WhatsApp Business API - Complete Setup Guide

## Current Status: ✅ Integration Code Ready, ⏳ Waiting for API Credentials

## Step-by-Step Setup Process

### 1. 🔑 Get Your API Credentials

#### A. Create Meta Developer Account
1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Log in with Facebook account (create one if needed)
3. Click "Create App" → "Business" → "WhatsApp"
4. Name your app: "Sales Agent Bot" or similar

#### B. Add WhatsApp Product
1. In app dashboard → "Add Product" → "WhatsApp"
2. Go to "Getting Started" section
3. You'll see:
   - **Test Phone Number** (provided by Meta)
   - **Phone Number ID** (copy this!)
   - **Access Token** (temporary, 24hrs only)

#### C. Create Permanent Access Token
1. Go to WhatsApp → Configuration
2. Click "System Users" → "Create System User"
3. Name: "Sales Agent System User"
4. Generate Token:
   - Select your app
   - Permission: `whatsapp_business_messaging`
   - **Copy the permanent token!**

### 2. 📝 Update Your Configuration

Replace the values in your `.env` file:

```env
# Replace with your actual values:
WHATSAPP_ACCESS_TOKEN="EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
WHATSAPP_PHONE_NUMBER_ID="123456789012345"
WHATSAPP_VERIFY_TOKEN="sales_agent_verify_token"
```

### 3. 🌐 Deploy Your Webhook

#### Option A: Quick Test with ngrok (Recommended for testing)
```bash
# Install ngrok from ngrok.com
# Run your WhatsApp integration
python whatsapp_integration.py

# In another terminal, expose it publicly
ngrok http 5000

# Copy the https URL (e.g., https://abc123.ngrok.io)
```

#### Option B: Deploy to Heroku (Production)
```bash
# Install Heroku CLI
# Create Heroku app
heroku create your-sales-agent-bot

# Set environment variables
heroku config:set WHATSAPP_ACCESS_TOKEN="your_token"
heroku config:set WHATSAPP_PHONE_NUMBER_ID="your_phone_id"
heroku config:set GOOGLE_API_KEY="your_google_key"

# Deploy
git add .
git commit -m "WhatsApp Sales Agent"
git push heroku main
```

### 4. 🔗 Configure Webhook in Meta

1. **Go to WhatsApp → Configuration**
2. **Webhook section:**
   - **Callback URL**: `https://your-domain.com/webhook`
   - **Verify Token**: `sales_agent_verify_token`
   - **Webhook Fields**: Check `messages`
3. **Click "Verify and Save"**

### 5. 🧪 Test Your Bot

#### Send Test Message via API:
```bash
curl -X POST http://localhost:5000/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "1234567890",
    "message": "Hello from Sales Agent!"
  }'
```

#### Test WhatsApp Features:
Send these messages to your WhatsApp number:
- "Hello" → Should get welcome message
- "Convert $500 to EUR" → Should show currency conversion
- "What products do you have?" → Should show product catalog
- "Current exchange rates" → Should show rate table

### 6. 🚀 Go Live

#### A. Add Your Phone Number
1. In Meta Developer Console
2. Go to WhatsApp → Phone Numbers
3. Add your business phone number
4. Verify with SMS/call

#### B. Create Message Templates
1. Go to WhatsApp → Message Templates
2. Create templates for:
   - Welcome message
   - Product catalogs
   - Currency conversion results

#### C. Submit for Review
1. Complete Business Verification
2. Submit app for review
3. Wait for approval (usually 1-2 days)

## 🔧 Troubleshooting

### Common Issues:

**❌ "Webhook verification failed"**
- Check verify token matches exactly
- Ensure webhook URL is publicly accessible
- Verify HTTPS (required by Meta)

**❌ "Invalid access token"**
- Use permanent token, not temporary one
- Check token has correct permissions
- Regenerate if expired

**❌ "Phone number not found"**
- Verify Phone Number ID is correct
- Check phone number is added to your app
- Ensure number is verified

### Debug Commands:
```bash
# Check if webhook is running
curl http://localhost:5000/health

# Test webhook verification
curl "http://localhost:5000/webhook?hub.mode=subscribe&hub.verify_token=sales_agent_verify_token&hub.challenge=test123"
```

## 📊 Features Your Bot Will Have

### 🛍️ Sales Features:
- Product recommendations
- Price comparisons  
- Stock availability
- Market insights
- Technical specifications

### 💱 Currency Features:
- Real-time currency conversion
- Exchange rate display
- Multi-currency pricing
- International sales support

### 📱 WhatsApp Features:
- Mobile-optimized formatting
- Emoji support
- Quick replies
- Rich media support (coming soon)

## 🎯 Next Steps After Setup

1. **Test thoroughly** with different message types
2. **Add more products** to your catalog
3. **Create message templates** for common responses
4. **Set up analytics** to track usage
5. **Scale up** with business verification

## 💡 Pro Tips

- **Test in sandbox first** before going live
- **Keep messages under 4000 characters** for best delivery
- **Use emojis** to make messages more engaging
- **Respond quickly** - WhatsApp users expect fast replies
- **Monitor rate limits** - 1000 messages/month on free tier

---

## 🆘 Need Help?

If you encounter issues:
1. Check the logs: `python whatsapp_integration.py`
2. Test locally first with ngrok
3. Verify all credentials are correct
4. Check Meta Developer Console for errors

Your Sales Agent with currency conversion is ready to serve WhatsApp customers! 🎉
