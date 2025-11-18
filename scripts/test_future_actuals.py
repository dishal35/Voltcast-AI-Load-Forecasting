"""
Test Future Actuals Handling
Verifies that actual values are NOT returned for future timestamps.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from api.services.data_sync import get_actual_load, get_actual_loads_range
from datetime import datetime, timedelta


def test_past_present_future():
    """Test that actuals are only returned for past/present, not future."""
    print("=" * 80)
    print("TEST: Past, Present, and Future Actuals")
    print("=" * 80)
    
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    # Test timestamps
    past_ts = now - timedelta(hours=24)      # 24 hours ago
    present_ts = now                          # Current hour
    future_ts = now + timedelta(hours=24)    # 24 hours from now
    
    print(f"\nCurrent time: {now}")
    print(f"Past timestamp: {past_ts}")
    print(f"Present timestamp: {present_ts}")
    print(f"Future timestamp: {future_ts}")
    
    # Test get_actual_load
    print(f"\n{'Testing get_actual_load():':-^80}")
    
    past_load = get_actual_load(past_ts)
    present_load = get_actual_load(present_ts)
    future_load = get_actual_load(future_ts)
    
    print(f"\nPast ({past_ts}):")
    if past_load is not None:
        print(f"  ✓ Actual: {past_load:.2f} MW (CORRECT - past data available)")
    else:
        print(f"  ⚠ Actual: None (may not be in CSV)")
    
    print(f"\nPresent ({present_ts}):")
    if present_load is not None:
        print(f"  ✓ Actual: {present_load:.2f} MW (CORRECT - current hour data available)")
    else:
        print(f"  ⚠ Actual: None (may not be synced yet)")
    
    print(f"\nFuture ({future_ts}):")
    if future_load is None:
        print(f"  ✅ Actual: None (CORRECT - future data should not exist)")
    else:
        print(f"  ❌ Actual: {future_load:.2f} MW (ERROR - future data should be None!)")
    
    # Test get_actual_loads_range
    print(f"\n{'Testing get_actual_loads_range():':-^80}")
    
    # Range spanning past to future
    start_ts = now - timedelta(hours=12)
    end_ts = now + timedelta(hours=12)
    
    print(f"\nRequesting range: {start_ts} to {end_ts}")
    print(f"  (12 hours past → 12 hours future)")
    
    df = get_actual_loads_range(start_ts, end_ts)
    
    if not df.empty:
        print(f"\n✓ Retrieved {len(df)} actual values")
        
        # Check that all timestamps are <= now
        future_timestamps = df[df['timestamp'] > now]
        
        if len(future_timestamps) == 0:
            print(f"  ✅ All timestamps are past/present (CORRECT)")
        else:
            print(f"  ❌ Found {len(future_timestamps)} future timestamps (ERROR):")
            print(future_timestamps)
        
        # Show range
        print(f"\n  Actual range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Expected: Should stop at {now} (current hour)")
        
        # Show last few records
        print(f"\n  Last 3 records:")
        print(df.tail(3))
    else:
        print(f"\n⚠ No actual values retrieved")


def test_prediction_api_future():
    """Test that prediction API returns None for future actuals."""
    print("\n" + "=" * 80)
    print("TEST: Prediction API with Future Timestamps")
    print("=" * 80)
    
    import requests
    
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    future_ts = now + timedelta(hours=6)  # 6 hours from now
    
    url = "http://localhost:8000/api/v1/predict/horizon"
    payload = {
        "timestamp": future_ts.isoformat(),
        "horizon": 24
    }
    
    try:
        print(f"\nRequesting prediction for: {future_ts}")
        print(f"  (6 hours in the future)")
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        predictions = data['predictions']
        actuals = data.get('actuals', [])
        
        print(f"\n✓ Received {len(predictions)} predictions")
        print(f"  Actuals array length: {len(actuals)}")
        
        # Count None values
        none_count = sum(1 for a in actuals if a is None)
        non_none_count = sum(1 for a in actuals if a is not None)
        
        print(f"\n  Actuals breakdown:")
        print(f"    None (future): {none_count}")
        print(f"    Values (past): {non_none_count}")
        
        if none_count == len(actuals):
            print(f"\n  ✅ All actuals are None (CORRECT - all timestamps are future)")
        elif non_none_count == 0:
            print(f"\n  ✅ No actual values (CORRECT - all timestamps are future)")
        else:
            print(f"\n  ⚠ Some actuals have values (may be partially past)")
        
        # Show first 5
        print(f"\n  First 5 hours:")
        for i in range(min(5, len(predictions))):
            hour_ts = future_ts + timedelta(hours=i)
            pred = predictions[i]
            actual = actuals[i] if i < len(actuals) else None
            
            if actual is None:
                print(f"    Hour {i} ({hour_ts.strftime('%H:%M')}): Pred={pred:.2f}, Actual=None ✓")
            else:
                print(f"    Hour {i} ({hour_ts.strftime('%H:%M')}): Pred={pred:.2f}, Actual={actual:.2f} ⚠")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ API not running. Start with: python run_api.py")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def test_prediction_api_past():
    """Test that prediction API returns actuals for past timestamps."""
    print("\n" + "=" * 80)
    print("TEST: Prediction API with Past Timestamps")
    print("=" * 80)
    
    import requests
    
    # Use a known past date with data
    past_ts = datetime(2024, 1, 1, 0, 0, 0)
    
    url = "http://localhost:8000/api/v1/predict/horizon"
    payload = {
        "timestamp": past_ts.isoformat(),
        "horizon": 24
    }
    
    try:
        print(f"\nRequesting prediction for: {past_ts}")
        print(f"  (historical date with known data)")
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        predictions = data['predictions']
        actuals = data.get('actuals', [])
        
        print(f"\n✓ Received {len(predictions)} predictions")
        
        # Count None values
        none_count = sum(1 for a in actuals if a is None)
        non_none_count = sum(1 for a in actuals if a is not None)
        
        print(f"\n  Actuals breakdown:")
        print(f"    Values (available): {non_none_count}")
        print(f"    None (missing): {none_count}")
        
        if non_none_count == len(actuals):
            print(f"\n  ✅ All actuals available (CORRECT - all timestamps are past)")
        elif non_none_count > 0:
            print(f"\n  ✅ Some actuals available (CORRECT - past data exists)")
        else:
            print(f"\n  ⚠ No actuals available (may be missing from CSV)")
        
        # Show first 5 with errors
        print(f"\n  First 5 hours with errors:")
        for i in range(min(5, len(predictions))):
            pred = predictions[i]
            actual = actuals[i] if i < len(actuals) else None
            
            if actual is not None:
                error = pred - actual
                print(f"    Hour {i}: Pred={pred:.2f}, Actual={actual:.2f}, Error={error:+.2f} ✓")
            else:
                print(f"    Hour {i}: Pred={pred:.2f}, Actual=None ⚠")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ API not running. Start with: python run_api.py")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("FUTURE ACTUALS HANDLING TEST")
    print("Verifying that future timestamps return None for actuals")
    print("=" * 80)
    
    test_past_present_future()
    test_prediction_api_future()
    test_prediction_api_past()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\n✅ Expected behavior:")
    print("  - Past timestamps: Return actual values")
    print("  - Current hour: Return actual value (if synced)")
    print("  - Future timestamps: Return None")
