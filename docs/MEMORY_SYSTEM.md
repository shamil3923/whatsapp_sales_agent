# 🧠 Conversation Memory System

Complete guide to the WhatsApp Sales Agent's conversation memory and context-aware response system.

## 🎯 Overview

The memory system enables your WhatsApp Sales Agent to:
- **Remember conversations** across multiple interactions
- **Learn user preferences** (currency, interests, name)
- **Provide context-aware responses** based on conversation history
- **Persist data** between bot restarts
- **Track user analytics** and engagement

## 🏗️ Architecture

### Core Components

1. **ConversationMemory** - Main memory manager
2. **ConversationSession** - User session data
3. **UserProfile** - User preferences and metadata
4. **ConversationMessage** - Individual message storage

### Data Flow

```
User Message → Memory Analysis → Context Retrieval → AI Response → Memory Update
```

## 📊 Data Structure

### User Profile
```python
{
    "phone_number": "+1234567890",
    "name": "John Smith",
    "preferred_currency": "EUR",
    "interests": ["gaming", "laptops"],
    "last_interaction": "2025-07-22T22:30:00",
    "total_interactions": 15
}
```

### Conversation Message
```python
{
    "timestamp": "2025-07-22T22:30:00",
    "role": "user",  # or "assistant"
    "content": "I need a gaming laptop",
    "message_type": "product_inquiry",
    "metadata": {"detected_products": ["laptop"]}
}
```

## 🚀 Features

### 1. **Automatic Message Classification**

The system automatically detects:
- **Currency Conversions**: "Convert 100 USD to EUR"
- **Product Inquiries**: "Show me laptops"
- **Greetings**: "Hello", "Hi"
- **Support Requests**: "I need help"

### 2. **User Preference Learning**

Automatically extracts and remembers:
- **Name**: "My name is John"
- **Preferred Currency**: From conversion requests
- **Interests**: From product inquiries
- **Interaction Patterns**: Frequency, timing

### 3. **Context-Aware Responses**

AI receives enriched context:
```
User Profile: John Smith (+1234567890)
Preferred Currency: EUR
Total Interactions: 5
Interests: gaming, laptops

Recent Conversation History:
[14:30] USER: I need a gaming laptop
[14:31] ASSISTANT: Great! What's your budget?
[14:32] USER: Around 1500 EUR
```

### 4. **Persistent Storage**

- **File-based storage** in `data/conversations/`
- **JSON format** for easy debugging
- **Automatic backup** and recovery
- **Session cleanup** for old data

## 🔧 Implementation

### Basic Usage

```python
from conversation_memory import ConversationMemory

# Initialize memory system
memory = ConversationMemory()

# Add user message
memory.add_message("+1234567890", "user", "Hello")

# Get conversation context
context = memory.get_conversation_context("+1234567890")

# Update user preferences
memory.update_user_preferences("+1234567890", name="John", preferred_currency="EUR")
```

### WhatsApp Integration

The memory system is integrated into `whatsapp_integration.py`:

```python
def process_message(self, phone_number: str, message: str) -> str:
    # Add user message to memory
    self.memory.add_message(phone_number, "user", message)
    
    # Get conversation context
    context = self.memory.get_conversation_context(phone_number)
    
    # Generate context-aware response
    response = get_ai_response(enhanced_context)
    
    # Save assistant response
    self.memory.add_message(phone_number, "assistant", response)
```

## 📱 API Endpoints

### Get Conversation History
```http
GET /conversation/{phone_number}
```

**Response:**
```json
{
    "user_profile": {
        "phone_number": "+1234567890",
        "name": "John Smith",
        "preferred_currency": "EUR",
        "interests": ["gaming", "laptops"],
        "total_interactions": 15
    },
    "messages": [
        {
            "timestamp": "2025-07-22T22:30:00",
            "role": "user",
            "content": "Hello",
            "message_type": "greeting"
        }
    ],
    "session_info": {
        "created_at": "2025-07-22T10:00:00",
        "total_messages": 30
    }
}
```

