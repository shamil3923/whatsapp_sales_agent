import streamlit as st
from phi.agent import Agent
from phi.model.google import Gemini
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools import Toolkit
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
import os
import requests
import json
from datetime import datetime
from typing import Optional

load_dotenv()

# Currency Conversion Tool
class CurrencyConverter(Toolkit):
    def __init__(self):
        super().__init__(name="currency_converter")
        self.register(self.convert_currency)
        self.register(self.get_exchange_rates)
        self.register(self.get_supported_currencies)

    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> str:
        """
        Convert an amount from one currency to another using real-time exchange rates.

        Args:
            amount: The amount to convert
            from_currency: Source currency code (e.g., 'USD', 'EUR', 'GBP')
            to_currency: Target currency code (e.g., 'USD', 'EUR', 'GBP')

        Returns:
            Formatted conversion result with exchange rate information
        """
        try:
            # Using exchangerate-api.com (free tier)
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if to_currency.upper() in data['rates']:
                    exchange_rate = data['rates'][to_currency.upper()]
                    converted_amount = amount * exchange_rate

                    return f"""
**Currency Conversion Result:**
- **Amount**: {amount:,.2f} {from_currency.upper()}
- **Converts to**: {converted_amount:,.2f} {to_currency.upper()}
- **Exchange Rate**: 1 {from_currency.upper()} = {exchange_rate:.4f} {to_currency.upper()}
- **Last Updated**: {data.get('date', 'N/A')}

*Note: Rates are indicative and may vary from actual transaction rates.*
                    """
                else:
                    return f"❌ Currency '{to_currency.upper()}' not supported. Use get_supported_currencies() to see available options."
            else:
                return f"❌ Error fetching exchange rates. Status code: {response.status_code}"

        except requests.exceptions.RequestException as e:
            return f"❌ Network error: {str(e)}"
        except Exception as e:
            return f"❌ Conversion error: {str(e)}"

    def get_exchange_rates(self, base_currency: str = "USD") -> str:
        """
        Get current exchange rates for a base currency against major currencies.

        Args:
            base_currency: Base currency code (default: 'USD')

        Returns:
            Formatted table of exchange rates
        """
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{base_currency.upper()}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                rates = data['rates']

                # Major currencies to display
                major_currencies = ['EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'INR']

                result = f"**Exchange Rates (Base: {base_currency.upper()})**\n\n"
                result += "| Currency | Rate | \n|----------|------|\n"

                for currency in major_currencies:
                    if currency in rates and currency != base_currency.upper():
                        result += f"| {currency} | {rates[currency]:.4f} |\n"

                result += f"\n*Last Updated: {data.get('date', 'N/A')}*"
                return result
            else:
                return f"❌ Error fetching exchange rates. Status code: {response.status_code}"

        except Exception as e:
            return f"❌ Error getting exchange rates: {str(e)}"

    def get_supported_currencies(self) -> str:
        """
        Get list of supported currency codes.

        Returns:
            List of supported currencies with their full names
        """
        # Common currencies with full names
        currencies = {
            'USD': 'US Dollar', 'EUR': 'Euro', 'GBP': 'British Pound', 'JPY': 'Japanese Yen',
            'AUD': 'Australian Dollar', 'CAD': 'Canadian Dollar', 'CHF': 'Swiss Franc',
            'CNY': 'Chinese Yuan', 'INR': 'Indian Rupee', 'KRW': 'South Korean Won',
            'SGD': 'Singapore Dollar', 'HKD': 'Hong Kong Dollar', 'NOK': 'Norwegian Krone',
            'SEK': 'Swedish Krona', 'DKK': 'Danish Krone', 'PLN': 'Polish Zloty',
            'CZK': 'Czech Koruna', 'HUF': 'Hungarian Forint', 'RUB': 'Russian Ruble',
            'BRL': 'Brazilian Real', 'MXN': 'Mexican Peso', 'ZAR': 'South African Rand',
            'TRY': 'Turkish Lira', 'NZD': 'New Zealand Dollar', 'THB': 'Thai Baht',
            'MYR': 'Malaysian Ringgit', 'PHP': 'Philippine Peso', 'IDR': 'Indonesian Rupiah'
        }

        result = "**Supported Currencies:**\n\n"
        result += "| Code | Currency Name |\n|------|---------------|\n"

        for code, name in currencies.items():
            result += f"| {code} | {name} |\n"

        result += "\n*Note: Many more currencies are supported. These are the most commonly used ones.*"
        return result

# Configure page
st.set_page_config(
    page_title="AI Sales Agent Pro",
    page_icon="🤖",
    layout="centered"
)
st.title("💼 Sales Agent")
st.markdown("Powered by Gemini Pro | Market Analytics | Currency Conversion 💱")

# Expanded Product Catalog
PRODUCT_CATALOG = """
**Available Products:**
- Premium Laptops: Gaming (RTX 4080, i7), Business (ThinkPad, MacBook Pro), Ultrabooks  
- Smartphones: iPhone 15 Pro, Samsung Galaxy S24, Google Pixel 8
- Accessories: Wireless chargers, Premium headphones, Protective cases
- Software: Office 365, Adobe Creative Suite, Antivirus solutions
"""

# System prompt with enhanced instructions
SALES_SYSTEM_PROMPT = f"""
**Role**: Senior Sales Analyst | Date: {datetime.now().strftime('%Y-%m-%d')}

**Core Capabilities**:
1. Real-time Market Analysis (via web search)
2. Inventory Management & Stock Checks
3. Product Comparisons & Alternatives
4. Technical Specifications Breakdown
5. Price Tracking & Competitor Monitoring
6. Trend Identification & Forecasting
7. **Currency Conversion & International Pricing** (NEW!)

**Product Catalog**:
{PRODUCT_CATALOG}

**Operational Guidelines**:
1. Always first check 'stock' field before recommendations
2. Use web search for latest market trends when needed
3. Compare minimum 3 products for any comparison request
4. Highlight 'trend_score' when > 4.5/5.0
5. Mention competitor alternatives with pricing
6. Provide warranty & return policy information
7. **Currency Conversion**: When customers ask about prices in different currencies, use convert_currency() tool
8. **International Sales**: Automatically offer currency conversion for international customers
9. Format responses with:
   - Bullet points for features
   - Tables for comparisons
   - Bold headers for sections
   - Currency conversions when relevant

**Error Handling**:
- If stock < 5: "Low stock alert: Only X remaining"
- If no data: "Let me research that..."
- For pricing: "Current promotion: [details]"
- For currency conversion errors: "Let me get the latest exchange rates..."
- Never invent specifications or exchange rates
"""

@st.cache_resource
def get_sales_agent():
    return Agent(
        model=Gemini(
            id="gemini-2.0-flash-exp",
            temperature=0.3,
            max_tokens=1024
        ),
        system_prompt=SALES_SYSTEM_PROMPT,
        tools=[DuckDuckGo(), CurrencyConverter()],
        markdown=True
    )

# Retry logic for API calls
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_ai_response(prompt):
    return get_sales_agent().run(prompt)

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hi! I'm your sales assistant. Ask about products, compare options, get market insights, or convert prices to different currencies! 🚀💱"
    }]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about products, trends, or currency conversion..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    response_content = "Sorry, I'm having trouble connecting. Please try again later."  # Default response
    try:
        with st.chat_message("assistant"):
            with st.spinner("Analyzing request..."):
                response = get_ai_response(prompt)
                response_content = response.content
                st.markdown(response_content)
                
                # Auto-suggest follow-ups
                if any(keyword in prompt.lower() for keyword in ["compare", "recommend", "suggest"]):
                    st.markdown("""
                    **Quick Actions**:
                    - 📊 Generate price comparison chart
                    - 📦 Check local availability
                    - ⏳ View price history
                    - 💱 Convert prices to your currency
                    """)
                elif any(keyword in prompt.lower() for keyword in ["price", "cost", "currency", "convert"]):
                    st.markdown("""
                    **Currency Options**:
                    - 💱 Convert to different currencies
                    - 📈 View current exchange rates
                    - 🌍 See international pricing
                    """)
                
    except Exception as e:
        response_content = f"Error: {str(e)}"
        st.error(response_content)
    
    finally:
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_content
        })
