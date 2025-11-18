"""
Test API endpoints with timing for previous, current, and future dates.
"""
import requests
import time
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000"

def test_endpoint(name, url, payload, timeout=60):
    """Test an endpoint and measure response time."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Payload: {payload}")
    print(f"{'='*60}")
    
    try:
        start = time.time()
        response = requests.post(url, json=payload, timeout=timeout)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS - {elapsed:.2f}s")
            
            # Show some data
            if 'predictions' in data:
                print(f"   Predictions: {len(data['predictions'])} hours")
                print(f"   First prediction: {data['predictions'][0]:.2f} MW")
            elif 'daily_forecasts' in data:
                print(f"   Daily forecasts: {len(data['daily_forecasts'])} days")
                print(f"   First day avg: {data['daily_forecasts'][0]['avg_demand_mw']:.2f} MW")
            
            return True, elapsed
        else:
            print(f"❌ FAILED - Status {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            return False, elapsed
    
    except requests.Timeout:
        elapsed = time.time() - start
        print(f"⏱️  TIMEOUT after {elapsed:.2f}s")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ ERROR - {e}")
        return False, elapsed


def main():
    """Test all scenarios."""
    print("\n" + "="*60)
    print("API ENDPOINT TIMING TEST")
    print("="*60)
    
    # Test dates
    previous_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    current_date = datetime.now().strftime("%Y-%m-%d")
    future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    results = []
    
    # 1. Daily prediction - Previous date (should use CSV)
    success, elapsed = test_endpoint(
        "Daily - Previous Date (CSV mode)",
        f"{API_BASE}/api/v1/predict/horizon",
        {
            "timestamp": f"{previous_date}T00:00:00",
            "horizon": 24
        },
        timeout=10
    )
    results.append(("Daily Previous", success, elapsed))
    
    # 2. Daily prediction - Current date (might use CSV or iterative)
    success, elapsed = test_endpoint(
        "Daily - Current Date",
        f"{API_BASE}/api/v1/predict/horizon",
        {
            "timestamp": f"{current_date}T00:00:00",
            "horizon": 24
        },
        timeout=30
    )
    results.append(("Daily Current", success, elapsed))
    
    # 3. Daily prediction - Future date (will use iterative)
    success, elapsed = test_endpoint(
        "Daily - Future Date (Iterative mode)",
        f"{API_BASE}/api/v1/predict/horizon",
        {
            "timestamp": f"{future_date}T00:00:00",
            "horizon": 24
        },
        timeout=60
    )
    results.append(("Daily Future", success, elapsed))
    
    # 4. Weekly prediction - Previous date (should use CSV)
    success, elapsed = test_endpoint(
        "Weekly - Previous Date (CSV mode)",
        f"{API_BASE}/api/v1/predict/weekly",
        {
            "start_date": previous_date
        },
        timeout=30
    )
    results.append(("Weekly Previous", success, elapsed))
    
    # 5. Weekly prediction - Current date (will use iterative)
    success, elapsed = test_endpoint(
        "Weekly - Current Date (Iterative mode)",
        f"{API_BASE}/api/v1/predict/weekly",
        {
            "start_date": current_date
        },
        timeout=120
    )
    results.append(("Weekly Current", success, elapsed))
    
    # 6. Weekly prediction - Future date (will use iterative)
    success, elapsed = test_endpoint(
        "Weekly - Future Date (Iterative mode)",
        f"{API_BASE}/api/v1/predict/weekly",
        {
            "start_date": future_date
        },
        timeout=120
    )
    results.append(("Weekly Future", success, elapsed))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for name, success, elapsed in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:25} {status:10} {elapsed:6.2f}s")
    
    # Overall
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    main()
