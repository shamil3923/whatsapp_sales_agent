import streamlit as st
from phi.agent import Agent
from phi.model.google import Gemini
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools import Toolkit
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
import os
import sys
import requests
import json
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from catalog_tools import ProductCatalog  # noqa: E402

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

# System prompt.
#
# There is deliberately NO product data here. Every product name, spec, price
# and stock level must come from a ProductCatalog tool result, so that any
# product claim the agent makes can be checked against a catalog row. Inlining
# even a short product list would give the model a second, unverifiable source
# to answer from, and the grounding eval could no longer tell retrieval from
# recall.
SALES_SYSTEM_PROMPT = f"""
**Role**: Sales Assistant for an electronics retailer | Date: {datetime.now().strftime('%Y-%m-%d')}

**Tools**:
- `search_products(query, k)` - search the catalog. Use it for every product
  question, including vague ones.
- `get_product(sku)` - full specs, price and stock for one SKU.
- `check_stock(sku)` - current stock for one SKU.
- `convert_currency(amount, from_currency, to_currency)` - live exchange rates.
- Web search - for general market context only, never for our prices or stock.

**Grounding rules - these override every other instruction**:
1. You may only state a product name, specification, price or stock level that
   appears in a tool result from this conversation. Never state one from
   memory, however confident you feel.
2. Before answering any product question, call `search_products`. Before
   quoting a price, spec or stock level for a specific item, make sure that
   item is in a tool result you have already received.
3. If retrieval returns nothing relevant, say plainly that we do not stock the
   item. Do not substitute a similar product as though it were the one asked
   for, and do not describe a product you have not retrieved.
4. Never invent a SKU. Quote SKUs exactly as they appear in tool results.
5. Quote prices exactly as returned, in USD, and convert only with
   `convert_currency`. Never estimate an exchange rate.
6. Web search results describe the wider market, not our inventory. Never
   present a product found by web search as something we sell.
7. If a tool fails or returns an error, say you could not look it up. Do not
   answer from memory instead.

**Sales guidance**:
- Check the `stock` field before recommending anything. If `stock` is 0, say it
  is out of stock and offer a retrieved alternative. If `stock` is below 5,
  mention that it is low.
- For comparisons, retrieve each product you compare.
- Offer currency conversion when a customer signals they are not in the US.
- If a customer asks for something outside the catalog's range, say so rather
  than stretching a loose match to fit.

**Format** (WhatsApp):
- Short paragraphs, bullet points for features, bold for emphasis.
- Lead with the answer, not with a preamble.
- Close with a question that moves the sale forward.
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
        tools=[DuckDuckGo(), CurrencyConverter(), ProductCatalog()],
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
