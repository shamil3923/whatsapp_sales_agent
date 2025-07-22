"""
Unit tests for Sales Agent functionality
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sales_agent import get_sales_agent, get_ai_response, CurrencyConverter


class TestCurrencyConverter(unittest.TestCase):
    """Test Currency Converter functionality"""
    
    def setUp(self):
        self.converter = CurrencyConverter()
    
    @patch('requests.get')
    def test_convert_currency_success(self, mock_get):
        """Test successful currency conversion"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'rates': {'EUR': 0.85},
            'date': '2025-07-22'
        }
        mock_get.return_value = mock_response
        
        result = self.converter.convert_currency(100, 'USD', 'EUR')
        
        self.assertIn('85.00 EUR', result)
        self.assertIn('100.00 USD', result)
        self.assertIn('0.8500', result)
    
    @patch('requests.get')
    def test_convert_currency_invalid_currency(self, mock_get):
        """Test conversion with invalid currency"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'rates': {'EUR': 0.85},
            'date': '2025-07-22'
        }
        mock_get.return_value = mock_response
        
        result = self.converter.convert_currency(100, 'USD', 'INVALID')
        
        self.assertIn('not supported', result)
    
    @patch('requests.get')
    def test_convert_currency_api_error(self, mock_get):
        """Test API error handling"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = self.converter.convert_currency(100, 'USD', 'EUR')
        
        self.assertIn('Error fetching', result)
    
    @patch('requests.get')
    def test_get_exchange_rates_success(self, mock_get):
        """Test getting exchange rates"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'rates': {'EUR': 0.85, 'GBP': 0.75, 'JPY': 110.0},
            'date': '2025-07-22'
        }
        mock_get.return_value = mock_response
        
        result = self.converter.get_exchange_rates('USD')
        
        self.assertIn('EUR', result)
        self.assertIn('0.8500', result)
        self.assertIn('2025-07-22', result)
    
    def test_get_supported_currencies(self):
        """Test getting supported currencies list"""
        result = self.converter.get_supported_currencies()
        
        self.assertIn('USD', result)
        self.assertIn('EUR', result)
        self.assertIn('US Dollar', result)
        self.assertIn('Euro', result)


class TestSalesAgent(unittest.TestCase):
    """Test Sales Agent core functionality"""
    
    @patch('sales_agent.Gemini')
    @patch('sales_agent.Agent')
    def test_get_sales_agent_creation(self, mock_agent, mock_gemini):
        """Test sales agent creation"""
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        agent = get_sales_agent()
        
        mock_agent.assert_called_once()
        mock_gemini.assert_called_once()
        self.assertEqual(agent, mock_agent_instance)
    
    @patch('sales_agent.get_sales_agent')
    def test_get_ai_response(self, mock_get_agent):
        """Test AI response generation"""
        mock_agent = Mock()
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_agent.run.return_value = mock_response
        mock_get_agent.return_value = mock_agent
        
        response = get_ai_response("Test prompt")
        
        mock_agent.run.assert_called_once_with("Test prompt")
        self.assertEqual(response, mock_response)
    
    def test_product_catalog_exists(self):
        """Test that product catalog is defined"""
        from sales_agent import PRODUCT_CATALOG
        
        self.assertIsInstance(PRODUCT_CATALOG, str)
        self.assertIn('Laptops', PRODUCT_CATALOG)
        self.assertIn('Smartphones', PRODUCT_CATALOG)
    
    def test_sales_system_prompt_exists(self):
        """Test that system prompt is properly configured"""
        from sales_agent import SALES_SYSTEM_PROMPT
        
        self.assertIsInstance(SALES_SYSTEM_PROMPT, str)
        self.assertIn('Sales Analyst', SALES_SYSTEM_PROMPT)
        self.assertIn('Currency Conversion', SALES_SYSTEM_PROMPT)


class TestIntegration(unittest.TestCase):
    """Integration tests for Sales Agent components"""
    
    @patch('requests.get')
    def test_currency_conversion_integration(self, mock_get):
        """Test full currency conversion workflow"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'rates': {'EUR': 0.85, 'GBP': 0.75},
            'date': '2025-07-22'
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        
        # Test conversion
        result = converter.convert_currency(1000, 'USD', 'EUR')
        self.assertIn('850.00 EUR', result)
        
        # Test rates
        rates = converter.get_exchange_rates('USD')
        self.assertIn('EUR', rates)
        self.assertIn('GBP', rates)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestCurrencyConverter))
    test_suite.addTest(unittest.makeSuite(TestSalesAgent))
    test_suite.addTest(unittest.makeSuite(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
