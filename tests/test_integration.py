"""
Integration tests for the complete WhatsApp Sales Agent system
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from whatsapp_integration import WhatsAppBot, app
from sales_agent import CurrencyConverter


class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.bot = WhatsAppBot()
    
    @patch('requests.post')
    @patch('requests.get')
    @patch('whatsapp_integration.get_ai_response')
    def test_complete_whatsapp_workflow(self, mock_ai_response, mock_get, mock_post):
        """Test complete WhatsApp message workflow"""
        # Mock currency API
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'rates': {'EUR': 0.85},
            'date': '2025-07-22'
        }
        
        # Mock WhatsApp API
        mock_post.return_value.status_code = 200
        
        # Mock AI response
        mock_response = Mock()
        mock_response.content = "Here's the currency conversion: **100 USD = 85 EUR**"
        mock_ai_response.return_value = mock_response
        
        # Simulate webhook message
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "1234567890",
                            "text": {"body": "Convert 100 USD to EUR"}
                        }]
                    }
                }]
            }]
        }
        
        response = self.app.post('/webhook',
                               data=json.dumps(webhook_data),
                               content_type='application/json')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Verify AI was called with WhatsApp context
        mock_ai_response.assert_called_once()
        call_args = mock_ai_response.call_args[0][0]
        self.assertIn("WhatsApp Message", call_args)
        self.assertIn("Convert 100 USD to EUR", call_args)
        
        # Verify WhatsApp message was sent
        mock_post.assert_called_once()
        sent_payload = mock_post.call_args[1]['json']
        self.assertEqual(sent_payload['to'], '1234567890')
        self.assertIn('85 EUR', sent_payload['text']['body'])
    
    @patch('requests.get')
    def test_currency_converter_real_workflow(self, mock_get):
        """Test currency converter with realistic data"""
        # Mock realistic API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'rates': {
                'EUR': 0.8542,
                'GBP': 0.7891,
                'JPY': 110.25,
                'CAD': 1.2456
            },
            'date': '2025-07-22'
        }
        
        converter = CurrencyConverter()
        
        # Test multiple conversions
        result_eur = converter.convert_currency(1000, 'USD', 'EUR')
        result_gbp = converter.convert_currency(500, 'USD', 'GBP')
        result_jpy = converter.convert_currency(100, 'USD', 'JPY')
        
        # Verify results
        self.assertIn('854.20 EUR', result_eur)
        self.assertIn('394.55 GBP', result_gbp)
        self.assertIn('11,025.00 JPY', result_jpy)
    
    def test_message_formatting_edge_cases(self):
        """Test message formatting with various edge cases"""
        test_cases = [
            ("**Bold** text", "*Bold* text"),
            ("###Header\n**Bold**", "Header\n*Bold*"),
            ("A" * 5000, "truncated"),  # Long message
            ("Normal text", "Normal text"),  # No formatting
            ("**Multiple** **bold** words", "*Multiple* *bold* words")
        ]
        
        for input_text, expected_part in test_cases:
            result = self.bot.format_for_whatsapp(input_text)
            self.assertIn(expected_part, result)
    
    @patch('requests.post')
    def test_error_handling_workflow(self, mock_post):
        """Test error handling in complete workflow"""
        # Test WhatsApp API failure
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = "Invalid phone number"
        
        result = self.bot.send_message("invalid_number", "Test message")
        self.assertFalse(result)
    
    def test_webhook_malformed_data(self):
        """Test webhook with malformed data"""
        malformed_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        # Missing messages field
                    }
                }]
            }]
        }
        
        response = self.app.post('/webhook',
                               data=json.dumps(malformed_data),
                               content_type='application/json')
        
        # Should handle gracefully
        self.assertEqual(response.status_code, 200)


class TestPerformanceAndReliability(unittest.TestCase):
    """Test performance and reliability aspects"""
    
    def setUp(self):
        self.bot = WhatsAppBot()
    
    def test_agent_caching(self):
        """Test that agent is properly cached"""
        with patch('whatsapp_integration.get_sales_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_get_agent.return_value = mock_agent
            
            # Multiple calls should only create agent once
            agent1 = self.bot.get_agent()
            agent2 = self.bot.get_agent()
            agent3 = self.bot.get_agent()
            
            self.assertEqual(agent1, agent2)
            self.assertEqual(agent2, agent3)
            mock_get_agent.assert_called_once()
    
    @patch('requests.get')
    def test_currency_api_timeout_handling(self, mock_get):
        """Test handling of API timeouts"""
        import requests
        mock_get.side_effect = requests.Timeout("Request timed out")
        
        converter = CurrencyConverter()
        result = converter.convert_currency(100, 'USD', 'EUR')
        
        self.assertIn('Error', result)
    
    def test_concurrent_message_processing(self):
        """Test handling of multiple concurrent messages"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def process_message(phone, message):
            try:
                with patch('whatsapp_integration.get_ai_response') as mock_ai:
                    mock_response = Mock()
                    mock_response.content = f"Response to {message}"
                    mock_ai.return_value = mock_response
                    
                    result = self.bot.process_message(phone, message)
                    results.put(result)
            except Exception as e:
                results.put(f"Error: {e}")
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=process_message,
                args=(f"123456789{i}", f"Message {i}")
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(results.qsize(), 5)
        while not results.empty():
            result = results.get()
            self.assertNotIn("Error:", result)


class TestSecurityAndValidation(unittest.TestCase):
    """Test security and input validation"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_webhook_token_validation(self):
        """Test webhook token validation"""
        # Valid token
        response = self.app.get('/webhook?hub.mode=subscribe&hub.verify_token=sales_agent_verify_token&hub.challenge=test')
        self.assertEqual(response.status_code, 200)
        
        # Invalid token
        response = self.app.get('/webhook?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=test')
        self.assertEqual(response.status_code, 403)
        
        # Missing parameters
        response = self.app.get('/webhook?hub.mode=subscribe')
        self.assertEqual(response.status_code, 403)
    
    def test_input_sanitization(self):
        """Test input sanitization for phone numbers and messages"""
        bot = WhatsAppBot()
        
        # Test various phone number formats
        test_numbers = [
            "+1234567890",
            "1234567890",
            "+1-234-567-8900",
            "invalid_number"
        ]
        
        for number in test_numbers:
            with patch('requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                # Should not crash with any input
                result = bot.send_message(number, "Test message")
                self.assertIsInstance(result, bool)
    
    def test_message_length_limits(self):
        """Test message length validation"""
        bot = WhatsAppBot()
        
        # Very long message
        long_message = "A" * 10000
        formatted = bot.format_for_whatsapp(long_message)
        
        # Should be truncated
        self.assertLess(len(formatted), 4100)
        self.assertIn("truncated", formatted)


if __name__ == '__main__':
    # Create comprehensive test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_suite.addTest(unittest.makeSuite(TestEndToEndIntegration))
    test_suite.addTest(unittest.makeSuite(TestPerformanceAndReliability))
    test_suite.addTest(unittest.makeSuite(TestSecurityAndValidation))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"INTEGRATION TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
