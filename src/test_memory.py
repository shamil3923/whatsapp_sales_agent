"""
Test script for conversation memory functionality
"""
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(__file__))

from conversation_memory import ConversationMemory

def test_memory_system():
    """Test the conversation memory system"""
    print("🧠 Testing WhatsApp Sales Agent Memory System")
    print("=" * 50)
    
    # Initialize memory
    memory = ConversationMemory()
    
    # Test user
    test_phone = "+1234567890"
    
    print(f"\n📱 Testing with phone number: {test_phone}")
    
    # Simulate conversation
    print("\n💬 Simulating conversation...")
    
    # User introduces themselves
    memory.add_message(test_phone, "user", "Hi, my name is John")
    memory.add_message(test_phone, "assistant", "Hello John! Welcome to our store! How can I help you today?")
    
    # User asks about products
    memory.add_message(test_phone, "user", "I'm looking for a laptop for gaming")
    memory.add_message(test_phone, "assistant", "Great choice! We have excellent gaming laptops with RTX 4080 graphics cards. What's your budget range?")
    
    # User asks about currency
    memory.add_message(test_phone, "user", "Convert 1500 USD to EUR please")
    memory.add_message(test_phone, "assistant", "1500 USD converts to approximately 1275 EUR at current rates. Would you like to see laptops in EUR pricing?")
    
    # User continues conversation
    memory.add_message(test_phone, "user", "Yes, show me laptops under 1200 EUR")
    memory.add_message(test_phone, "assistant", "Perfect! Here are some great gaming laptops under 1200 EUR...")
    
    print("✅ Added conversation messages")
    
    # Test context retrieval
    print("\n🔍 Testing context retrieval...")
    context = memory.get_conversation_context(test_phone)
    print("Context:")
    print(context)
    
    # Test user profile
    print("\n👤 Testing user profile...")
    user_summary = memory.get_user_summary(test_phone)
    print("User Summary:")
    for key, value in user_summary.items():
        print(f"  {key}: {value}")
    
    # Test preferences update
    print("\n⚙️ Testing preferences update...")
    memory.update_user_preferences(test_phone, preferred_currency="EUR", name="John Smith")
    memory.add_user_interest(test_phone, "gaming")
    memory.add_user_interest(test_phone, "laptops")
    
    updated_summary = memory.get_user_summary(test_phone)
    print("Updated User Summary:")
    for key, value in updated_summary.items():
        print(f"  {key}: {value}")
    
    # Test session persistence
    print("\n💾 Testing session persistence...")
    
    # Create new memory instance (simulates restart)
    memory2 = ConversationMemory()
    
    # Check if data persisted
    loaded_context = memory2.get_conversation_context(test_phone)
    print("Loaded context after restart:")
    print(loaded_context)
    
    # Test analytics
    print("\n📊 Testing analytics...")
    all_users = memory2.get_all_users_summary()
    print(f"Total users: {len(all_users)}")
    for user in all_users:
        print(f"  User: {user['phone_number']} - {user['total_interactions']} interactions")
    
    print("\n✅ Memory system test completed successfully!")
    
    return True

def test_multiple_users():
    """Test with multiple users"""
    print("\n👥 Testing multiple users...")
    
    memory = ConversationMemory()
    
    # User 1
    memory.add_message("+1111111111", "user", "Hello, I'm Alice")
    memory.add_message("+1111111111", "assistant", "Hi Alice! How can I help?")
    memory.update_user_preferences("+1111111111", name="Alice", preferred_currency="USD")
    memory.add_user_interest("+1111111111", "smartphones")
    
    # User 2
    memory.add_message("+2222222222", "user", "Hi, I'm Bob from UK")
    memory.add_message("+2222222222", "assistant", "Hello Bob! Welcome!")
    memory.update_user_preferences("+2222222222", name="Bob", preferred_currency="GBP")
    memory.add_user_interest("+2222222222", "laptops")
    
    # User 3
    memory.add_message("+3333333333", "user", "Bonjour, je suis Marie")
    memory.add_message("+3333333333", "assistant", "Bonjour Marie! Comment puis-je vous aider?")
    memory.update_user_preferences("+3333333333", name="Marie", preferred_currency="EUR")
    memory.add_user_interest("+3333333333", "accessories")
    
    # Get analytics
    analytics = memory.get_all_users_summary()
    print(f"Total users: {len(analytics)}")
    
    for user in analytics:
        print(f"📱 {user['name']} ({user['phone_number']})")
        print(f"   Currency: {user['preferred_currency']}")
        print(f"   Interests: {', '.join(user['interests'])}")
        print(f"   Messages: {user['total_messages']}")
        print()
    
    print("✅ Multiple users test completed!")

def demonstrate_context_awareness():
    """Demonstrate context-aware responses"""
    print("\n🎯 Demonstrating Context-Aware Responses")
    print("=" * 50)
    
    memory = ConversationMemory()
    phone = "+9999999999"
    
    # Simulate a realistic conversation flow
    conversations = [
        ("user", "Hello"),
        ("assistant", "Hi! Welcome to our store! I'm your AI sales assistant. How can I help you today?"),
        ("user", "I'm looking for a new laptop"),
        ("assistant", "Great! I'd be happy to help you find the perfect laptop. What will you primarily use it for?"),
        ("user", "Gaming and video editing"),
        ("assistant", "Excellent! For gaming and video editing, you'll want a powerful machine. What's your budget range?"),
        ("user", "Around 2000 USD"),
        ("assistant", "Perfect! With a $2000 budget, we have some fantastic options. Would you like to see our top gaming laptops?"),
        ("user", "Yes, but can you show prices in EUR?"),
        ("assistant", "Of course! 2000 USD is approximately 1700 EUR. Here are our top gaming laptops in EUR..."),
        ("user", "Thanks! I'll think about it and come back later"),
        ("assistant", "No problem! Take your time. I'll remember our conversation when you return. Have a great day!"),
    ]
    
    # Add all messages
    for role, content in conversations:
        memory.add_message(phone, role, content)
        if role == "user" and "eur" in content.lower():
            memory.update_user_preferences(phone, preferred_currency="EUR")
        if "gaming" in content.lower():
            memory.add_user_interest(phone, "gaming")
        if "video editing" in content.lower():
            memory.add_user_interest(phone, "video editing")
    
    print("📝 Conversation history added")
    
    # Now simulate user returning
    print("\n🔄 User returns after some time...")
    
    # Get context for returning user
    context = memory.get_conversation_context(phone, last_n_messages=5)
    print("\nContext for AI (last 5 messages):")
    print(context)
    
    # Simulate new message
    memory.add_message(phone, "user", "Hi, I'm back. Do you remember me?")
    
    # Show full context
    full_context = memory.get_conversation_context(phone)
    print("\n📋 Full conversation context:")
    print(full_context)
    
    print("\n✅ Context awareness demonstration completed!")

if __name__ == "__main__":
    try:
        # Run all tests
        test_memory_system()
        test_multiple_users()
        demonstrate_context_awareness()
        
        print("\n🎉 All memory tests passed successfully!")
        print("\n💡 The memory system is ready for integration with your WhatsApp bot!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
