#!/usr/bin/env python3
"""
Currency Conversion Demo
This script demonstrates the currency conversion functionality
that has been integrated into the Sales Agent.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sales_agent import CurrencyConverter

def main():
    print("🚀 Currency Conversion Demo")
    print("=" * 50)
    
    # Initialize the currency converter
    converter = CurrencyConverter()
    
    # Demo 1: Convert USD to EUR
    print("\n📊 Demo 1: Convert $1000 USD to EUR")
    result = converter.convert_currency(1000, "USD", "EUR")
    print(result)
    
    # Demo 2: Get exchange rates for USD
    print("\n📊 Demo 2: Current USD Exchange Rates")
    rates = converter.get_exchange_rates("USD")
    print(rates)
    
    # Demo 3: Show supported currencies
    print("\n📊 Demo 3: Supported Currencies")
    currencies = converter.get_supported_currencies()
    print(currencies)
    
    # Demo 4: Convert GBP to JPY
    print("\n📊 Demo 4: Convert £500 GBP to JPY")
    result = converter.convert_currency(500, "GBP", "JPY")
    print(result)
    
    print("\n" + "=" * 50)
    print("✅ Demo completed! The currency converter is now integrated into the Sales Agent.")
    print("💡 Try asking the Sales Agent questions like:")
    print("   - 'Convert $1200 to EUR'")
    print("   - 'What are the current exchange rates?'")
    print("   - 'Show me iPhone prices in different currencies'")
    print("   - 'Convert the laptop price to British pounds'")

if __name__ == "__main__":
    main()
