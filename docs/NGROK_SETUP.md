# 🚀 ngrok Setup Guide - WhatsApp Sales Agent

## Why ngrok?
✅ **Super fast setup** (5 minutes)  
✅ **No account required** for basic use  
✅ **Perfect for testing**  
✅ **Works immediately**  

## Step-by-Step Setup

### Step 1: Download ngrok
1. **Go to**: [ngrok.com](https://ngrok.com)
2. **Click "Download"**
3. **Choose Windows**
4. **Download the ZIP file**
5. **Extract to a folder** (e.g., `C:\ngrok\`)

### Step 2: Start Your WhatsApp Bot
```bash
# In your project folder
python whatsapp_integration.py
```

You should see:
```
INFO:__main__:Starting WhatsApp Sales Agent...
* Running on all addresses (0.0.0.0)
* Running on http://127.0.0.1:5000
* Running on http://192.168.x.x:5000
```

**Keep this terminal open!**

### Step 3: Start ngrok (New Terminal)
1. **Open a NEW terminal/command prompt**
2. **Navigate to ngrok folder**:
   ```bash
   cd C:\ngrok
   ```
3. **Start ngrok**:
   ```bash
   ngrok http 5000
   ```

You'll see something like:
```
ngrok                                                          

Session Status                online
Account                       (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:5000
Forwarding                    http://abc123.ngrok.io -> http://localhost:5000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Copy the HTTPS URL**: `https://abc123.ngrok.io`

### Step 4: Configure Webhook in Meta
1. **Go to**: [developers.facebook.com](https://developers.facebook.com)
2. **Your App** → **WhatsApp** → **Configuration**
3. **Webhook Section**:
   - **Callback URL**: `https://abc123.ngrok.io/webhook`
   - **Verify Token**: `sales_agent_verify_token`
   - **Webhook Fields**: ✅ Check `messages`
4. **Click "Verify and Save"**

### Step 5: Test Your Bot! 🎉

Send these messages to your WhatsApp test number:

#### Sales Queries:
- **"Hello"** → Welcome message
- **"What products do you have?"** → Product catalog
- **"Compare iPhone vs Samsung"** → Product comparison

#### Currency Conversion:
- **"Convert $500 to EUR"** → Real-time conversion
- **"Current exchange rates"** → Rate table
- **"iPhone price in British pounds"** → Multi-currency pricing

## 🔧 Troubleshooting

### Common Issues:

**❌ "ngrok: command not found"**
- Make sure you're in the ngrok folder
- Or add ngrok to your PATH

**❌ "Webhook verification failed"**
- Check the ngrok URL is correct
- Make sure both terminals are running
- Verify token must be exactly: `sales_agent_verify_token`

**❌ "Connection refused"**
- Make sure `python whatsapp_integration.py` is running
- Check it's running on port 5000

**❌ ngrok tunnel closed**
- Free ngrok tunnels expire after 2 hours
- Just restart ngrok to get a new URL
- Update webhook URL in Meta Console

### Debug Commands:
```bash
# Check if your bot is running
curl http://localhost:5000/health

# Check ngrok status
# Go to: http://127.0.0.1:4040 in browser
```

## 💡 Pro Tips

1. **Keep both terminals open** (bot + ngrok)
2. **Use HTTPS URL** (not HTTP) for webhook
3. **ngrok free tunnels change** - update webhook URL when restarting
4. **Monitor ngrok dashboard** at http://127.0.0.1:4040
5. **Check logs** in both terminals for debugging

## 🎯 What Your Bot Will Do

### 🛍️ Sales Features:
- Product recommendations and comparisons
- Real-time market insights
- Stock availability checks
- Technical specifications

### 💱 Currency Features:
- **Real-time conversion**: "Convert $500 to EUR"
- **Exchange rates**: "What are current rates?"
- **Multi-currency pricing**: "Show prices in different currencies"
- **International support**: Automatic currency suggestions

### 📱 WhatsApp Features:
- Mobile-optimized formatting
- Emoji support and professional presentation
- Quick response times
- Error handling and retry logic

## 🚀 Ready to Go Live?

Once you're happy with testing:
1. **Get ngrok Pro** for permanent URLs
2. **Or deploy to Heroku/Railway** for production
3. **Complete Meta business verification**
4. **Add more phone numbers** to recipient list

---

## 🆘 Need Help?

If you encounter issues:
1. **Check both terminals** are running
2. **Verify ngrok URL** is correct in Meta Console
3. **Test webhook**: `https://your-ngrok-url.ngrok.io/health`
4. **Check ngrok dashboard**: http://127.0.0.1:4040

Your WhatsApp Sales Agent with currency conversion is ready to serve customers! 🎉📱💱
