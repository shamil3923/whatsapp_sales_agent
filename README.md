# 🤖 WhatsApp Sales Agent Pro

An intelligent WhatsApp sales agent powered by Google Gemini AI with real-time currency conversion, market analysis, and automated customer support.

## ✨ Features

- **🤖 AI-Powered Sales Agent**: Intelligent responses using Google Gemini 2.0
- **💱 Real-Time Currency Conversion**: Support for 20+ major currencies
- **📱 WhatsApp Integration**: Native WhatsApp Business API integration
- **🔍 Market Research**: Real-time web search for product information
- **📊 Product Catalog**: Comprehensive product database
- **🌐 Multi-Language Support**: Handles international customers
- **🔒 Secure Webhook**: Verified webhook endpoints
- **📈 Analytics Ready**: Built-in logging and monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- WhatsApp Business Account
- Meta Developer Account
- Google AI API Key
- Ngrok (for local development)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/shamil3923/ERP_Recommendation_Widget-.git
cd Task_02
```

2. **Create virtual environment**
```bash
python -m venv sales_agent_env
# Windows
sales_agent_env\Scripts\activate
# Linux/Mac
source sales_agent_env/bin/activate
```

3. **Install dependencies**
```bash
pip install -r config/requirements.txt
```

4. **Configure environment**
```bash
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

5. **Run the application**
```bash
# Start WhatsApp bot
python src/whatsapp_integration.py

# Start web interface (optional)
streamlit run src/sales_agent.py
```

## 📁 Project Structure

```
├── src/                    # Source code
│   ├── sales_agent.py      # Core AI agent
│   ├── whatsapp_integration.py  # WhatsApp bot
│   └── currency_demo.py    # Currency converter demo
├── tests/                  # Test files
│   ├── test_sales_agent.py
│   ├── test_whatsapp_integration.py
│   ├── test_integration.py
│   └── run_tests.py
├── docs/                   # Documentation
│   ├── SETUP_GUIDE.md
│   ├── API_REFERENCE.md
│   └── DEPLOYMENT.md
├── config/                 # Configuration files
│   ├── .env
│   └── requirements.txt
└── README.md
```

## 🔧 Configuration

### Environment Variables

Create `config/.env` with:

```env
# Google AI
GOOGLE_API_KEY=your_google_api_key

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
```

### WhatsApp Setup

1. Create Meta Developer Account
2. Create WhatsApp Business App
3. Get Access Token and Phone Number ID
4. Configure Webhook URL
5. Verify webhook token

See [docs/WHATSAPP_SETUP_GUIDE.md](docs/WHATSAPP_SETUP_GUIDE.md) for detailed instructions.

## 🧪 Testing

Run all tests:
```bash
python tests/run_tests.py
```

Run specific test suite:
```bash
python tests/run_tests.py sales_agent
python tests/run_tests.py whatsapp_integration
python tests/run_tests.py integration
```

## 📚 API Reference

### WhatsApp Bot Endpoints

- `GET /health` - Health check
- `GET /webhook` - Webhook verification
- `POST /webhook` - Receive WhatsApp messages
- `POST /send-message` - Send manual messages

### Currency Converter

- `convert_currency(amount, from_currency, to_currency)` - Convert currencies
- `get_exchange_rates(base_currency)` - Get current exchange rates
- `get_supported_currencies()` - List supported currencies

## 🚀 Deployment

### Local Development
```bash
# Start ngrok tunnel
ngrok http 5000

# Update webhook URL in Meta Developer Console
# Run the bot
python src/whatsapp_integration.py
```

### Production Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for:
- Heroku deployment
- AWS deployment
- Docker containerization
- Environment setup

## 🔍 Usage Examples

### Basic Chat
```
User: "Hello"
Bot: "Hi! 👋 Welcome to our store! I can help you with products, pricing, and currency conversions. What are you looking for today?"
```

### Currency Conversion
```
User: "Convert 100 USD to EUR"
Bot: "💱 **Currency Conversion Result:**
- **Amount**: 100.00 USD
- **Converts to**: 85.42 EUR
- **Exchange Rate**: 1 USD = 0.8542 EUR
- **Last Updated**: 2025-07-22"
```

### Product Inquiry
```
User: "Show me laptops"
Bot: "💻 **Available Laptops:**
- Gaming Laptops: RTX 4080, i7 processor
- Business Laptops: ThinkPad, MacBook Pro
- Ultrabooks: Lightweight, long battery life

Would you like details on any specific category?"
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@example.com
- 💬 WhatsApp: +1-xxx-xxx-xxxx
- 🐛 Issues: [GitHub Issues](https://github.com/shamil3923/ERP_Recommendation_Widget-/issues)

## 🙏 Acknowledgments

- Google Gemini AI for intelligent responses
- Meta WhatsApp Business API
- ExchangeRate-API for currency data
- Streamlit for web interface
- Flask for webhook handling

---

**Made with ❤️ by [Mohamed Shamil](https://github.com/shamil3923)**