### Get User Analytics
```http
GET /analytics/users
```

**Response:**
```json
{
    "total_users": 25,
    "summary": {
        "total_interactions": 150,
        "active_users_24h": 8,
        "top_interests": [
            ["laptops", 12],
            ["smartphones", 8],
            ["gaming", 6]
        ]
    },
    "users": [...]
}
```

## 🧪 Testing

### Run Memory Tests
```bash
python src/test_memory.py
```

### Test Features
- ✅ Message storage and retrieval
- ✅ User preference learning
- ✅ Context generation
- ✅ Session persistence
- ✅ Multiple user handling
- ✅ Analytics generation

## 📈 Benefits

### For Users
- **Personalized Experience**: Remembers preferences and history
- **Faster Service**: No need to repeat information
- **Relevant Recommendations**: Based on interests and past interactions
- **Seamless Conversations**: Context flows naturally

### For Business
- **User Analytics**: Understand customer behavior
- **Improved Engagement**: Higher satisfaction rates
- **Better Targeting**: Personalized product recommendations
- **Data Insights**: Track popular products and currencies

## ⚙️ Configuration

### Memory Settings
```python
# In conversation_memory.py
max_messages_per_session = 50  # Keep last 50 messages
session_timeout_hours = 24     # Reset context after 24 hours
storage_dir = "data/conversations"  # Storage location
```

### Storage Management
```python
# Clean up old sessions (30+ days)
memory.cleanup_old_sessions(days_old=30)

# Get storage statistics
users = memory.get_all_users_summary()
total_storage = sum(len(user['messages']) for user in users)
```

## 🔒 Privacy & Security

### Data Protection
- **Local Storage**: All data stored locally, not in cloud
- **Encrypted Storage**: Consider encrypting sensitive data
- **Data Retention**: Automatic cleanup of old conversations
- **User Control**: Users can request data deletion

### Best Practices
- **Minimal Data**: Only store necessary information
- **Regular Cleanup**: Remove old, inactive sessions
- **Access Control**: Secure API endpoints
- **Audit Logging**: Track data access and modifications

## 🚀 Advanced Features

### 1. **Smart Context Summarization**
For long conversations, automatically summarize older messages:
```python
# Future enhancement
session.session_summary = "User John is interested in gaming laptops under 1500 EUR"
```

### 2. **Multi-Language Support**
Detect and remember user's preferred language:
```python
memory.update_user_preferences(phone_number, preferred_language="es")
```

### 3. **Integration with CRM**
Export user data to external CRM systems:
```python
crm_data = memory.export_user_data(phone_number, format="salesforce")
```

## 🛠️ Troubleshooting

### Common Issues

**Memory not persisting:**
- Check file permissions in `data/conversations/`
- Verify JSON format is valid
- Ensure sufficient disk space

**Context not loading:**
- Check if session file exists
- Verify phone number format consistency
- Review error logs for JSON parsing issues

**Performance issues:**
- Limit message history (reduce `max_messages_per_session`)
- Implement session cleanup
- Consider database storage for high volume

## 📚 Examples

### Example 1: Returning Customer
```
User: "Hi, I'm back"
Context: User John, previously interested in gaming laptops, preferred EUR
Response: "Welcome back John! Ready to continue looking at those gaming laptops in EUR?"
```

### Example 2: Currency Preference
```
User: "Convert 500 USD to EUR"
System: Learns user prefers EUR
Next interaction: Automatically shows prices in EUR
```

### Example 3: Interest Tracking
```
User: "Show me smartphones"
System: Adds "smartphones" to user interests
Future: Recommends smartphone accessories and related products
```

---

**The memory system transforms your WhatsApp bot from a simple Q&A tool into an intelligent, context-aware sales assistant that builds relationships with customers over time! 🚀**
