# 💱 Currency Conversion Features

## Overview
The Sales Agent now includes comprehensive currency conversion capabilities, allowing customers to view prices and make conversions in real-time using live exchange rates.

## New Features Added

### 🔧 Currency Conversion Tools
- **Real-time Exchange Rates**: Uses exchangerate-api.com for up-to-date rates
- **170+ Currencies Supported**: Major world currencies and many regional ones
- **Automatic Rate Updates**: Rates updated every 60 minutes
- **Error Handling**: Graceful handling of network issues and invalid currencies

### 🎯 Core Functions

#### 1. `convert_currency(amount, from_currency, to_currency)`
- Converts any amount between supported currencies
- Shows exchange rate and conversion details
- Example: Convert $1000 USD to EUR

#### 2. `get_exchange_rates(base_currency)`
- Displays current exchange rates for major currencies
- Customizable base currency (default: USD)
- Formatted as easy-to-read table

#### 3. `get_supported_currencies()`
- Lists all supported currency codes and names
- Includes 25+ most commonly used currencies
- Helpful reference for users

## Usage Examples

### In the Sales Agent Chat:
```
User: "Convert $1200 to EUR"
Agent: Shows conversion with current exchange rate

User: "What's the current exchange rate for GBP?"
Agent: Displays USD to GBP rate and other major currencies

User: "Show me iPhone prices in different currencies"
Agent: Converts product prices to multiple currencies

User: "Convert the laptop price to British pounds"
Agent: Performs specific currency conversion for products
```

### Sample Conversions:
- **$1,000 USD** → **€857.00 EUR** (Rate: 1 USD = 0.8570 EUR)
- **£500 GBP** → **¥99,420 JPY** (Rate: 1 GBP = 198.84 JPY)
- **€750 EUR** → **$875.44 USD** (Rate: 1 EUR = 1.1673 USD)

## Integration Details

### Updated System Prompt
- Added currency conversion as core capability #7
- Enhanced operational guidelines for international sales
- Automatic currency conversion suggestions for international customers

### Enhanced User Interface
- Updated page title to include "Currency Conversion 💱"
- Modified chat placeholder to mention currency features
- Added currency-specific quick action suggestions
- Enhanced welcome message with currency emoji

### Error Handling
- Network timeout protection (10-second limit)
- Invalid currency code detection
- API failure fallback messages
- Rate limiting awareness

## Technical Implementation

### Dependencies Added:
- `requests>=2.32.0` - For API calls
- `duckduckgo-search>=8.1.0` - Already included
- `tenacity>=9.0.0` - For retry logic

### API Integration:
- **Provider**: exchangerate-api.com (free tier)
- **Update Frequency**: Every 60 minutes
- **Supported Currencies**: 170+
- **Rate Limit**: 1,500 requests/month (free tier)

### Code Structure:
```python
class CurrencyConverter(Toolkit):
    - convert_currency()      # Main conversion function
    - get_exchange_rates()    # Rate display function  
    - get_supported_currencies()  # Currency list function
```

## Benefits for Sales

### 🌍 International Customers
- Instant price conversions to local currency
- Eliminates conversion confusion
- Builds trust with accurate, real-time rates

### 💼 Sales Process
- Streamlined international sales
- Reduced friction in purchase decisions
- Professional presentation of pricing

### 📊 Market Analysis
- Compare prices across different markets
- Understand currency impact on pricing
- Track exchange rate trends

## Testing

Run the demo script to test all functions:
```bash
python currency_demo.py
```

This will demonstrate:
- USD to EUR conversion
- Current exchange rates display
- Supported currencies list
- GBP to JPY conversion

## Future Enhancements

### Potential Additions:
- Historical exchange rate charts
- Currency trend analysis
- Multi-currency price comparisons
- Automatic regional pricing suggestions
- Currency volatility alerts

### API Upgrade Options:
- Premium API for higher rate limits
- Historical data access
- More frequent updates (real-time)
- Additional financial data

---

## Quick Start Guide

1. **Start the Sales Agent**: `streamlit run sales_agent.py`
2. **Ask for conversion**: "Convert $500 to EUR"
3. **View exchange rates**: "Show current exchange rates"
4. **Check currencies**: "What currencies do you support?"

The currency conversion feature is now fully integrated and ready to enhance your international sales experience! 🚀💱
