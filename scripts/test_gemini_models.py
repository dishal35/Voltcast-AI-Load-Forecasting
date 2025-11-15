#!/usr/bin/env python3
"""
Test script to check available Gemini models
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure API
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY not found in environment")
    exit(1)

genai.configure(api_key=api_key)

print("🔍 Available Gemini models:")
try:
    models = genai.list_models()
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"✅ {model.name}")
except Exception as e:
    print(f"❌ Error listing models: {e}")

# Test a simple generation
print("\n🔍 Testing model generation:")
model_names = [
    'gemini-1.5-pro',
    'gemini-1.5-flash',
    'gemini-1.0-pro',
    'models/gemini-1.5-pro',
    'models/gemini-1.5-flash'
]

for model_name in model_names:
    try:
        print(f"\nTesting {model_name}...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, what is 2+2?")
        print(f"✅ {model_name}: {response.text[:50]}...")
        break
    except Exception as e:
        print(f"❌ {model_name}: {e}")