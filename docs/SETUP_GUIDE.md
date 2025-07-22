# 🚀 Complete Setup Guide

Step-by-step guide to set up WhatsApp Sales Agent Pro from scratch.

## 📋 Prerequisites

Before starting, ensure you have:

- **Python 3.8+** installed
- **Git** for version control
- **WhatsApp Business Account**
- **Meta Developer Account**
- **Google AI Studio Account**
- **Ngrok** for local development

## 🔧 Step 1: Environment Setup

### 1.1 Clone Repository
```bash
git clone https://github.com/shamil3923/ERP_Recommendation_Widget-.git
cd Task_02
```

### 1.2 Create Virtual Environment
```bash
# Create virtual environment
python -m venv sales_agent_env

# Activate virtual environment
# Windows:
sales_agent_env\Scripts\activate
# Linux/Mac:
source sales_agent_env/bin/activate
```

### 1.3 Install Dependencies
```bash
pip install -r config/requirements.txt
```

## 🔑 Step 2: API Keys Setup

### 2.1 Google AI API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the generated key
4. Save it for the `.env` file

### 2.2 Meta Developer Setup

1. **Create Meta Developer Account**
   - Go to [Meta for Developers](https://developers.facebook.com/)
   - Sign up or log in
   - Complete developer verification

2. **Create WhatsApp Business App**
   - Click "Create App"
   - Select "Business" type
   - Enter app name and contact email
   - Create app

3. **Add WhatsApp Product**
   - In app dashboard, click "Add Product"
   - Select "WhatsApp"
   - Click "Set Up"

4. **Get Credentials**
   - **Access Token**: Copy from "Temporary access token"
   - **Phone Number ID**: Copy from "From" dropdown
   - **App ID**: From app settings
   - **App Secret**: From app settings

## 📱 Step 3: WhatsApp Configuration

### 3.1 Configure Webhook

1. **Start Ngrok** (for local development)
   ```bash
   ngrok http 5000
   ```
   Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

2. **Set Webhook URL**
   - In WhatsApp Business API setup
   - Webhook URL: `https://your-ngrok-url.ngrok-free.app/webhook`
   - Verify Token: `sales_agent_verify_token`
   - Click "Verify and Save"

3. **Subscribe to Webhook Fields**
   - Select: `messages`
   - Click "Subscribe"

### 3.2 Test Phone Number

1. **Add Test Number**
   - In WhatsApp Business API setup
   - Click "Add phone number"
   - Enter your phone number
   - Verify with OTP

## ⚙️ Step 4: Configuration Files

### 4.1 Create Environment File

Create `config/.env`:
```env
# Google AI Configuration
GOOGLE_API_KEY=your_google_api_key_here

# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_VERIFY_TOKEN=sales_agent_verify_token

# Optional: Custom Configuration
DEBUG=True
LOG_LEVEL=INFO
```

### 4.2 Verify Configuration

Run the verification script:
```bash
python src/verify_meta_setup.py
```

Expected output:
```
✅ Environment variables loaded
✅ WhatsApp API connection successful
✅ Phone number ID valid
✅ All configurations verified!
```

## 🚀 Step 5: Running the Application

### 5.1 Start WhatsApp Bot
```bash
python src/whatsapp_integration.py
```

Expected output:
```
INFO:__main__:Starting WhatsApp Sales Agent...
* Running on http://127.0.0.1:5000
* Running on all addresses (0.0.0.0)
```

### 5.2 Start Web Interface (Optional)
```bash
# In a new terminal
streamlit run src/sales_agent.py
```

Access at: http://localhost:8501

## 🧪 Step 6: Testing

### 6.1 Test Webhook
```bash
curl "https://your-ngrok-url.ngrok-free.app/webhook?hub.mode=subscribe&hub.verify_token=sales_agent_verify_token&hub.challenge=test123"
```

Should return: `test123`

### 6.2 Test Health Endpoint
```bash
curl http://localhost:5000/health
```

Should return:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-22T22:00:00Z"
}
```

### 6.3 Send Test Message

Send a WhatsApp message to your business number:
```
Hello
```

Expected bot response:
```
Hi! 👋 Welcome to our store! I can help you with products, pricing, and currency conversions. What are you looking for today?
```

### 6.4 Test Currency Conversion
```
Convert 100 USD to EUR
```

Expected response:
```
💱 **Currency Conversion Result:**
- **Amount**: 100.00 USD
- **Converts to**: 85.42 EUR
- **Exchange Rate**: 1 USD = 0.8542 EUR
- **Last Updated**: 2025-07-22
```

## 🔍 Step 7: Troubleshooting

### Common Issues

#### 1. Webhook Verification Failed
**Problem**: 403 Forbidden on webhook verification

**Solution**:
- Check verify token matches in `.env` and Meta console
- Ensure ngrok URL is correct and accessible
- Verify webhook URL format: `https://domain.com/webhook`

#### 2. Access Token Expired
**Problem**: "Session has expired" error

**Solution**:
- Generate new access token in Meta Developer Console
- Update `WHATSAPP_ACCESS_TOKEN` in `.env`
- Restart the application

#### 3. Messages Not Received
**Problem**: Bot doesn't respond to messages

**Solution**:
- Check webhook subscription is active
- Verify phone number is added to test numbers
- Check application logs for errors
- Ensure ngrok tunnel is running

#### 4. Currency API Errors
**Problem**: Currency conversion fails

**Solution**:
- Check internet connection
- Verify exchangerate-api.com is accessible
- Check API rate limits
- Review error logs

### Debug Mode

Enable debug logging:
```python
# In whatsapp_integration.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Log Files

Check logs for errors:
```bash
# View recent logs
tail -f application.log

# Search for errors
grep "ERROR" application.log
```

## 📊 Step 8: Monitoring

### 8.1 Health Monitoring

Set up monitoring for:
- `/health` endpoint
- Response times
- Error rates
- Message volume

### 8.2 Log Analysis

Monitor these log patterns:
```
INFO:__main__:Message sent successfully
ERROR:__main__:Failed to send message
INFO:werkzeug:POST /webhook HTTP/1.1 200
```

## 🔒 Step 9: Security

### 9.1 Production Checklist

- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS in production
- [ ] Implement rate limiting
- [ ] Set up proper logging
- [ ] Configure firewall rules
- [ ] Use production WSGI server (not Flask dev server)

### 9.2 Access Token Security

- Rotate access tokens regularly
- Use short-lived tokens when possible
- Store tokens securely (not in code)
- Monitor token usage

## 🚀 Step 10: Deployment

### 10.1 Local Development
✅ You're ready! Your bot is running locally.

### 10.2 Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Heroku deployment
- AWS deployment
- Docker containerization
- CI/CD setup

## 📞 Support

If you encounter issues:

1. **Check logs** for error messages
2. **Review configuration** files
3. **Test API endpoints** individually
4. **Consult documentation** for specific errors
5. **Create GitHub issue** with error details

## ✅ Success Checklist

- [ ] Python environment set up
- [ ] Dependencies installed
- [ ] API keys configured
- [ ] Webhook verified
- [ ] Test message sent and received
- [ ] Currency conversion working
- [ ] Health endpoint responding
- [ ] Logs showing successful operations

**Congratulations! 🎉 Your WhatsApp Sales Agent is now ready to serve customers!**

---

Next: [API Reference](API_REFERENCE.md) | [Deployment Guide](DEPLOYMENT.md)
