#!/usr/bin/env python3
"""
Test script for Voltcast-AI FastAPI.
"""
import requests
import json
from datetime import datetime, timedelta
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("Testing /api/v1/health...")
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_status():
    """Test status endpoint."""
    print("\nTesting /api/v1/status...")
    response = requests.get(f"{BASE_URL}/api/v1/status")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Service Status: {data['status']}")
        print(f"Model Version: {data['version']}")
        print(f"Artifacts: {data['artifacts']}")
        print(f"Residual Stats: {data['residual_stats']}")
    return response.status_code == 200

def test_predict():
    """Test single prediction endpoint."""
    print("\nTesting /api/v1/predict...")
    
    payload = {
        "timestamp": "2023-01-07T15:00:00",
        "temperature": 25.5,
        "solar_generation": 150.0,
        "humidity": 65.0,
        "cloud_cover": 30.0
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/predict", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Prediction: {data['prediction']:.2f} MW")
        print(f"Confidence Interval: [{data['confidence_interval']['lower']:.2f}, {data['confidence_interval']['upper']:.2f}] MW")
        if 'components' in data:
            print(f"Baseline: {data['components']['baseline']:.2f} MW")
            print(f"Residual: {data['components']['residual']:.4f} MW")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

def test_predict_horizon():
    """Test horizon prediction endpoint."""
    print("\nTesting /api/v1/predict/horizon...")
    
    payload = {
        "timestamp": "2023-01-07T15:00:00",
        "temperature": 25.5,
        "solar_generation": 150.0,
        "humidity": 65.0,
        "cloud_cover": 30.0,
        "horizon": 6
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/predict/horizon", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Horizon: {data['horizon']} hours")
        print(f"Baseline: {data['baseline']:.2f} MW")
        print(f"Predictions: {[f'{p:.2f}' for p in data['predictions'][:3]]}... MW")
        print(f"Residuals: {[f'{r:.4f}' for r in data['residuals'][:3]]}...")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

def test_root():
    """Test root endpoint."""
    print("\nTesting / (root)...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Service: {data['service']}")
        print(f"Endpoints: {list(data['endpoints'].keys())}")
    
    return response.status_code == 200

def main():
    """Run all tests."""
    print("=" * 60)
    print("Voltcast-AI FastAPI Test Suite")
    print("=" * 60)
    
    # Wait for server to be ready
    print("Waiting for server to be ready...")
    for i in range(30):
        try:
            response = requests.get(f"{BASE_URL}/api/v1/health", timeout=2)
            if response.status_code == 200:
                print("✓ Server is ready")
                break
        except:
            pass
        time.sleep(1)
        print(f"  Waiting... ({i+1}/30)")
    else:
        print("✗ Server not ready after 30 seconds")
        return False
    
    # Run tests
    tests = [
        ("Health Check", test_health),
        ("Status", test_status),
        ("Root", test_root),
        ("Single Prediction", test_predict),
        ("Horizon Prediction", test_predict_horizon),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            print(f"✓ {name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            results.append((name, False))
            print(f"✗ {name}: ERROR - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
