"""
Unit tests for WhatsApp Integration functionality
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from whatsapp_integration import WhatsAppBot, app


class TestWhatsAppBot(unittest.TestCase):
    """Test WhatsApp Bot functionality"""
    
    def setUp(self):
        self.bot = WhatsAppBot()
    
    def test_bot_initialization(self):
        """Test bot initialization"""
        self.assertIsNone(self.bot.sales_agent)
        self.assertEqual(self.bot.user_sessions, {})
    
    @patch('whatsapp_integration.get_sales_agent')
    def test_get_agent(self, mock_get_sales_agent):
        """Test agent creation and caching"""
        mock_agent = Mock()
        mock_get_sales_agent.return_value = mock_agent
        
        # First call should create agent
        agent1 = self.bot.get_agent()
        self.assertEqual(agent1, mock_agent)
        self.assertEqual(self.bot.sales_agent, mock_agent)
        
        # Second call should return cached agent
        agent2 = self.bot.get_agent()
        self.assertEqual(agent2, mock_agent)
        mock_get_sales_agent.assert_called_once()
    
    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = self.bot.send_message("+1234567890", "Test message")
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['messaging_product'], 'whatsapp')
        self.assertEqual(payload['to'], '+1234567890')
        self.assertEqual(payload['text']['body'], 'Test message')
    
    @patch('requests.post')
    def test_send_message_failure(self, mock_post):
        """Test message sending failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Error message"
        mock_post.return_value = mock_response
        
        result = self.bot.send_message("+1234567890", "Test message")
        
        self.assertFalse(result)
    
    @patch('requests.post')
    def test_send_template_message(self, mock_post):
        """Test template message sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = self.bot.send_template_message("+1234567890", "hello_world")
        
        self.assertTrue(result)
        
        # Check template payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['type'], 'template')
        self.assertEqual(payload['template']['name'], 'hello_world')
    
    @patch('whatsapp_integration.get_ai_response')
    def test_process_message(self, mock_get_ai_response):
        """Test message processing"""
        mock_response = Mock()
        mock_response.content = "**Bold text** and normal text"
        mock_get_ai_response.return_value = mock_response
        
        result = self.bot.process_message("+1234567890", "Hello")
        
        # Check formatting
        self.assertIn("*Bold text*", result)
        self.assertNotIn("**", result)
        mock_get_ai_response.assert_called_once()
    
    def test_format_for_whatsapp(self):
        """Test WhatsApp message formatting"""
        test_message = "**Bold** text with ###Header and ##Subheader"
        
        result = self.bot.format_for_whatsapp(test_message)
        
        self.assertEqual(result, "*Bold* text with Header and Subheader")
    
    def test_format_for_whatsapp_long_message(self):
        """Test long message truncation"""
        long_message = "A" * 5000  # Longer than 4000 chars
        
        result = self.bot.format_for_whatsapp(long_message)
        
        self.assertLess(len(result), 4100)
        self.assertIn("truncated", result)


class TestWebhookEndpoints(unittest.TestCase):
    """Test Flask webhook endpoints"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
    
    def test_webhook_verification(self):
        """Test webhook verification"""
        response = self.app.get('/webhook?hub.mode=subscribe&hub.verify_token=sales_agent_verify_token&hub.challenge=test123')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode(), 'test123')
    
    def test_webhook_verification_invalid_token(self):
        """Test webhook verification with invalid token"""
        response = self.app.get('/webhook?hub.mode=subscribe&hub.verify_token=invalid&hub.challenge=test123')
        
        self.assertEqual(response.status_code, 403)
    
    @patch('whatsapp_integration.whatsapp_bot')
    def test_webhook_message_handling(self, mock_bot):
        """Test webhook message handling"""
        mock_bot.process_message.return_value = "Test response"
        mock_bot.send_message.return_value = True
        
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "1234567890",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }
        
        response = self.app.post('/webhook', 
                               data=json.dumps(webhook_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        mock_bot.process_message.assert_called_once_with("1234567890", "Hello")
        mock_bot.send_message.assert_called_once_with("1234567890", "Test response")
    
    def test_send_manual_message_endpoint(self):
        """Test manual message sending endpoint"""
        with patch('whatsapp_integration.whatsapp_bot') as mock_bot:
            mock_bot.send_message.return_value = True
            
            data = {
                "phone_number": "+1234567890",
                "message": "Test message"
            }
            
            response = self.app.post('/send-message',
                                   data=json.dumps(data),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.data)
            self.assertTrue(response_data['success'])
    
    def test_send_manual_message_missing_data(self):
        """Test manual message endpoint with missing data"""
        data = {"phone_number": "+1234567890"}  # Missing message
        
        response = self.app.post('/send-message',
                               data=json.dumps(data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 400)


class TestEnvironmentConfiguration(unittest.TestCase):
    """Test environment configuration"""
    
    @patch.dict(os.environ, {
        'WHATSAPP_ACCESS_TOKEN': 'test_token',
        'WHATSAPP_PHONE_NUMBER_ID': 'test_id',
        'WHATSAPP_VERIFY_TOKEN': 'test_verify'
    })
    def test_environment_variables_loaded(self):
        """Test that environment variables are properly loaded"""
        # Reload module to pick up new env vars
        import importlib
        import whatsapp_integration
        importlib.reload(whatsapp_integration)
        
        self.assertEqual(whatsapp_integration.WHATSAPP_TOKEN, 'test_token')
        self.assertEqual(whatsapp_integration.WHATSAPP_PHONE_NUMBER_ID, 'test_id')
        self.assertEqual(whatsapp_integration.VERIFY_TOKEN, 'test_verify')


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestWhatsAppBot))
    test_suite.addTest(unittest.makeSuite(TestWebhookEndpoints))
    test_suite.addTest(unittest.makeSuite(TestEnvironmentConfiguration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
