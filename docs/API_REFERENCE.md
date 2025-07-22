# 📚 API Reference

Complete API documentation for WhatsApp Sales Agent Pro.

## 🌐 REST API Endpoints

### Health Check

**GET** `/health`

Check if the service is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-22T22:00:00Z",
  "version": "1.0.0"
}
```

### Webhook Verification

**GET** `/webhook`

Verify webhook for WhatsApp Business API.

**Parameters:**
- `hub.mode` (string): Should be "subscribe"
- `hub.verify_token` (string): Your verification token
- `hub.challenge` (string): Challenge string from Meta

**Response:**
- `200`: Returns challenge string
- `403`: Invalid verification token

### Webhook Handler

**POST** `/webhook`

Receive and process WhatsApp messages.

**Request Body:**
```json
{
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "from": "1234567890",
                "text": {
                  "body": "Hello"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "status": "success"
}
```

### Manual Message Sending

**POST** `/send-message`

Send a message manually (for testing).

**Request Body:**
```json
{
  "phone_number": "+1234567890",
  "message": "Hello from Sales Agent!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message sent successfully"
}
```

## 🤖 Sales Agent API

### Core Agent Functions

#### `get_sales_agent()`
Create or get cached sales agent instance.

**Returns:** Agent instance with Gemini model and tools

#### `get_ai_response(prompt)`
Get AI response for a given prompt.

**Parameters:**
- `prompt` (string): User input or context

**Returns:** AI response object with content

## 💱 Currency Converter API

### CurrencyConverter Class

#### `convert_currency(amount, from_currency, to_currency)`
Convert amount between currencies.

**Parameters:**
- `amount` (float): Amount to convert
- `from_currency` (string): Source currency code (e.g., "USD")
- `to_currency` (string): Target currency code (e.g., "EUR")

**Returns:** Formatted conversion result string

**Example:**
```python
converter = CurrencyConverter()
result = converter.convert_currency(100, "USD", "EUR")
# Returns: "**Currency Conversion Result:**\n- **Amount**: 100.00 USD\n..."
```

#### `get_exchange_rates(base_currency)`
Get current exchange rates for a base currency.

**Parameters:**
- `base_currency` (string): Base currency code (default: "USD")

**Returns:** Formatted exchange rates table

#### `get_supported_currencies()`
Get list of supported currency codes.

**Returns:** Formatted table of currency codes and names

## 📱 WhatsApp Bot API

### WhatsAppBot Class

#### `__init__()`
Initialize WhatsApp bot with empty session storage.

#### `get_agent()`
Get or create sales agent instance (cached).

**Returns:** Sales agent instance

#### `send_message(phone_number, message)`
Send text message to WhatsApp user.

**Parameters:**
- `phone_number` (string): Recipient phone number
- `message` (string): Message content

**Returns:** Boolean success status

#### `send_template_message(phone_number, template_name)`
Send template message to WhatsApp user.

**Parameters:**
- `phone_number` (string): Recipient phone number
- `template_name` (string): Template name (default: "hello_world")

**Returns:** Boolean success status

#### `process_message(phone_number, message)`
Process incoming message and generate response.

**Parameters:**
- `phone_number` (string): Sender phone number
- `message` (string): Received message

**Returns:** Formatted response string

#### `format_for_whatsapp(message)`
Format message for WhatsApp display.

**Parameters:**
- `message` (string): Raw message with markdown

**Returns:** WhatsApp-formatted message

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google AI API key | Yes |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp access token | Yes |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID | Yes |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token | Yes |

### Product Catalog

The agent uses a predefined product catalog:

```python
PRODUCT_CATALOG = """
**Available Products:**
- Premium Laptops: Gaming (RTX 4080, i7), Business (ThinkPad, MacBook Pro), Ultrabooks  
- Smartphones: iPhone 15 Pro, Samsung Galaxy S24, Google Pixel 8
- Accessories: Wireless chargers, Premium headphones, Protective cases
- Software: Office 365, Adobe Creative Suite, Antivirus solutions
"""
```

## 🚨 Error Handling

### Common Error Responses

#### WhatsApp API Errors
```json
{
  "error": {
    "message": "Error validating access token",
    "type": "OAuthException",
    "code": 190
  }
}
```

#### Currency API Errors
```
❌ Error fetching exchange rates. Status code: 500
❌ Currency 'INVALID' not supported
❌ Error getting exchange rates: Connection timeout
```

#### Bot Processing Errors
```
Sorry, I'm having trouble processing your request. Please try again! 🤖
```

## 📊 Response Formats

### Currency Conversion Response
```
💱 **Currency Conversion Result:**
- **Amount**: 100.00 USD
- **Converts to**: 85.42 EUR
- **Exchange Rate**: 1 USD = 0.8542 EUR
- **Last Updated**: 2025-07-22

*Note: Rates are indicative and may vary from actual transaction rates.*
```

### Exchange Rates Response
```
**Exchange Rates (Base: USD)**

| Currency | Rate |
|----------|------|
| EUR | 0.8542 |
| GBP | 0.7891 |
| JPY | 110.25 |

*Last Updated: 2025-07-22*
```

### Product Information Response
```
💻 **Available Laptops:**
- Gaming Laptops: RTX 4080, i7 processor
- Business Laptops: ThinkPad, MacBook Pro  
- Ultrabooks: Lightweight, long battery life

💡 **Current Promotions:**
- 15% off gaming laptops this week
- Free shipping on orders over $500

What specific laptop features are you looking for? 🤔
```

## 🔒 Security

### Webhook Verification
All webhook requests are verified using the configured verify token.

### Input Sanitization
- Phone numbers are validated
- Messages are sanitized for WhatsApp formatting
- Long messages are truncated (4000 char limit)

### Rate Limiting
Consider implementing rate limiting for production use:
- Max 10 requests per minute per phone number
- Max 100 requests per hour per IP

## 📈 Monitoring

### Logging
The application logs:
- Incoming webhook requests
- Message processing results
- API call successes/failures
- Error conditions

### Metrics
Track these metrics for monitoring:
- Messages processed per hour
- Response time
- Error rates
- Currency conversion requests
- User engagement

---

For more information, see the [main README](../README.md) or [setup guide](SETUP_GUIDE.md).
