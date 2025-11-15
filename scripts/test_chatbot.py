#!/usr/bin/env python3
"""
Test script for VoltCast AI Chatbot
Tests the Gemini-powered chatbot functionality.
"""
import requests
import json
import sys
from datetime import datetime

API_BASE = "http://localhost:8000/api/v1"

def test_chatbot_status():
    """Test chatbot status endpoint."""
    print("🔍 Testing chatbot status...")
    try:
        response = requests.get(f"{API_BASE}/chat/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"   Model: {data['model']}")
            print(f"   Current demand: {data['context'].get('current_demand_mw', 'N/A')} MW")
            print(f"   Temperature: {data['context'].get('current_temperature', 'N/A')}°C")
            return True
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Status check error: {e}")
        return False

def test_suggested_questions():
    """Test suggested questions endpoint."""
    print("\n🔍 Testing suggested questions...")
    try:
        response = requests.get(f"{API_BASE}/chat/suggestions")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Got {len(data['questions'])} suggested questions:")
            for i, question in enumerate(data['questions'][:3], 1):
                print(f"   {i}. {question}")
            return data['questions']
        else:
            print(f"❌ Suggestions failed: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Suggestions error: {e}")
        return []

def test_chat_message(message: str):
    """Test sending a chat message."""
    print(f"\n🔍 Testing chat message: '{message}'")
    try:
        payload = {
            "message": message,
            "conversation_history": []
        }
        
        response = requests.post(f"{API_BASE}/chat", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat response received:")
            print(f"   Success: {data['success']}")
            print(f"   Model: {data['model']}")
            print(f"   Response: {data['response'][:100]}...")
            
            # Show context info
            context = data.get('context', {})
            if context.get('current_demand_mw'):
                print(f"   Context: {context['current_demand_mw']} MW, {context.get('current_temperature')}°C")
            
            return data
        else:
            print(f"❌ Chat failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return None

def test_conversation():
    """Test a multi-turn conversation."""
    print("\n🔍 Testing conversation flow...")
    
    messages = [
        "What's the current electricity demand?",
        "Why might the demand be at this level?",
        "How does weather affect electricity usage?"
    ]
    
    conversation_history = []
    
    for i, message in enumerate(messages, 1):
        print(f"\n--- Turn {i} ---")
        
        payload = {
            "message": message,
            "conversation_history": conversation_history
        }
        
        try:
            response = requests.post(f"{API_BASE}/chat", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                print(f"User: {message}")
                print(f"Assistant: {data['response'][:150]}...")
                
                # Add to conversation history
                conversation_history.append({
                    "user": message,
                    "assistant": data['response'],
                    "timestamp": data['timestamp']
                })
                
            else:
                print(f"❌ Turn {i} failed: {response.status_code}")
                break
                
        except Exception as e:
            print(f"❌ Turn {i} error: {e}")
            break

def main():
    """Run all chatbot tests."""
    print("🤖 VoltCast AI Chatbot Test Suite")
    print("=" * 40)
    
    # Test 1: Status check
    if not test_chatbot_status():
        print("\n❌ Chatbot not available. Check:")
        print("   1. API server is running")
        print("   2. GEMINI_API_KEY is set in .env")
        print("   3. google-generativeai package is installed")
        sys.exit(1)
    
    # Test 2: Suggested questions
    suggestions = test_suggested_questions()
    
    # Test 3: Simple chat messages
    test_messages = [
        "What's the current demand?",
        "How does temperature affect electricity usage?",
        "Why is the load high today?"
    ]
    
    for message in test_messages:
        test_chat_message(message)
    
    # Test 4: Use a suggested question if available
    if suggestions:
        test_chat_message(suggestions[0])
    
    # Test 5: Conversation flow
    test_conversation()
    
    print("\n✅ Chatbot testing completed!")
    print("\nTo use the chatbot:")
    print("1. Set your GEMINI_API_KEY in .env file")
    print("2. Start the API server: python run_api.py")
    print("3. Open the frontend and use the chat interface")

if __name__ == "__main__":
    main()